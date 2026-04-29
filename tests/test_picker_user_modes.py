"""Tests for `immediate_models_for_provider` walking the merged config (BUG-06)."""

from __future__ import annotations

from pathlib import Path

from thoth.config import ConfigManager
from thoth.interactive_picker import immediate_models_for_provider


def _config_with_modes(tmp_path: Path, body: str) -> ConfigManager:
    cfg_file = tmp_path / "thoth.config.toml"
    cfg_file.write_text('version = "2.0"\n' + body)
    cm = ConfigManager(cfg_file)
    cm.load_all_layers()
    return cm


def test_user_mode_appears_in_picker(tmp_path: Path):
    cm = _config_with_modes(
        tmp_path,
        '[modes.custom_quick]\nprovider = "openai"\nmodel = "gpt-4o-2024-11-20"\n',
    )
    models = immediate_models_for_provider("openai", cm)
    assert "gpt-4o-2024-11-20" in models


def test_picker_excludes_background_models(tmp_path: Path):
    cm = _config_with_modes(tmp_path, "")
    models = immediate_models_for_provider("openai", cm)
    assert all("deep-research" not in m for m in models)


def test_picker_no_openai_hardcoded_extras_when_unconfigured(tmp_path: Path):
    """Provider symmetry: openai is no longer special-cased with hardcoded
    {'o3', 'gpt-4o-mini', 'gpt-4o'} extras. The picker reflects the config."""
    cm = _config_with_modes(
        tmp_path,
        '[modes.tiny]\nprovider = "perplexity"\nmodel = "sonar-small"\n',
    )
    perp = immediate_models_for_provider("perplexity", cm)
    assert "sonar-small" in perp


def test_picker_provider_filter(tmp_path: Path):
    cm = _config_with_modes(
        tmp_path,
        "[modes.openai_quick]\n"
        'provider = "openai"\n'
        'model = "openai-only"\n'
        "\n"
        "[modes.mock_quick]\n"
        'provider = "mock"\n'
        'model = "mock-only"\n',
    )
    openai_models = immediate_models_for_provider("openai", cm)
    mock_models = immediate_models_for_provider("mock", cm)
    assert "openai-only" in openai_models
    assert "openai-only" not in mock_models
    assert "mock-only" in mock_models
    assert "mock-only" not in openai_models
