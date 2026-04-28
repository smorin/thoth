"""Category F — get_init_data unit tests."""

from __future__ import annotations


def test_get_init_data_returns_dict_with_config_path(isolated_thoth_home, monkeypatch):
    from thoth.commands import get_init_data

    data = get_init_data(non_interactive=True, config_path=None)
    assert isinstance(data, dict)
    assert "config_path" in data
    assert "created" in data
    assert isinstance(data["created"], bool)


def test_get_init_data_does_not_branch_on_as_json(isolated_thoth_home):
    """spec §7.2 critical invariant — `as_json` MUST NOT appear in handler signature."""
    import inspect

    from thoth.commands import get_init_data

    params = inspect.signature(get_init_data).parameters
    assert "as_json" not in params
