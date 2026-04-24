"""CLI-surface tests for the thoth_test runner itself."""

import importlib.machinery
import importlib.util
import json
import pathlib
import subprocess

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _run_thoth_test(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["./thoth_test", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.fixture(scope="module")
def thoth_test_mod():
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    loader = importlib.machinery.SourceFileLoader("thoth_test_mod", str(repo_root / "thoth_test"))
    spec = importlib.util.spec_from_loader("thoth_test_mod", loader)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_resolve_selection_provider_filter_keeps_agnostic(thoth_test_mod):
    TC = thoth_test_mod.TestCase
    all_tests = [
        TC(test_id="A", description="agnostic", command=["x"]),
        TC(test_id="B", description="mock only", command=["x"], provider="mock"),
        TC(test_id="C", description="openai only", command=["x"], provider="openai"),
    ]
    selected, warnings = thoth_test_mod.resolve_selection(
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


def test_resolve_selection_substring_pattern(thoth_test_mod):
    TC = thoth_test_mod.TestCase
    all_tests = [
        TC(test_id="M1T-01", description="alpha", command=["x"]),
        TC(test_id="M1T-02", description="beta cancelled", command=["x"]),
        TC(test_id="OTHER", description="gamma", command=["x"]),
    ]
    selected, _ = thoth_test_mod.resolve_selection(
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
    proc = _run_thoth_test("--list")
    assert proc.returncode == 0
    lines = [line for line in proc.stdout.splitlines() if line]
    assert lines, "expected at least one test listed"
    for line in lines:
        parts = line.split("\t")
        assert len(parts) == 4, f"expected 4 tab-separated fields, got {len(parts)}: {line!r}"


def test_list_json_shape():
    proc = _run_thoth_test("--list-json")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert isinstance(data, list)
    assert data, "expected at least one test"
    entry = data[0]
    for key in ("test_id", "provider", "test_type", "description", "is_interactive"):
        assert key in entry, f"missing key {key!r} in {entry!r}"


def test_list_and_list_json_mutually_exclusive():
    proc = _run_thoth_test("--list", "--list-json")
    assert proc.returncode == 2
    assert "mutually exclusive" in proc.stderr.lower()


def test_list_respects_provider_filter():
    all_proc = _run_thoth_test("--list")
    filtered_proc = _run_thoth_test("--list", "--provider", "mock")
    assert all_proc.returncode == 0 and filtered_proc.returncode == 0
    all_ids = {line.split("\t")[0] for line in all_proc.stdout.splitlines() if line}
    filtered_ids = {line.split("\t")[0] for line in filtered_proc.stdout.splitlines() if line}
    assert filtered_ids <= all_ids
    assert filtered_ids, "mock filter should keep at least mock-provider tests"


def test_id_exact_match_runs_only_that_test(thoth_test_mod):
    TC = thoth_test_mod.TestCase
    all_tests = [
        TC(test_id="A", description="a", command=["x"]),
        TC(test_id="AB", description="ab", command=["x"]),
        TC(test_id="B", description="b", command=["x"]),
    ]
    selected, warnings = thoth_test_mod.resolve_selection(
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


def test_id_unknown_warns_but_does_not_error(thoth_test_mod):
    TC = thoth_test_mod.TestCase
    all_tests = [TC(test_id="A", description="a", command=["x"])]
    selected, warnings = thoth_test_mod.resolve_selection(
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


def test_id_overrides_provider_filter_and_marks_requested_but_filtered(thoth_test_mod):
    TC = thoth_test_mod.TestCase
    all_tests = [
        TC(test_id="OA", description="openai test", command=["x"], provider="openai"),
        TC(test_id="MK", description="mock test", command=["x"], provider="mock"),
    ]
    selected, warnings = thoth_test_mod.resolve_selection(
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


def test_id_integration_runs_exactly_one_test():
    proc = _run_thoth_test("-r", "--id", "M1T-01", "-q")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "1 passed" in proc.stdout


def test_cache_written_on_every_run(tmp_path, monkeypatch):
    cache_file = REPO_ROOT / ".thoth_test_cache" / "last_run.json"
    if cache_file.exists():
        cache_file.unlink()
    proc = _run_thoth_test("-r", "--id", "M1T-01")
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


def test_cache_failure_includes_full_output(thoth_test_mod, tmp_path):
    runner = thoth_test_mod.TestRunner()
    runner.start_time = 0.0
    runner.filtered_tests = [
        thoth_test_mod.TestCase(test_id="F1", description="fail", command=["x"], provider="mock"),
    ]
    runner.results = [
        thoth_test_mod.TestResult(
            test_id="F1",
            passed=False,
            duration=0.1,
            stdout="big stdout payload",
            stderr="big stderr payload",
            exit_code=1,
            error_message="boom",
        )
    ]
    report = thoth_test_mod.serialize_run_report(runner, invocation=["./thoth_test", "-r"])
    assert len(report["tests"]) == 1
    entry = report["tests"][0]
    assert entry["passed"] is False
    assert entry["stdout"] == "big stdout payload"
    assert entry["stderr"] == "big stderr payload"
    assert report["schema_version"] == 1
    assert report["counts"]["failed"] == 1


def test_last_failed_exits_2_when_no_cache(tmp_path):
    cache_file = REPO_ROOT / ".thoth_test_cache" / "last_run.json"
    if cache_file.exists():
        cache_file.unlink()
    proc = _run_thoth_test("-r", "--last-failed")
    assert proc.returncode == 2
    assert "no prior failures" in proc.stderr.lower()


def test_last_failed_zero_failures_also_exits_2(tmp_path):
    # First populate cache with only passes.
    proc = _run_thoth_test("-r", "--id", "M1T-01")
    assert proc.returncode == 0
    proc2 = _run_thoth_test("-r", "--last-failed")
    assert proc2.returncode == 2
    assert "no prior failures" in proc2.stderr.lower()


def test_read_last_failed_returns_ids(thoth_test_mod, tmp_path):
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
    assert thoth_test_mod.read_last_failed(cache) == ["BAD"]


def test_read_last_failed_raises_on_missing(thoth_test_mod, tmp_path):
    with pytest.raises(FileNotFoundError):
        thoth_test_mod.read_last_failed(tmp_path / "nope.json")


def test_report_json_writes_to_given_path(tmp_path):
    target = tmp_path / "run.json"
    proc = _run_thoth_test("-r", "--id", "M1T-01", "--report-json", str(target))
    assert proc.returncode == 0
    assert target.exists()
    payload = json.loads(target.read_text())
    assert payload["schema_version"] == 1
    assert payload["counts"]["total"] == 1


def test_report_json_matches_cache_content(tmp_path):
    target = tmp_path / "run.json"
    proc = _run_thoth_test("-r", "--id", "M1T-01", "--report-json", str(target))
    assert proc.returncode == 0
    cache_file = REPO_ROOT / ".thoth_test_cache" / "last_run.json"
    assert cache_file.exists()
    cache_payload = json.loads(cache_file.read_text())
    target_payload = json.loads(target.read_text())
    # finished_at may differ by one clock tick between writes; compare everything else.
    for key in ("schema_version", "invocation", "requested_providers", "counts", "tests"):
        assert cache_payload[key] == target_payload[key], f"mismatch on {key}"


def test_quiet_suppresses_table_on_pass():
    proc = _run_thoth_test("-r", "--id", "M1T-01", "-q")
    assert proc.returncode == 0
    assert "Test Results" not in proc.stdout
    assert "1 passed" in proc.stdout
    assert "0 failed" in proc.stdout
    assert ".thoth_test_cache/last_run.json" in proc.stdout


def test_quiet_emits_fenced_failure_for_failing_test(thoth_test_mod, capsys, monkeypatch, tmp_path):
    fake_cache = tmp_path / "cache.json"
    monkeypatch.setattr(thoth_test_mod, "CACHE_FILE", fake_cache)
    monkeypatch.setattr(thoth_test_mod.write_cache_atomic, "__defaults__", (fake_cache,))
    runner = thoth_test_mod.TestRunner(quiet=True)
    runner.start_time = 0.0
    runner.filtered_tests = [
        thoth_test_mod.TestCase(
            test_id="FAIL-1",
            description="deliberate failure",
            command=["x"],
            provider="mock",
        )
    ]
    runner.results = [
        thoth_test_mod.TestResult(
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
    # Seed the real cache with a stale failing ID.
    cache_file = REPO_ROOT / ".thoth_test_cache" / "last_run.json"
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
    try:
        proc = _run_thoth_test("-r", "--last-failed")
        assert proc.returncode == 2
        assert "removed tests" in proc.stderr.lower() or "nothing to rerun" in proc.stderr.lower()
    finally:
        if cache_file.exists():
            cache_file.unlink()
