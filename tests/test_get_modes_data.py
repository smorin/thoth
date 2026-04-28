"""Category F — modes data-function unit tests."""

from __future__ import annotations

import inspect


def test_get_modes_list_data_returns_modes_list(isolated_thoth_home):
    from thoth.modes_cmd import get_modes_list_data

    data = get_modes_list_data(name=None, source="all", show_secrets=False)
    assert "modes" in data
    assert any(m["name"] == "default" for m in data["modes"])


def test_get_modes_list_data_filters_by_name(isolated_thoth_home):
    from thoth.modes_cmd import get_modes_list_data

    data = get_modes_list_data(name="default", source="all", show_secrets=False)
    assert data["mode"]["name"] == "default"


def test_get_modes_list_data_unknown_name_returns_none(isolated_thoth_home):
    from thoth.modes_cmd import get_modes_list_data

    data = get_modes_list_data(name="not-a-real-mode", source="all", show_secrets=False)
    assert data["mode"] is None


def test_signature_excludes_as_json(isolated_thoth_home):
    from thoth.modes_cmd import get_modes_list_data

    assert "as_json" not in inspect.signature(get_modes_list_data).parameters
