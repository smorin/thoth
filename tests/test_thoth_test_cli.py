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
