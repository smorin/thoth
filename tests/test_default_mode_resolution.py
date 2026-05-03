"""Tests for `_config_default_mode` precedence chain (P35-TS05)."""

from __future__ import annotations

from pathlib import Path

import pytest

from thoth.cli import _config_default_mode
from thoth.config import ConfigManager
from thoth.config_cmd import get_config_profile_add_data, get_modes_set_default_data


def test_resolution_empty_returns_default(isolated_thoth_home: Path) -> None:
    cm = ConfigManager()
    cm.load_all_layers()
    assert _config_default_mode(cm) == "default"


def test_resolution_general_default_mode(isolated_thoth_home: Path) -> None:
    get_modes_set_default_data("deep_research", project=False, profile=None, config_path=None)
    cm = ConfigManager()
    cm.load_all_layers()
    assert _config_default_mode(cm) == "deep_research"


def test_resolution_active_profile_overrides_general(isolated_thoth_home: Path) -> None:
    get_config_profile_add_data("work", project=False, config_path=None)
    get_modes_set_default_data("deep_research", project=False, profile=None, config_path=None)
    get_modes_set_default_data("quick_research", project=False, profile="work", config_path=None)

    cm = ConfigManager()
    cm.load_all_layers({"_profile": "work"})
    assert _config_default_mode(cm) == "quick_research"


def test_resolution_profile_without_default_mode_falls_through(
    isolated_thoth_home: Path,
) -> None:
    get_config_profile_add_data("work", project=False, config_path=None)
    get_modes_set_default_data("deep_research", project=False, profile=None, config_path=None)

    cm = ConfigManager()
    cm.load_all_layers({"_profile": "work"})
    assert _config_default_mode(cm) == "deep_research"


def test_resolution_env_beats_profile(
    isolated_thoth_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    get_config_profile_add_data("work", project=False, config_path=None)
    get_modes_set_default_data("quick_research", project=False, profile="work", config_path=None)
    monkeypatch.setenv("THOTH_DEFAULT_MODE", "thinking")

    cm = ConfigManager()
    cm.load_all_layers({"_profile": "work"})
    assert _config_default_mode(cm) == "thinking"


def test_resolution_inactive_profile_default_is_ignored(
    isolated_thoth_home: Path,
) -> None:
    """Profile X has default_mode but X is not active -> only general counts."""
    get_config_profile_add_data("work", project=False, config_path=None)
    get_modes_set_default_data("quick_research", project=False, profile="work", config_path=None)
    get_modes_set_default_data("deep_research", project=False, profile=None, config_path=None)

    # No --profile -> no active profile -> fall through to general.
    cm = ConfigManager()
    cm.load_all_layers()
    assert _config_default_mode(cm) == "deep_research"
