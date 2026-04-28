from __future__ import annotations

from pathlib import Path

import pytest

from thoth.config_profiles import (
    ProfileSelection,
    collect_profile_catalog,
    resolve_profile_layer,
    resolve_profile_selection,
)
from thoth.errors import ConfigProfileError


def test_resolve_profile_selection_prefers_flag_over_env_and_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("THOTH_PROFILE", "env-profile")
    selection = resolve_profile_selection(
        cli_profile="flag-profile",
        base_config={"general": {"default_profile": "config-profile"}},
    )
    assert selection == ProfileSelection(
        name="flag-profile",
        source="flag",
        source_detail="--profile flag",
    )


def test_resolve_profile_selection_uses_env_before_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("THOTH_PROFILE", "env-profile")
    selection = resolve_profile_selection(
        cli_profile=None,
        base_config={"general": {"default_profile": "config-profile"}},
    )
    assert selection.name == "env-profile"
    assert selection.source == "env"
    assert selection.source_detail == "THOTH_PROFILE"


def test_resolve_profile_selection_uses_config_pointer_when_flag_and_env_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("THOTH_PROFILE", raising=False)
    selection = resolve_profile_selection(
        cli_profile=None,
        base_config={"general": {"default_profile": "config-profile"}},
    )
    assert selection.name == "config-profile"
    assert selection.source == "config"
    assert selection.source_detail == "general.default_profile"


def test_resolve_profile_selection_none_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("THOTH_PROFILE", raising=False)
    selection = resolve_profile_selection(cli_profile=None, base_config={"general": {}})
    assert selection.name is None
    assert selection.source == "none"
    assert selection.source_detail is None


def test_project_profile_shadows_user_profile_wholesale(tmp_path: Path) -> None:
    catalog = collect_profile_catalog(
        user_config={"profiles": {"prod": {"general": {"default_mode": "thinking"}}}},
        project_config={"profiles": {"prod": {"execution": {"poll_interval": 5}}}},
        user_path=tmp_path / "user.toml",
        project_path=tmp_path / "thoth.toml",
    )
    layer = resolve_profile_layer(
        ProfileSelection("prod", "flag", "--profile flag"),
        catalog,
    )
    assert layer is not None
    assert layer.tier == "project"
    assert layer.data == {"execution": {"poll_interval": 5}}


def test_collect_catalog_skips_project_when_no_project_file(tmp_path: Path) -> None:
    catalog = collect_profile_catalog(
        user_config={"profiles": {"prod": {"general": {}}}},
        project_config={},
        user_path=tmp_path / "user.toml",
        project_path=None,
    )
    assert {entry.tier for entry in catalog} == {"user"}


def test_missing_selected_profile_raises_with_source(tmp_path: Path) -> None:
    catalog = collect_profile_catalog(
        user_config={"profiles": {"prod": {"general": {"default_mode": "thinking"}}}},
        project_config={},
        user_path=tmp_path / "user.toml",
        project_path=None,
    )
    with pytest.raises(ConfigProfileError) as exc:
        resolve_profile_layer(
            ProfileSelection("prdo", "flag", "--profile flag"),
            catalog,
        )
    assert "prdo" in exc.value.message
    assert "--profile flag" in exc.value.message
    assert "prod" in (exc.value.suggestion or "")


@pytest.mark.parametrize(
    "selection,detail_substring",
    [
        (ProfileSelection("ghost", "env", "THOTH_PROFILE"), "THOTH_PROFILE"),
        (ProfileSelection("ghost", "config", "general.default_profile"), "general.default_profile"),
    ],
)
def test_missing_profile_raises_for_each_selection_source(
    tmp_path: Path,
    selection: ProfileSelection,
    detail_substring: str,
) -> None:
    catalog = collect_profile_catalog(
        user_config={"profiles": {"prod": {"general": {"default_mode": "thinking"}}}},
        project_config={},
        user_path=tmp_path / "user.toml",
        project_path=None,
    )
    with pytest.raises(ConfigProfileError) as exc:
        resolve_profile_layer(selection, catalog)
    assert detail_substring in exc.value.message
