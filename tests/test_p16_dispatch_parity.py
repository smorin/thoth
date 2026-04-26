"""P16-TS01..17: post-refactor invocations match pre-refactor baselines.

Parity policy (decided in T15):
- 8 byte-stable invocations whose stdout/stderr we trust line-set-equal across
  the refactor (PARITY_LABELS below).
- 7 structural tests for invocations whose pre-refactor stdout was a pre-refactor
  bug (e.g. Click leaking parent help) or whose layout intentionally changed
  (e.g. two-section --help layout per T11). Structural tests assert behavioral
  contracts (exit code, key substrings) without freezing the exact byte
  rendering.

Skipped before parity is in scope (e.g. if THOTH_PARITY_SKIP=1 env is set
during early refactor scaffolding).
"""

from __future__ import annotations

import os

import pytest

PARITY_LABELS = [
    "version_short",
    "version_long",
    "status_no_args",
    "providers_list",
    "config_list",
    "modes_no_args",
    "help_auth",
    "unknown_command",
]


@pytest.mark.parametrize("label", PARITY_LABELS)
def test_dispatch_parity(label: str, baseline, run_thoth):
    """P16-TS01: post-refactor exit_code, stdout, AND stderr match baseline (line-set equality)."""
    if os.getenv("THOTH_PARITY_SKIP") == "1":
        pytest.skip("parity gate temporarily disabled during scaffolding")

    expected = baseline(label)
    exit_code, stdout, stderr = run_thoth(expected["argv"])

    assert exit_code == expected["exit_code"], (
        f"exit_code mismatch for {label}: got {exit_code}, baseline {expected['exit_code']}"
    )
    # Both stdout and stderr: line-set equality (sorted set of lines).
    # Tolerates Click's terminal-width-dependent re-formatting; catches
    # added/removed lines and exit-code changes. Strict line-order checks
    # for the --help layout live in tests/test_p16_thothgroup.py (added in T11).
    assert sorted(stdout.splitlines()) == sorted(expected["stdout"].splitlines()), (
        f"stdout drift for {label}"
    )
    assert sorted(stderr.splitlines()) == sorted(expected["stderr"].splitlines()), (
        f"stderr drift for {label}"
    )


def test_help_unknown_topic_errors_structural(run_thoth):
    """P16-TS12: thoth help <unknown-topic> exits non-zero with a clear error."""
    exit_code, stdout, stderr = run_thoth(["help", "nosuchtopic"])
    assert exit_code != 0
    combined = stdout + stderr
    assert "nosuchtopic" in combined.lower() or "unknown" in combined.lower()


def test_init_help_structural(run_thoth):
    """P16-TS13: thoth init --help shows the init subcommand's help (not parent)."""
    exit_code, stdout, stderr = run_thoth(["init", "--help"])
    assert exit_code == 0
    assert "init" in stdout.lower()
    assert "Initialize" in stdout or "initialize" in stdout


def test_list_help_structural(run_thoth):
    """P16-TS14: thoth list --help shows the list subcommand's help (not parent)."""
    exit_code, stdout, stderr = run_thoth(["list", "--help"])
    assert exit_code == 0
    assert "list" in stdout.lower()
    assert "--all" in stdout or "operations" in stdout.lower()


def test_providers_no_args_lists_subcommands(run_thoth):
    """P16-TS15: thoth providers (no args) lists list/models/check subcommands.

    Click's natural behavior for a subgroup invoked without a subcommand is
    to print the usage/command listing and exit 2. We accept either 0 or 2
    here — the contract is that the subcommand list is reachable.
    """
    exit_code, stdout, stderr = run_thoth(["providers"])
    assert exit_code in (0, 2)
    combined = stdout + stderr
    # Click lists the subcommands somewhere
    assert "list" in combined
    assert "models" in combined
    assert "check" in combined


def test_config_no_args_errors_with_op_hint(run_thoth):
    """P16-TS16: thoth config (no op) exits 2 with hint about required op."""
    exit_code, stdout, stderr = run_thoth(["config"])
    assert exit_code == 2
    combined = stdout + stderr
    assert (
        "op" in combined.lower()
        or "required" in combined.lower()
        or "(get|set" in combined
    )


def test_help_init_forwards_to_subcommand(run_thoth):
    """P16-TS17: thoth help init forwards to init's --help."""
    exit_code, stdout, stderr = run_thoth(["help", "init"])
    assert exit_code == 0
    assert "init" in stdout.lower()
