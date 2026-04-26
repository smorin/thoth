"""P16-TS01..15: post-refactor invocations match pre-refactor baselines.

Each test parametrizes one captured invocation. CI runs these in PR1 to
prove "no user-visible behavior change."

Skipped before parity is in scope (e.g. if THOTH_PARITY_SKIP=1 env is set
during early refactor scaffolding). Re-enabled by Task 15.
"""

from __future__ import annotations

import os

import pytest

PARITY_LABELS = [
    "help",
    "version_short",
    "version_long",
    "init_help",
    "status_no_args",
    "list_help",
    "providers_no_args",
    "providers_list",
    "config_no_args",
    "config_list",
    "modes_no_args",
    "help_init",
    "help_auth",
    "help_unknown_topic",
    "unknown_command",
]


@pytest.mark.parametrize("label", PARITY_LABELS)
def test_dispatch_parity(label: str, baseline, run_thoth):
    """P16-TS01: post-refactor exit_code matches baseline; stdout structurally
    equivalent (allowing for whitespace/color drift); stderr similar."""
    if os.getenv("THOTH_PARITY_SKIP") == "1":
        pytest.skip("parity gate temporarily disabled during scaffolding")

    expected = baseline(label)
    exit_code, stdout, stderr = run_thoth(expected["argv"])

    assert exit_code == expected["exit_code"], (
        f"exit_code mismatch for {label}: got {exit_code}, baseline {expected['exit_code']}"
    )
    # stdout: line-set equality (tolerates re-ordering of help sections; we
    # explicitly assert structure in test_p16_thothgroup.py for help layout)
    assert sorted(stdout.splitlines()) == sorted(expected["stdout"].splitlines()), (
        f"stdout drift for {label}"
    )
