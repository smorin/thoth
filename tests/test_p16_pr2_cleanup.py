"""P16 PR2 — Category C: Q5-A cleanup-batch tests."""

from __future__ import annotations

from click.testing import CliRunner

from thoth.cli import cli


def test_providers_models_refresh_and_no_cache_mutex():
    """Q5-A row 1: --refresh-cache and --no-cache are mutually exclusive."""
    r = CliRunner().invoke(cli, ["providers", "models", "--refresh-cache", "--no-cache"])
    assert r.exit_code == 2, r.output
    combined = r.output or ""
    assert "mutually exclusive" in combined.lower() or "cannot use" in combined.lower()
