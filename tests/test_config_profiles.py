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


from thoth.config import ConfigManager


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_config_manager_no_profile_keeps_existing_effective_config(
    isolated_thoth_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("THOTH_PROFILE", raising=False)
    cm = ConfigManager()
    cm.load_all_layers({})
    assert cm.get("general.default_mode") == "default"
    assert cm.profile_selection.name is None
    assert cm.active_profile is None


def test_config_manager_applies_profile_between_project_and_env(
    isolated_thoth_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from thoth.paths import user_config_file

    monkeypatch.setenv("THOTH_PROFILE", "fast")
    monkeypatch.setenv("THOTH_DEFAULT_MODE", "clarification")
    _write(
        user_config_file(),
        """
version = "2.0"

[general]
default_mode = "deep_research"

[profiles.fast.general]
default_mode = "thinking"
""".strip()
        + "\n",
    )

    cm = ConfigManager()
    cm.load_all_layers({})

    assert cm.get("general.default_mode") == "clarification"
    assert cm.layers["profile"]["general"]["default_mode"] == "thinking"
    assert cm.profile_selection.name == "fast"
    assert cm.active_profile is not None
    assert cm.active_profile.tier == "user"


def test_cli_setting_override_beats_active_profile(isolated_thoth_home: Path) -> None:
    from thoth.paths import user_config_file

    _write(
        user_config_file(),
        """
version = "2.0"

[profiles.fast.execution]
poll_interval = 5
""".strip()
        + "\n",
    )

    cm = ConfigManager()
    cm.load_all_layers({"_profile": "fast", "execution": {"poll_interval": 99}})

    assert cm.get("execution.poll_interval") == 99
    assert cm.layers["profile"]["execution"]["poll_interval"] == 5


def test_default_profile_pointer_survives_profile_splitting(
    isolated_thoth_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from thoth.paths import user_config_file

    monkeypatch.delenv("THOTH_PROFILE", raising=False)
    _write(
        user_config_file(),
        """
version = "2.0"

[general]
default_profile = "fast"

[profiles.fast.general]
default_mode = "thinking"
""".strip()
        + "\n",
    )

    cm = ConfigManager()
    cm.load_all_layers({})

    assert cm.get("general.default_profile") == "fast"
    assert cm.profile_selection.name == "fast"
    assert cm.profile_selection.source == "config"


def test_config_manager_uses_dot_thoth_project_file_when_present(
    isolated_thoth_home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catalog must report the actual project file used (covers both project_config_paths)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("THOTH_PROFILE", raising=False)
    _write(
        tmp_path / ".thoth" / "config.toml",
        """
version = "2.0"

[profiles.proj.general]
default_mode = "thinking"
""".strip()
        + "\n",
    )

    cm = ConfigManager()
    cm.load_all_layers({"_profile": "proj"})

    assert cm.active_profile is not None
    assert cm.active_profile.tier == "project"
    assert cm.active_profile.path == Path(".thoth/config.toml") or \
           cm.active_profile.path.name == "config.toml"


def test_thoth_profile_is_not_a_per_setting_env_override() -> None:
    """Regression guard: THOTH_PROFILE must not be added to env_mappings."""
    import inspect

    from thoth import config as thoth_config

    src = inspect.getsource(thoth_config.ConfigManager._get_env_overrides)
    assert "THOTH_PROFILE" not in src, (
        "THOTH_PROFILE belongs to Stage 1 selection (read by resolve_profile_selection), "
        "not Stage 2 per-setting overrides. See CPP REQ-CPP-004."
    )


from click.testing import CliRunner

from thoth.cli import cli


def test_root_profile_reaches_config_get(isolated_thoth_home: Path) -> None:
    from thoth.paths import user_config_file

    _write(
        user_config_file(),
        """
version = "2.0"

[profiles.fast.general]
default_mode = "thinking"
""".strip()
        + "\n",
    )

    result = CliRunner().invoke(
        cli,
        ["--profile", "fast", "config", "get", "general.default_mode"],
    )

    assert result.exit_code == 0, result.output
    assert result.output.strip().splitlines()[-1] == "thinking"


def test_unknown_root_profile_errors_before_config_get(isolated_thoth_home: Path) -> None:
    result = CliRunner().invoke(
        cli,
        ["--profile", "missing", "config", "get", "general.default_mode"],
    )

    assert result.exit_code == 1
    assert "Profile 'missing' not found" in result.output
