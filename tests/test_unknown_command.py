"""P36 Layer 1: uniform `--help` + unknown-command dispatch tests.

These tests exercise the subprocess path via the `run_doxa` fixture
(defined in tests/conftest_p16.py) so we observe the same dispatch
behavior the user sees, with no API keys leaking from the parent env.
"""

from __future__ import annotations

# `run_doxa` is autoloaded from tests/conftest_p16.py via tests/conftest.py.


def test_help_works_for_unknown_command(run_doxa):
    """`doxa profiles --help` → exit 2, structured 'unknown command' error.

    Must include the typed name in the title, the curated did-you-mean
    pointer at `doxa config profiles`, and the registered top-level
    command listing header.
    """
    exit_code, stdout, stderr = run_doxa(["profiles", "--help"])
    assert exit_code == 2, (exit_code, stdout, stderr)
    combined = stdout + stderr
    assert "unknown command 'profiles'" in combined, combined
    assert "Did you mean 'doxa config profiles'" in combined, combined
    assert "Available top-level commands:" in combined, combined


def test_unknown_single_token_no_help_flag(run_doxa):
    """`doxa profiles` (no --help) → exit 2 with the same error.

    The single-token unknown-command branch must intercept this BEFORE the
    bare-prompt fallback can swallow it as a research prompt.
    """
    exit_code, stdout, stderr = run_doxa(["profiles"])
    assert exit_code == 2, (exit_code, stdout, stderr)
    combined = stdout + stderr
    assert "unknown command 'profiles'" in combined, combined
    assert "Available top-level commands:" in combined, combined


def test_help_works_for_registered_command(run_doxa):
    """`doxa modes --help` → click's standard help (regression check)."""
    exit_code, stdout, stderr = run_doxa(["modes", "--help"])
    assert exit_code == 0, (exit_code, stdout, stderr)
    assert "--help" in stdout, stdout


def test_help_works_for_builtin_mode(run_doxa):
    """`doxa default --help` → mode dispatch preserved (no unknown-command capture).

    The L1 short-circuit must NOT swallow builtin-mode invocations;
    they fall through to the existing mode-positional dispatch in Path 2.
    The exact exit code / output of that dispatcher is out of L1's scope.
    """
    exit_code, stdout, stderr = run_doxa(["default", "--help"])
    combined = stdout + stderr
    assert "unknown command" not in combined, combined


def test_bare_prompt_multi_token_falls_through(run_doxa):
    """`doxa quantum gravity` → bare-prompt fallback preserved.

    With no API keys in the fixture's env, this will likely surface the
    API-key error from the runner. We assert only that the unknown-command
    branch did NOT capture it (multi-token strings are research prompts).
    """
    exit_code, stdout, stderr = run_doxa(["quantum", "gravity"])
    combined = stdout + stderr
    assert "unknown command" not in combined, combined


def test_help_flag_short_form(run_doxa):
    """`doxa profiles -h` → same path as --help."""
    exit_code, stdout, stderr = run_doxa(["profiles", "-h"])
    assert exit_code == 2, (exit_code, stdout, stderr)
    combined = stdout + stderr
    assert "unknown command 'profiles'" in combined, combined


def test_unknown_command_lists_full_command_set(run_doxa):
    """The error's command listing must enumerate registered top-level commands."""
    exit_code, stdout, stderr = run_doxa(["profiles", "--help"])
    assert exit_code == 2
    combined = stdout + stderr
    # Spot-check a few we know are registered (P16+).
    for name in ("config", "modes", "providers"):
        assert name in combined, f"missing {name!r} in: {combined}"
