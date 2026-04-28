"""Category F — providers data-function unit tests."""

from __future__ import annotations

import inspect


def test_get_providers_list_data_returns_providers_dict(stub_config):
    from thoth.commands import get_providers_list_data

    data = get_providers_list_data(stub_config, filter_provider=None)
    assert isinstance(data, dict)
    assert "providers" in data
    assert isinstance(data["providers"], list)
    for entry in data["providers"]:
        assert "name" in entry
        assert "key_set" in entry


def test_get_providers_list_data_filters_by_provider(stub_config):
    from thoth.commands import get_providers_list_data

    data = get_providers_list_data(stub_config, filter_provider="openai")
    assert all(entry["name"] == "openai" for entry in data["providers"])


def test_get_providers_models_data_returns_models_per_provider(stub_config):
    from thoth.commands import get_providers_models_data

    data = get_providers_models_data(stub_config, filter_provider=None)
    assert "providers" in data
    for provider_entry in data["providers"]:
        assert "name" in provider_entry
        assert isinstance(provider_entry["models"], list)


def test_get_providers_check_data_returns_missing_list(stub_config):
    from thoth.commands import get_providers_check_data

    data = get_providers_check_data(stub_config)
    assert "missing" in data
    assert "complete" in data


def test_data_functions_exclude_as_json(stub_config):
    from thoth.commands import (
        get_providers_check_data,
        get_providers_list_data,
        get_providers_models_data,
    )

    for fn in (get_providers_list_data, get_providers_models_data, get_providers_check_data):
        assert "as_json" not in inspect.signature(fn).parameters
