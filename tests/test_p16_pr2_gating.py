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
