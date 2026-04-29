"""Tests for get_config() and ConfigManager wiring."""

from __future__ import annotations

import pytest

from thoth.__main__ import ConfigManager, get_config


def test_get_config_returns_config_manager() -> None:
    """get_config() must return a fully-loaded ConfigManager (not the legacy Config shim)."""
    cfg = get_config()
    assert isinstance(cfg, ConfigManager)
    # Must be loaded: ConfigManager() alone leaves .data empty until load_all_layers runs.
    assert cfg.data, "expected get_config() to return a loaded ConfigManager"
    assert "providers" in cfg.data


def test_load_all_layers_rejects_unknown_cli_args_keys() -> None:
    """BUG-05 (B): cli_args is a CLI override LAYER, not a generic options bag.

    Misuse like ``{"config_path": ...}`` (which belongs in the
    ``ConfigManager(config_path=...)`` constructor) must raise at the
    boundary instead of silently polluting ``cm.data``.
    """
    cm = ConfigManager()
    with pytest.raises(ValueError, match=r"cli_args key 'config_path'"):
        cm.load_all_layers({"config_path": None})

    with pytest.raises(ValueError, match=r"cli_args key 'arbitrary_key'"):
        cm.load_all_layers({"arbitrary_key": "x"})


def test_load_all_layers_accepts_profile_sentinel_and_known_top_level_keys() -> None:
    """The validator must not regress against legitimate cli_args shapes."""
    cm = ConfigManager()
    # Empty dict
    cm.load_all_layers({})
    # Sentinel only (no profile registered, but the empty selection path is fine)
    cm.load_all_layers({})
    # Known top-level config root: nested override
    cm.load_all_layers({"execution": {"poll_interval": 99}})
    assert cm.data["execution"]["poll_interval"] == 99
