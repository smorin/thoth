"""Category F — config data-function unit tests."""

from __future__ import annotations

import inspect


def test_get_config_get_data_returns_value_dict(isolated_thoth_home):
    from thoth.config_cmd import get_config_get_data

    data = get_config_get_data("paths.base_output_dir", layer=None, raw=False, show_secrets=False)
    assert isinstance(data, dict)
    assert "key" in data
    assert "value" in data
    assert "found" in data
    assert data["found"] is True


def test_get_config_get_data_missing_key_returns_not_found(isolated_thoth_home):
    from thoth.config_cmd import get_config_get_data

    data = get_config_get_data("nonexistent.key", layer=None, raw=False, show_secrets=False)
    assert data["found"] is False


def test_get_config_get_data_masks_secret_when_not_show_secrets(isolated_thoth_home, monkeypatch):
    from thoth.config_cmd import get_config_get_data

    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret-value")
    data = get_config_get_data(
        "providers.openai.api_key", layer=None, raw=False, show_secrets=False
    )
    if data["found"]:
        assert "secret" not in str(data["value"]).lower() or "***" in str(data["value"])


def test_get_config_list_data_returns_layers(isolated_thoth_home):
    from thoth.config_cmd import get_config_list_data

    data = get_config_list_data(layer=None, keys_only=False, show_secrets=False)
    assert "config" in data or "keys" in data


def test_get_config_path_data_returns_path(isolated_thoth_home):
    from thoth.config_cmd import get_config_path_data

    data = get_config_path_data(project=False)
    assert "path" in data


def test_data_functions_exclude_as_json(isolated_thoth_home):
    import thoth.config_cmd as cc

    for name in (
        "get_config_get_data",
        "get_config_set_data",
        "get_config_unset_data",
        "get_config_list_data",
        "get_config_path_data",
    ):
        fn = getattr(cc, name)
        assert "as_json" not in inspect.signature(fn).parameters, name
