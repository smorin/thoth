"""P16 PR2 — Category B: legacy-form gating tests.

Each removed form must exit 2 with a Click-native error containing the
`(use 'thoth NEW_FORM')` migration substring on stderr per Q6-PR2-C1.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from thoth.cli import cli


@pytest.mark.parametrize(
    "argv,migration_hint",
    [
        # --resume / -R global flag (removed in Task 5)
        (["--resume", "op_x"], "thoth resume"),
        (["-R", "op_x"], "thoth resume"),
    ],
)
def test_resume_legacy_form_gated(argv, migration_hint):
    r = CliRunner().invoke(cli, argv)
    assert r.exit_code == 2, f"expected exit 2, got {r.exit_code}\noutput={r.output!r}"
    assert migration_hint in r.output, (
        f"expected migration hint {migration_hint!r} in output, got {r.output!r}"
    )


@pytest.mark.parametrize(
    "argv,migration_hint",
    [
        # providers `--` separator form
        (["providers", "--", "--list"], "thoth providers list"),
        (["providers", "--", "--models"], "thoth providers models"),
        (["providers", "--", "--keys"], "thoth providers check"),
        (["providers", "--", "--refresh-cache"], "thoth providers models --refresh-cache"),
        (["providers", "--", "--no-cache"], "thoth providers models --no-cache"),
        # providers in-group hidden flag form (PR1.5 shim)
        (["providers", "--list"], "thoth providers list"),
        (["providers", "--models"], "thoth providers models"),
        (["providers", "--keys"], "thoth providers check"),
        (["providers", "--check"], "thoth providers check"),
    ],
)
def test_providers_legacy_form_gated(argv, migration_hint):
    r = CliRunner().invoke(cli, argv)
    assert r.exit_code == 2, f"expected exit 2, got {r.exit_code}\noutput={r.output!r}"
    combined = r.output or ""
    assert migration_hint in combined, (
        f"expected migration hint {migration_hint!r} in output, got {combined!r}"
    )


@pytest.mark.parametrize(
    "argv,migration_hint",
    [
        (["modes", "--json"], "thoth modes list --json"),
        (["modes", "--show-secrets"], "thoth modes list --show-secrets"),
        (["modes", "--full"], "thoth modes list --full"),
        (["modes", "--name", "deep_research"], "thoth modes list --name"),
        (["modes", "--source", "user"], "thoth modes list --source"),
    ],
)
def test_modes_legacy_form_gated(argv, migration_hint):
    r = CliRunner().invoke(cli, argv)
    assert r.exit_code == 2, f"expected exit 2, got {r.exit_code}\noutput={r.output!r}"
    combined = r.output or ""
    assert migration_hint in combined, f"hint {migration_hint!r} not in output {combined!r}"


def test_help_auth_parse_time_hijack_removed():
    """Q5-A row 13.ii: `thoth --help auth` is no longer hijacked at parse time."""
    r = CliRunner().invoke(cli, ["--help", "auth"])
    # Click natively rejects 'auth' as an unexpected positional argument,
    # OR `--help` consumes the rest and exits 0 with the group help.
    # Either way, the OLD behavior (rendering auth-help) must NOT happen.
    combined = r.output or ""
    # The old hijack rendered "Authentication" prominently; verify that's gone.
    assert "Authentication" not in combined or r.exit_code != 0


def test_help_subcommand_topic_still_works():
    """`thoth help status` still forwards to `thoth status --help`."""
    r = CliRunner().invoke(cli, ["help", "status"])
    assert r.exit_code == 0, r.output
    assert "OP_ID" in r.output or "status" in r.output.lower()


def test_help_auth_topic_via_help_subcommand_removed():
    """The `auth` virtual topic on `thoth help auth` is dropped per Q5-A row 13.ii."""
    r = CliRunner().invoke(cli, ["help", "auth"])
    assert r.exit_code == 2, r.output
    combined = r.output or ""
    assert "unknown help topic" in combined.lower() or "available topics" in combined.lower()
