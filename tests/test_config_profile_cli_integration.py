"""End-to-end CLI coverage for P21 profile propagation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from thoth.cli import cli


@pytest.fixture(autouse=True)
def _reset_config_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the process-wide --config override from leaking between tests."""
    from thoth import config as thoth_config

    monkeypatch.setattr(thoth_config, "_config_path", None)


def _write_profile_config(path: Path) -> None:
    path.write_text(
        """
version = "2.0"

[profiles.fast]
prompt_prefix = "PROFILE_FLAG"

[profiles.fast.general]
default_mode = "thinking"

[profiles.fast.providers.mock]
api_key = "test"
""".strip()
        + "\n"
    )


def test_root_profile_applies_prompt_prefix_to_ask_research(
    isolated_thoth_home: Path,
    tmp_path: Path,
) -> None:
    cfg = tmp_path / "thoth.config.toml"
    out = tmp_path / "out.txt"
    _write_profile_config(cfg)

    result = CliRunner().invoke(
        cli,
        [
            "--config",
            str(cfg),
            "--profile",
            "fast",
            "ask",
            "--mode",
            "thinking",
            "--provider",
            "mock",
            "--api-key-mock",
            "test",
            "--quiet",
            "--out",
            str(out),
            "hello",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    assert "Echo: PROFILE_FLAG\n\nhello" in out.read_text()


def test_missing_root_profile_fails_research_before_provider(
    isolated_thoth_home: Path,
    tmp_path: Path,
) -> None:
    cfg = tmp_path / "thoth.config.toml"
    out = tmp_path / "out.txt"
    _write_profile_config(cfg)

    result = CliRunner().invoke(
        cli,
        [
            "--config",
            str(cfg),
            "--profile",
            "missing",
            "ask",
            "--mode",
            "thinking",
            "--provider",
            "mock",
            "--api-key-mock",
            "test",
            "--quiet",
            "--out",
            str(out),
            "hello",
        ],
    )

    combined_error = f"{result.output}\n{result.exception!r}"
    assert result.exit_code == 1
    assert "Profile 'missing' not found" in combined_error
    assert not out.exists()


def test_profile_default_mode_used_for_bare_prompt(
    isolated_thoth_home: Path,
    tmp_path: Path,
) -> None:
    cfg = tmp_path / "thoth.config.toml"
    out = tmp_path / "out.txt"
    _write_profile_config(cfg)

    result = CliRunner().invoke(
        cli,
        [
            "--config",
            str(cfg),
            "--profile",
            "fast",
            "--provider",
            "mock",
            "--api-key-mock",
            "test",
            "--quiet",
            "--out",
            str(out),
            "hello",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    assert "# Mock streaming response (mode=thinking)" in out.read_text()


def test_providers_check_honors_root_profile_provider_key(
    isolated_thoth_home: Path,
    tmp_path: Path,
) -> None:
    cfg = tmp_path / "thoth.config.toml"
    _write_profile_config(cfg)

    result = CliRunner().invoke(
        cli,
        [
            "--config",
            str(cfg),
            "--profile",
            "fast",
            "providers",
            "check",
            "--provider",
            "mock",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    assert "set" in result.output
    assert "missing" not in result.output


def test_config_get_json_missing_profile_emits_json_error(
    isolated_thoth_home: Path,
    tmp_path: Path,
) -> None:
    cfg = tmp_path / "thoth.config.toml"
    _write_profile_config(cfg)

    result = CliRunner().invoke(
        cli,
        [
            "--config",
            str(cfg),
            "--profile",
            "missing",
            "config",
            "get",
            "general.default_mode",
            "--json",
        ],
    )

    assert result.exit_code == 1
    assert result.output.startswith("{"), result.output or repr(result.exception)
    payload = json.loads(result.output)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "CONFIG_PROFILE_ERROR"
    assert "Profile 'missing' not found" in payload["error"]["message"]
