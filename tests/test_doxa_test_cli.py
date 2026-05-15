"""CLI-surface tests for the doxa_test runner itself."""

import importlib.machinery
import importlib.util
import json
import pathlib
import subprocess

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DOXA_TEST = REPO_ROOT / "doxa_test"


def _run_doxa_test(
    *args: str, cache_dir: pathlib.Path | None = None
) -> subprocess.CompletedProcess:
    """Invoke the doxa_test script.

    Pass ``cache_dir=tmp_path / ".doxa_test_cache"`` (or similar) to isolate
    the run's cache file from the repo's real cache. The child reads
    ``DOXA_TEST_CACHE_DIR`` to override the default location.
    """
    env = None
    if cache_dir is not None:
        import os as _os

        env = {**_os.environ, "DOXA_TEST_CACHE_DIR": str(cache_dir)}
    return subprocess.run(
        [str(DOXA_TEST), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )


@pytest.fixture(scope="module")
def doxa_test_mod():
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    loader = importlib.machinery.SourceFileLoader("doxa_test_mod", str(repo_root / "doxa_test"))
    spec = importlib.util.spec_from_loader("doxa_test_mod", loader)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_resolve_selection_provider_filter_keeps_agnostic(doxa_test_mod):
    TC = doxa_test_mod.TestCase
    all_tests = [
        TC(test_id="A", description="agnostic", command=["x"]),
        TC(test_id="B", description="mock only", command=["x"], provider="mock"),
        TC(test_id="C", description="openai only", command=["x"], provider="openai"),
    ]
    selected, warnings = doxa_test_mod.resolve_selection(
        all_tests,
        test=None,
        provider_filter=["mock"],
        interactive=False,
        skip_interactive=False,
        ids=[],
        last_failed=False,
    )
    ids = [t.test_id for t in selected]
    assert ids == ["A", "B"]
    assert warnings == []


def test_resolve_selection_substring_pattern(doxa_test_mod):
    TC = doxa_test_mod.TestCase
    all_tests = [
        TC(test_id="M1T-01", description="alpha", command=["x"]),
        TC(test_id="M1T-02", description="beta cancelled", command=["x"]),
        TC(test_id="OTHER", description="gamma", command=["x"]),
    ]
    selected, _ = doxa_test_mod.resolve_selection(
        all_tests,
        test="cancelled",
        provider_filter=None,
        interactive=False,
        skip_interactive=False,
        ids=[],
        last_failed=False,
    )
    assert [t.test_id for t in selected] == ["M1T-02"]


def test_list_tsv_shape():
    proc = _run_doxa_test("--list")
    assert proc.returncode == 0
    lines = [line for line in proc.stdout.splitlines() if line]
    assert lines, "expected at least one test listed"
    for line in lines:
        parts = line.split("\t")
        assert len(parts) == 4, f"expected 4 tab-separated fields, got {len(parts)}: {line!r}"


def test_list_json_shape():
    proc = _run_doxa_test("--list-json")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert isinstance(data, list)
    assert data, "expected at least one test"
    entry = data[0]
    for key in ("test_id", "provider", "test_type", "description", "is_interactive"):
        assert key in entry, f"missing key {key!r} in {entry!r}"


def test_list_and_list_json_mutually_exclusive():
    proc = _run_doxa_test("--list", "--list-json")
    assert proc.returncode == 2
    assert "mutually exclusive" in proc.stderr.lower()


def test_list_respects_provider_filter():
    all_proc = _run_doxa_test("--list")
    filtered_proc = _run_doxa_test("--list", "--provider", "mock")
    assert all_proc.returncode == 0 and filtered_proc.returncode == 0
    all_ids = {line.split("\t")[0] for line in all_proc.stdout.splitlines() if line}
    filtered_ids = {line.split("\t")[0] for line in filtered_proc.stdout.splitlines() if line}
    assert filtered_ids <= all_ids
    assert filtered_ids, "mock filter should keep at least mock-provider tests"


def test_list_accepts_gemini_provider_filter():
    proc = _run_doxa_test("--list", "--provider", "gemini")
    assert proc.returncode == 0
    assert "REAL-03\tgemini\t" in proc.stdout


def test_list_omits_obsolete_combined_placeholder():
    proc = _run_doxa_test("--list")
    assert proc.returncode == 0
    assert "COMB-01\t" not in proc.stdout


def test_provider_discovery_includes_gemini_when_key_is_set(doxa_test_mod, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-test")
    keys = doxa_test_mod.get_test_api_keys()
    assert keys["gemini"] == "AIza-test"
    assert "gemini" in doxa_test_mod.get_available_providers(keys)


def test_id_exact_match_runs_only_that_test(doxa_test_mod):
    TC = doxa_test_mod.TestCase
    all_tests = [
        TC(test_id="A", description="a", command=["x"]),
        TC(test_id="AB", description="ab", command=["x"]),
        TC(test_id="B", description="b", command=["x"]),
    ]
    selected, warnings = doxa_test_mod.resolve_selection(
        all_tests,
        test=None,
        provider_filter=None,
        interactive=False,
        skip_interactive=False,
        ids=["A"],
        last_failed=False,
    )
    assert [t.test_id for t in selected] == ["A"]
    assert warnings == []


def test_id_unknown_warns_but_does_not_error(doxa_test_mod):
    TC = doxa_test_mod.TestCase
    all_tests = [TC(test_id="A", description="a", command=["x"])]
    selected, warnings = doxa_test_mod.resolve_selection(
        all_tests,
        test=None,
        provider_filter=None,
        interactive=False,
        skip_interactive=False,
        ids=["DOES-NOT-EXIST"],
        last_failed=False,
    )
    assert selected == []
    assert any("DOES-NOT-EXIST" in w for w in warnings)


def test_id_overrides_provider_filter_and_marks_requested_but_filtered(doxa_test_mod):
    TC = doxa_test_mod.TestCase
    all_tests = [
        TC(test_id="OA", description="openai test", command=["x"], provider="openai"),
        TC(test_id="MK", description="mock test", command=["x"], provider="mock"),
    ]
    selected, warnings = doxa_test_mod.resolve_selection(
        all_tests,
        test=None,
        provider_filter=["mock"],
        interactive=False,
        skip_interactive=False,
        ids=["OA"],
        last_failed=False,
    )
    assert [t.test_id for t in selected] == ["OA"]
    assert getattr(selected[0], "_requested_but_filtered", False) is True
    assert any("OA" in w and "provider" in w.lower() for w in warnings)


def test_id_integration_runs_exactly_one_test(tmp_path):
    proc = _run_doxa_test("-r", "--id", "M1T-01", "-q", cache_dir=tmp_path / ".doxa_test_cache")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "1 passed" in proc.stdout


def test_cache_written_on_every_run(tmp_path):
    cache_file = tmp_path / ".doxa_test_cache" / "last_run.json"
    proc = _run_doxa_test("-r", "--id", "M1T-01", cache_dir=tmp_path / ".doxa_test_cache")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert cache_file.exists(), "cache file should be written after every run"
    payload = json.loads(cache_file.read_text())
    assert payload["schema_version"] == 1
    assert payload["counts"]["total"] == 1
    assert payload["counts"]["passed"] == 1
    entry = payload["tests"][0]
    assert entry["test_id"] == "M1T-01"
    assert entry["passed"] is True
    assert entry["stdout"] is None
    assert entry["stderr"] is None


def test_cache_failure_includes_full_output(doxa_test_mod, tmp_path):
    runner = doxa_test_mod.TestRunner()
    runner.start_time = 0.0
    runner.filtered_tests = [
        doxa_test_mod.TestCase(test_id="F1", description="fail", command=["x"], provider="mock"),
    ]
    runner.results = [
        doxa_test_mod.TestResult(
            test_id="F1",
            passed=False,
            duration=0.1,
            stdout="big stdout payload",
            stderr="big stderr payload",
            exit_code=1,
            error_message="boom",
        )
    ]
    report = doxa_test_mod.serialize_run_report(runner, invocation=["./doxa_test", "-r"])
    assert len(report["tests"]) == 1
    entry = report["tests"][0]
    assert entry["passed"] is False
    assert entry["stdout"] == "big stdout payload"
    assert entry["stderr"] == "big stderr payload"
    assert report["schema_version"] == 1
    assert report["counts"]["failed"] == 1


def test_last_failed_exits_2_when_no_cache(tmp_path):
    proc = _run_doxa_test("-r", "--last-failed", cache_dir=tmp_path / ".doxa_test_cache")
    assert proc.returncode == 2
    assert "no cached run found" in proc.stderr.lower()


def test_last_failed_zero_failures_also_exits_2(tmp_path):
    # First populate cache with only passes.
    proc = _run_doxa_test("-r", "--id", "M1T-01", cache_dir=tmp_path / ".doxa_test_cache")
    assert proc.returncode == 0
    proc2 = _run_doxa_test("-r", "--last-failed", cache_dir=tmp_path / ".doxa_test_cache")
    assert proc2.returncode == 2
    assert "no failures" in proc2.stderr.lower()


def test_read_last_failed_returns_ids(doxa_test_mod, tmp_path):
    cache = tmp_path / "last_run.json"
    cache.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "tests": [
                    {"test_id": "OK", "passed": True, "skipped": False},
                    {"test_id": "BAD", "passed": False, "skipped": False},
                ],
            }
        )
    )
    assert doxa_test_mod.read_last_failed(cache) == ["BAD"]


def test_read_last_failed_raises_on_missing(doxa_test_mod, tmp_path):
    with pytest.raises(FileNotFoundError):
        doxa_test_mod.read_last_failed(tmp_path / "nope.json")


def test_read_last_failed_raises_on_corrupt_json(doxa_test_mod, tmp_path):
    cache = tmp_path / "cache.json"
    cache.write_text("{not valid json")
    with pytest.raises(FileNotFoundError):
        doxa_test_mod.read_last_failed(cache)


def test_read_last_failed_raises_on_missing_tests_key(doxa_test_mod, tmp_path):
    cache = tmp_path / "cache.json"
    cache.write_text(json.dumps({"schema_version": 1}))
    assert doxa_test_mod.read_last_failed(cache) == []


def test_read_last_failed_raises_on_wrong_schema_version(doxa_test_mod, tmp_path):
    cache = tmp_path / "cache.json"
    cache.write_text(json.dumps({"schema_version": 999, "tests": []}))
    with pytest.raises(FileNotFoundError):
        doxa_test_mod.read_last_failed(cache)


def test_read_last_failed_raises_on_non_dict_payload(doxa_test_mod, tmp_path):
    cache = tmp_path / "cache.json"
    cache.write_text(json.dumps([{"test_id": "X", "passed": False}]))
    with pytest.raises(FileNotFoundError):
        doxa_test_mod.read_last_failed(cache)


def test_read_last_failed_skips_malformed_entries(doxa_test_mod, tmp_path):
    cache = tmp_path / "cache.json"
    cache.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "tests": [
                    "not a dict",
                    {"passed": False},  # missing test_id
                    {"test_id": "GOOD", "passed": False},
                ],
            }
        )
    )
    assert doxa_test_mod.read_last_failed(cache) == ["GOOD"]


def test_report_json_writes_to_given_path(tmp_path):
    target = tmp_path / "run.json"
    proc = _run_doxa_test(
        "-r",
        "--id",
        "M1T-01",
        "--report-json",
        str(target),
        cache_dir=tmp_path / ".doxa_test_cache",
    )
    assert proc.returncode == 0
    assert target.exists()
    payload = json.loads(target.read_text())
    assert payload["schema_version"] == 1
    assert payload["counts"]["total"] == 1


def test_report_json_matches_cache_content(tmp_path):
    target = tmp_path / "run.json"
    proc = _run_doxa_test(
        "-r",
        "--id",
        "M1T-01",
        "--report-json",
        str(target),
        cache_dir=tmp_path / ".doxa_test_cache",
    )
    assert proc.returncode == 0
    cache_file = tmp_path / ".doxa_test_cache" / "last_run.json"
    assert cache_file.exists()
    cache_payload = json.loads(cache_file.read_text())
    target_payload = json.loads(target.read_text())
    # finished_at may differ by one clock tick between writes; compare everything else.
    for key in ("schema_version", "invocation", "requested_providers", "counts", "tests"):
        assert cache_payload[key] == target_payload[key], f"mismatch on {key}"


def test_quiet_suppresses_table_on_pass(tmp_path):
    proc = _run_doxa_test("-r", "--id", "M1T-01", "-q", cache_dir=tmp_path / ".doxa_test_cache")
    assert proc.returncode == 0
    assert "Test Results" not in proc.stdout
    assert "1 passed" in proc.stdout
    assert "0 failed" in proc.stdout
    assert ".doxa_test_cache/last_run.json" in proc.stdout


def test_quiet_emits_fenced_failure_for_failing_test(doxa_test_mod, capsys, monkeypatch, tmp_path):
    fake_cache = tmp_path / "cache.json"
    monkeypatch.setattr(doxa_test_mod, "CACHE_FILE", fake_cache)
    monkeypatch.setattr(doxa_test_mod.write_cache_atomic, "__defaults__", (fake_cache,))
    runner = doxa_test_mod.TestRunner(quiet=True)
    runner.start_time = 0.0
    runner.filtered_tests = [
        doxa_test_mod.TestCase(
            test_id="FAIL-1",
            description="deliberate failure",
            command=["x"],
            provider="mock",
        )
    ]
    runner.results = [
        doxa_test_mod.TestResult(
            test_id="FAIL-1",
            passed=False,
            duration=0.5,
            stdout="STDOUT-MARKER",
            stderr="STDERR-MARKER",
            exit_code=1,
            error_message="boom",
        )
    ]
    with pytest.raises(SystemExit):
        runner.generate_report()
    out = capsys.readouterr().out
    assert "===BEGIN FAILURE FAIL-1===" in out
    assert "===END FAILURE FAIL-1===" in out
    assert "STDOUT-MARKER" in out
    assert "STDERR-MARKER" in out
    assert "Test Results" not in out
    # Cache was redirected; real one untouched.
    assert (tmp_path / "cache.json").exists()


def test_last_failed_exits_2_when_all_cached_ids_unknown(tmp_path):
    # Seed an isolated cache with a stale failing ID.
    cache_file = tmp_path / ".doxa_test_cache" / "last_run.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "tests": [
                    {"test_id": "NO-SUCH-TEST", "passed": False, "skipped": False},
                ],
            }
        )
    )
    proc = _run_doxa_test("-r", "--last-failed", cache_dir=tmp_path / ".doxa_test_cache")
    assert proc.returncode == 2
    assert "removed tests" in proc.stderr.lower() or "nothing to rerun" in proc.stderr.lower()


def test_list_with_last_failed_previews_failures(tmp_path):
    # Seed cache with one real failing ID (M1T-01 exists).
    cache_file = tmp_path / ".doxa_test_cache" / "last_run.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "tests": [
                    {"test_id": "M1T-01", "passed": False, "skipped": False},
                ],
            }
        )
    )
    proc = _run_doxa_test("--list", "--last-failed", cache_dir=tmp_path / ".doxa_test_cache")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    # TSV output: only M1T-01 should appear as a data row.
    lines = [ln for ln in proc.stdout.splitlines() if ln and not ln.startswith("test_id\t")]
    assert len(lines) == 1
    assert lines[0].startswith("M1T-01\t")


def test_list_with_last_failed_no_cache_exits_2(tmp_path):
    proc = _run_doxa_test("--list", "--last-failed", cache_dir=tmp_path / ".doxa_test_cache")
    assert proc.returncode == 2
    assert "no cached run found" in proc.stderr.lower()


def test_rerun_hint_uses_id_not_t(doxa_test_mod, tmp_path, monkeypatch, capsys):
    # Redirect the cache so the report write doesn't hit the repo. Must patch
    # BOTH the module attribute and write_cache_atomic.__defaults__ because
    # generate_report calls write_cache_atomic(report) bare and Python freezes
    # the default arg at function-definition time.
    fake_cache = tmp_path / "cache.json"
    monkeypatch.setattr(doxa_test_mod, "CACHE_FILE", fake_cache)
    monkeypatch.setattr(doxa_test_mod.write_cache_atomic, "__defaults__", (fake_cache,))
    runner = doxa_test_mod.TestRunner()
    runner.start_time = 0.0
    runner.filtered_tests = [
        doxa_test_mod.TestCase(test_id="FAIL-1", description="fail", command=["x"], provider="mock")
    ]
    runner.results = [
        doxa_test_mod.TestResult(
            test_id="FAIL-1",
            passed=False,
            duration=0.1,
            stdout="",
            stderr="",
            exit_code=1,
            error_message="boom",
        )
    ]
    with pytest.raises(SystemExit):
        runner.generate_report()
    out = capsys.readouterr().out
    assert "--id FAIL-1" in out
    assert "--last-failed" in out
    assert "-t FAIL-1" not in out


def test_interactive_runner_pins_uv_cache_dir(doxa_test_mod, monkeypatch):
    captured = {}

    class FakeChild:
        before = ""
        exitstatus = 0
        signalstatus = None

        def expect(self, pattern, timeout=None):
            return 0

        def isalive(self):
            return False

        def close(self, force=False):
            return None

    def fake_spawn(command, args=None, env=None, **kwargs):
        captured["env"] = env or {}
        return FakeChild()

    monkeypatch.delenv("UV_CACHE_DIR", raising=False)
    monkeypatch.setattr(doxa_test_mod.pexpect, "spawn", fake_spawn)

    runner = doxa_test_mod.InteractiveTestRunner()
    result = runner.run_interactive_test(
        doxa_test_mod.TestCase(
            test_id="INT-UV",
            description="interactive uv cache",
            command=["./doxa_research", "-i"],
            test_type="interactive",
        )
    )

    assert result.passed
    assert captured["env"]["UV_CACHE_DIR"] == str(pathlib.Path.home() / ".cache" / "uv")


def test_validate_file_contents_checks_recent_matching_files(doxa_test_mod, tmp_path):
    target = tmp_path / "answer.md"
    target.write_text("# Mock streaming response\n\nEcho: test output\n")

    passed, matched, error = doxa_test_mod.validate_file_contents(
        {"answer.md": [r"# Mock streaming response", r"Echo: test output"]},
        since=0.0,
        base=tmp_path,
    )

    assert passed
    assert matched == [target]
    assert error == ""


def test_validate_file_contents_reports_missing_pattern(doxa_test_mod, tmp_path):
    target = tmp_path / "answer.md"
    target.write_text("wrong content")

    passed, matched, error = doxa_test_mod.validate_file_contents(
        {"answer.md": [r"Echo: test output"]},
        since=0.0,
        base=tmp_path,
    )

    assert not passed
    assert matched == [target]
    assert "Missing content pattern" in error


def test_validate_file_content_absence_reports_forbidden_pattern(doxa_test_mod, tmp_path):
    target = tmp_path / "answer.md"
    target.write_text("---\noperation_id: op_test\n---\n\n# Mock Research Results\n")

    passed, matched, error = doxa_test_mod.validate_file_content_absence(
        {"answer.md": [r"operation_id:"]},
        since=0.0,
        base=tmp_path,
    )

    assert not passed
    assert matched == [target]
    assert "Unexpected content pattern" in error


def test_validate_file_content_absence_allows_missing_pattern(doxa_test_mod, tmp_path):
    target = tmp_path / "answer.md"
    target.write_text("# Mock Research Results\n")

    passed, matched, error = doxa_test_mod.validate_file_content_absence(
        {"answer.md": [r"operation_id:"]},
        since=0.0,
        base=tmp_path,
    )

    assert passed
    assert matched == [target]
    assert error == ""
