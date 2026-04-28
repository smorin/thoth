"""Unit tests for the parallel-execution hazard detector in ``thoth_test``.

Loads ``thoth_test`` (a script with no .py extension) via importlib so we can
unit-test the pure ``detect_parallel_hazards`` function without invoking the
CLI. The script is import-safe: ``main()`` is guarded by ``__name__`` and
none of the decorated commands fire at import time.
"""

from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import ModuleType

THOTH_TEST_PATH = Path(__file__).resolve().parent.parent / "thoth_test"


def _load_thoth_test() -> ModuleType:
    # `thoth_test` has no .py suffix, so spec_from_file_location can't infer a
    # loader. Pass SourceFileLoader explicitly.
    loader = SourceFileLoader("thoth_test_mod", str(THOTH_TEST_PATH))
    spec = importlib.util.spec_from_file_location("thoth_test_mod", THOTH_TEST_PATH, loader=loader)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_MOD = _load_thoth_test()
detect_parallel_hazards = _MOD.detect_parallel_hazards


def _tc(test_id: str, *args: str):
    """Build a minimal TestCase for hazard-detection tests.

    Builds via _MOD.TestCase rather than importing the symbol at module scope
    so pytest doesn't try to collect TestCase as a test class.
    """
    return _MOD.TestCase(
        test_id=test_id,
        description=f"hazard probe {test_id}",
        command=["./thoth", "prompt", *args],
    )


def test_disjoint_o_paths_clean():
    cases = [_tc("A", "-o", "out_a"), _tc("B", "-o", "out_b")]
    assert detect_parallel_hazards(cases) == []


def test_no_opt_out_flags_clean():
    cases = [_tc("A"), _tc("B"), _tc("C", "--provider", "mock")]
    assert detect_parallel_hazards(cases) == []


def test_duplicate_o_flag_collides():
    cases = [_tc("A", "-o", "shared"), _tc("B", "-o", "shared")]
    hazards = detect_parallel_hazards(cases)
    assert len(hazards) == 1
    assert "A" in hazards[0] and "B" in hazards[0]
    assert "-o" in hazards[0]


def test_duplicate_project_collides():
    cases = [_tc("A", "--project", "p"), _tc("B", "--project", "p")]
    hazards = detect_parallel_hazards(cases)
    assert len(hazards) == 1
    assert "--project" in hazards[0]


def test_o_and_output_dir_alias_collide():
    cases = [_tc("A", "-o", "shared"), _tc("B", "--output-dir", "shared")]
    hazards = detect_parallel_hazards(cases)
    assert len(hazards) == 1


def test_path_normalization_dot_slash():
    cases = [_tc("A", "-o", "./foo"), _tc("B", "-o", "foo")]
    hazards = detect_parallel_hazards(cases)
    assert len(hazards) == 1


def test_cross_form_o_vs_project_collide():
    """`-o research-outputs/foo` and `--project foo` resolve to the same path."""
    cases = [
        _tc("A", "-o", "research-outputs/foo"),
        _tc("B", "--project", "foo"),
    ]
    hazards = detect_parallel_hazards(cases)
    assert len(hazards) == 1
    assert "A" in hazards[0] and "B" in hazards[0]


def test_three_way_collision_lists_all_ids():
    cases = [
        _tc("A", "-o", "shared"),
        _tc("B", "-o", "shared"),
        _tc("C", "-o", "shared"),
    ]
    hazards = detect_parallel_hazards(cases)
    assert len(hazards) == 1
    for tid in ("A", "B", "C"):
        assert tid in hazards[0]


def test_first_flag_occurrence_wins():
    """If a test mistakenly has `-o` twice, the first one is the effective value
    (matches the `any(a in cmd for a in ...)` check the runner uses)."""
    cases = [
        _tc("A", "-o", "first", "-o", "second"),
        _tc("B", "-o", "first"),
    ]
    hazards = detect_parallel_hazards(cases)
    assert len(hazards) == 1
    assert "first" in hazards[0]


def test_o_eq_form_collides_with_space_form():
    """`-o=foo` must resolve to the same target as `-o foo`."""
    cases = [_tc("A", "-o=shared"), _tc("B", "-o", "shared")]
    hazards = detect_parallel_hazards(cases)
    assert len(hazards) == 1
    assert "A" in hazards[0] and "B" in hazards[0]


def test_output_dir_eq_form_collides_with_o_space_form():
    """`--output-dir=foo` and `-o foo` are aliases under either syntax."""
    cases = [_tc("A", "--output-dir=foo"), _tc("B", "-o", "foo")]
    hazards = detect_parallel_hazards(cases)
    assert len(hazards) == 1


def test_project_eq_form_collides_with_space_form():
    cases = [_tc("A", "--project=p"), _tc("B", "--project", "p")]
    hazards = detect_parallel_hazards(cases)
    assert len(hazards) == 1


def test_project_eq_form_cross_collides_with_o_path():
    """`--project=foo` resolves to research-outputs/foo, same as `-o research-outputs/foo`."""
    cases = [
        _tc("A", "--project=foo"),
        _tc("B", "-o=research-outputs/foo"),
    ]
    hazards = detect_parallel_hazards(cases)
    assert len(hazards) == 1


def test_ambiguous_multi_flag_test_is_flagged():
    """A single TestCase with both -o and --project is ambiguous."""
    cases = [_tc("A", "-o", "x", "--project", "y")]
    hazards = detect_parallel_hazards(cases)
    # Reports the ambiguity for test A (1 message).
    assert any("Ambiguous" in h and "A" in h for h in hazards)


def test_ambiguous_multi_flag_eq_form():
    """=-attached forms still trip the ambiguity check."""
    cases = [_tc("A", "-o=x", "--project=y")]
    hazards = detect_parallel_hazards(cases)
    assert any("Ambiguous" in h and "A" in h for h in hazards)


def test_ambiguous_does_not_suppress_collision_check():
    """An ambiguous test that ALSO collides with another test should produce
    both error lines (ambiguity report + collision report)."""
    cases = [
        _tc("A", "-o", "x", "--project", "shared"),  # ambiguous; first match -o x
        _tc("B", "-o", "x"),  # collides with A on '-o x'
    ]
    hazards = detect_parallel_hazards(cases)
    assert any("Ambiguous" in h for h in hazards)
    assert any("Parallel hazard" in h and "A" in h and "B" in h for h in hazards)


def test_real_suite_is_clean():
    """Smoke test: the actual suite must have zero parallel hazards.

    Guards against silent regressions when new TestCases are added with
    -o/--output-dir/--project flags whose targets collide with an existing
    case (e.g. a second test using `--project test_project`).
    """
    all_tests = _MOD.all_tests
    assert detect_parallel_hazards(all_tests) == []
