"""P16 PR2 — Category D: --raw x --show-secrets security matrix (Q4-PR2-D)."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from thoth.cli import cli


@pytest.fixture
def secret_config(isolated_thoth_home, monkeypatch):
    """Set a known secret value via env-layer override."""
    fake_key = "sk-" + "FAKE-VALUE-FOR-TESTS-ONLY"  # noqa: S105 — test fixture
    monkeypatch.setenv("OPENAI_API_KEY", fake_key)
    return fake_key


# --raw alone — masks (NEW behavior post-Q4-D)
def test_get_secret_raw_masks(secret_config):
    r = CliRunner().invoke(cli, ["config", "get", "providers.openai.api_key", "--raw"])
    assert r.exit_code == 0, r.output
    assert secret_config not in r.output
    # --raw reads pre-substitution layer data; either the unresolved template
    # or a mask is acceptable — both prevent leakage of the real secret.
    assert "${OPENAI_API_KEY}" in r.output or "***" in r.output or "REDACTED" in r.output


# --show-secrets alone — reveals
def test_get_secret_show_secrets_reveals(secret_config):
    r = CliRunner().invoke(cli, ["config", "get", "providers.openai.api_key", "--show-secrets"])
    assert r.exit_code == 0, r.output
    assert secret_config in r.output


# --raw + --show-secrets — reveals
def test_get_secret_raw_and_show_secrets_reveals(secret_config):
    r = CliRunner().invoke(
        cli,
        ["config", "get", "providers.openai.api_key", "--raw", "--show-secrets"],
    )
    assert r.exit_code == 0, r.output
    # With --raw, value is the unresolved template; --show-secrets ensures no
    # masking is applied, so the template literal must appear.
    assert "${OPENAI_API_KEY}" in r.output


# Neither flag — masks
def test_get_secret_no_flags_masks(secret_config):
    r = CliRunner().invoke(cli, ["config", "get", "providers.openai.api_key"])
    assert r.exit_code == 0, r.output
    assert secret_config not in r.output


# Non-secret + --raw — still works (formatting flag)
def test_get_non_secret_with_raw(isolated_thoth_home):
    r = CliRunner().invoke(cli, ["config", "get", "general.default_mode", "--raw"])
    assert r.exit_code == 0, r.output
    assert r.output.strip() == "default"


# Non-secret + --show-secrets — works (no-op for non-secrets)
def test_get_non_secret_with_show_secrets(isolated_thoth_home):
    r = CliRunner().invoke(cli, ["config", "get", "general.default_mode", "--show-secrets"])
    assert r.exit_code == 0, r.output
    assert "default" in r.output


# --json + secret + no --show-secrets — masks
def test_get_secret_json_masks(secret_config):
    r = CliRunner().invoke(cli, ["config", "get", "providers.openai.api_key", "--json"])
    assert r.exit_code == 0, r.output
    assert secret_config not in r.output


# --json + secret + --show-secrets — reveals
def test_get_secret_json_show_secrets_reveals(secret_config):
    r = CliRunner().invoke(
        cli,
        ["config", "get", "providers.openai.api_key", "--json", "--show-secrets"],
    )
    assert r.exit_code == 0, r.output
    assert secret_config in r.output


# I3 (PR2 review-fix): `config list --raw` is rejected with a clear message.
# `--raw` is a per-layer get-only concept; for machine-readable list output
# the user should use `config list --json`.
def test_list_raw_rejected_with_clear_message(isolated_thoth_home):
    r = CliRunner().invoke(cli, ["config", "list", "--raw"])
    assert r.exit_code == 2, r.output
    out = r.output.lower()
    assert "--raw" in out
    assert "config get" in out or "--json" in out
