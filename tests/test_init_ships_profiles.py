"""P21-T10: `thoth init` ships example profiles users can customize.

The generated `~/.config/thoth/config.toml` should contain:
  - daily          — thinking + default project for daily notes
  - quick          — thinking (immediate)
  - openai_deep    — single-provider deep_research
  - all_deep       — parallel openai+perplexity deep_research
  - interactive    — interactive default mode
  - deep_research  — deep_research with a `prompt_prefix` example
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from thoth.commands import CommandHandler
from thoth.config import ConfigManager
from thoth.config_profiles import resolve_prompt_prefix


@pytest.fixture(autouse=True)
def _reset_config_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep CLI --config tests from leaking into later tests."""
    from thoth import config as thoth_config

    monkeypatch.setattr(thoth_config, "_config_path", None)


@pytest.fixture
def init_run(isolated_thoth_home: Path) -> Path:
    """Run init_command against the isolated XDG config dir, return config path."""
    from thoth.paths import user_config_file

    handler = CommandHandler(ConfigManager())
    handler.init_command()
    path = user_config_file()
    assert path.exists(), f"init did not create config at {path}"
    return path


def test_init_writes_parseable_config(init_run: Path) -> None:
    cm = ConfigManager()
    cm.load_all_layers({})
    # Every shipped profile should be in the catalog.
    names = {entry.name for entry in cm.profile_catalog}
    assert {
        "daily",
        "quick",
        "openai_deep",
        "all_deep",
        "interactive",
        "deep_research",
    }.issubset(names)


@pytest.mark.parametrize(
    "profile_name,expected_default_mode",
    [
        ("daily", "thinking"),
        ("quick", "thinking"),
        ("openai_deep", "deep_research"),
        ("all_deep", "deep_research"),
        ("interactive", "interactive"),
        ("deep_research", "deep_research"),
    ],
)
def test_each_shipped_profile_sets_expected_default_mode(
    init_run: Path, profile_name: str, expected_default_mode: str
) -> None:
    cm = ConfigManager()
    cm.load_all_layers({"_profile": profile_name})
    assert cm.profile_selection.name == profile_name
    assert cm.get("general.default_mode") == expected_default_mode


def test_openai_deep_profile_uses_single_provider(init_run: Path) -> None:
    cm = ConfigManager()
    cm.load_all_layers({"_profile": "openai_deep"})
    deep = cm.data["modes"]["deep_research"]
    assert deep.get("providers") == ["openai"]
    assert deep.get("parallel") is False


def test_all_deep_profile_uses_parallel_providers(init_run: Path) -> None:
    cm = ConfigManager()
    cm.load_all_layers({"_profile": "all_deep"})
    deep = cm.data["modes"]["deep_research"]
    assert deep.get("providers") == ["openai", "perplexity"]
    assert deep.get("parallel") is True


def test_deep_research_profile_carries_prompt_prefix(init_run: Path) -> None:
    cm = ConfigManager()
    cm.load_all_layers({"_profile": "deep_research"})
    prefix = resolve_prompt_prefix(cm, "deep_research")
    assert prefix is not None
    assert len(prefix) > 0


def test_build_profile_section_preserves_sibling_subsections() -> None:
    """C14: siblings sharing a prefix (e.g., modes.deep_research + modes.thinking)
    must coexist under the same intermediate table, not overwrite each other."""
    from thoth.commands import _build_profile_section

    body = {
        "modes.deep_research": {"providers": ["openai"], "parallel": False},
        "modes.thinking": {"prompt_prefix": "Think hard."},
    }
    table = _build_profile_section(body)
    modes = table.get("modes")
    assert modes is not None, "modes intermediate table missing"
    assert "deep_research" in modes, (
        f"deep_research silently dropped; modes keys = {list(modes.keys())}"
    )
    assert "thinking" in modes, f"thinking silently dropped; modes keys = {list(modes.keys())}"
    # Full content must round-trip — not just keys
    assert modes["deep_research"]["providers"] == ["openai"]
    assert modes["deep_research"]["parallel"] is False
    assert modes["thinking"]["prompt_prefix"] == "Think hard."


def test_cli_init_custom_config_path_writes_starter_profiles(
    isolated_thoth_home: Path,
    tmp_path: Path,
) -> None:
    from thoth.cli import cli

    target = tmp_path / "custom-thoth.toml"
    result = CliRunner().invoke(cli, ["--config", str(target), "init"])

    assert result.exit_code == 0, result.output
    assert target.exists()
    text = target.read_text()
    assert "[profiles.daily.general]" in text
    assert "[profiles.deep_research.modes.deep_research]" in text


def test_cli_init_json_non_interactive_writes_starter_profiles(
    isolated_thoth_home: Path,
    tmp_path: Path,
) -> None:
    import json

    from thoth.cli import cli

    target = tmp_path / "json-thoth.toml"
    result = CliRunner().invoke(
        cli,
        ["--config", str(target), "init", "--json", "--non-interactive"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["data"]["created"] is True
    text = target.read_text()
    assert "[profiles.daily.general]" in text
    assert "[profiles.deep_research.modes.deep_research]" in text
