"""Tests for get_config() and ConfigManager wiring."""

from __future__ import annotations

from thoth.__main__ import ConfigManager, get_config


def test_get_config_returns_config_manager() -> None:
    """get_config() must return a fully-loaded ConfigManager (not the legacy Config shim)."""
    cfg = get_config()
    assert isinstance(cfg, ConfigManager)
    # Must be loaded: ConfigManager() alone leaves .data empty until load_all_layers runs.
    assert cfg.data, "expected get_config() to return a loaded ConfigManager"
    assert "providers" in cfg.data
