"""Tests for the `thoth config` subcommand."""

from __future__ import annotations

from pathlib import Path

import pytest

from thoth.config_cmd import config_command


def test_get_returns_merged_value(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = config_command("get", ["general.default_mode"])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == "default"


def test_get_missing_key_exits_nonzero(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = config_command("get", ["nonexistent.key"])
    assert rc == 1


def test_get_layer_defaults(isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # Write a user override, confirm --layer defaults still returns the default.
    user_toml = Path(isolated_thoth_home) / "config" / "thoth" / "config.toml"
    user_toml.parent.mkdir(parents=True, exist_ok=True)
    user_toml.write_text('version = "2.0"\n[general]\ndefault_mode = "exploration"\n')

    rc = config_command("get", ["--layer", "defaults", "general.default_mode"])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == "default"


def test_get_raw_preserves_env_template(
    isolated_thoth_home: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    rc = config_command("get", ["--raw", "providers.openai.api_key"])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == "${OPENAI_API_KEY}"
