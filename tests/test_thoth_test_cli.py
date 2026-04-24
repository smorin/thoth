"""CLI-surface tests for the thoth_test runner itself."""

import importlib.machinery
import importlib.util
import pathlib

import pytest


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
