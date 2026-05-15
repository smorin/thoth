from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from doxa_research.cli import cli
from doxa_research.config import ConfigManager
from doxa_research.config_profiles import (
    ProfileSelection,
    collect_profile_catalog,
    resolve_profile_layer,
    resolve_profile_selection,
)
from doxa_research.errors import ConfigProfileError


def test_resolve_profile_selection_prefers_flag_over_env_and_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DOXA_PROFILE", "env-profile")
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
    monkeypatch.setenv("DOXA_PROFILE", "env-profile")
    selection = resolve_profile_selection(
        cli_profile=None,
        base_config={"general": {"default_profile": "config-profile"}},
    )
    assert selection.name == "env-profile"
    assert selection.source == "env"
    assert selection.source_detail == "DOXA_PROFILE"


def test_resolve_profile_selection_uses_config_pointer_when_flag_and_env_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DOXA_PROFILE", raising=False)
    selection = resolve_profile_selection(
        cli_profile=None,
        base_config={"general": {"default_profile": "config-profile"}},
    )
    assert selection.name == "config-profile"
    assert selection.source == "config"
    assert selection.source_detail == "general.default_profile"


def test_resolve_profile_selection_none_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DOXA_PROFILE", raising=False)
    selection = resolve_profile_selection(cli_profile=None, base_config={"general": {}})
    assert selection.name is None
    assert selection.source == "none"
    assert selection.source_detail is None


def test_project_profile_shadows_user_profile_wholesale(tmp_path: Path) -> None:
    catalog = collect_profile_catalog(
        user_config={"profiles": {"prod": {"general": {"default_mode": "thinking"}}}},
        project_config={"profiles": {"prod": {"execution": {"poll_interval": 5}}}},
        user_path=tmp_path / "user.toml",
        project_path=tmp_path / "doxa.config.toml",
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
        (ProfileSelection("ghost", "env", "DOXA_PROFILE"), "DOXA_PROFILE"),
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


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_config_manager_no_profile_keeps_existing_effective_config(
    isolated_doxa_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DOXA_PROFILE", raising=False)
    cm = ConfigManager()
    cm.load_all_layers({})
    assert cm.get("general.default_mode") == "default"
    assert cm.profile_selection.name is None
    assert cm.active_profile is None


def test_config_manager_applies_profile_between_project_and_env(
    isolated_doxa_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from doxa_research.paths import user_config_file

    monkeypatch.setenv("DOXA_PROFILE", "fast")
    monkeypatch.setenv("DOXA_DEFAULT_MODE", "clarification")
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


def test_cli_setting_override_beats_active_profile(isolated_doxa_home: Path) -> None:
    from doxa_research.paths import user_config_file

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
    isolated_doxa_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from doxa_research.paths import user_config_file

    monkeypatch.delenv("DOXA_PROFILE", raising=False)
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


def test_config_manager_uses_dot_doxa_project_file_when_present(
    isolated_doxa_home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catalog must report the actual project file used (covers both project_config_paths)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DOXA_PROFILE", raising=False)
    _write(
        tmp_path / ".doxa.config.toml",
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
    assert (
        cm.active_profile.path == Path(".doxa.config.toml")
        or cm.active_profile.path.name == "doxa.config.toml"
    )


def test_doxa_profile_is_not_a_per_setting_env_override() -> None:
    """Regression guard (structural): DOXA_PROFILE must not be added to env_mappings.

    Brittle under refactor — a future move of env_mappings to a module-level
    constant would silently bypass this check. See the companion behavioral
    guard ``test_doxa_profile_does_not_leak_into_env_layer_at_runtime`` for
    the refactor-safe check (BUG-06).
    """
    import inspect

    from doxa_research import config as doxa_config

    src = inspect.getsource(doxa_config.ConfigManager._get_env_overrides)
    assert "DOXA_PROFILE" not in src, (
        "DOXA_PROFILE belongs to Stage 1 selection (read by resolve_profile_selection), "
        "not Stage 2 per-setting overrides. See CPP REQ-CPP-004."
    )


def test_doxa_profile_does_not_leak_into_env_layer_at_runtime(
    isolated_doxa_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BUG-06 (behavioral): regardless of how env mappings are structured
    (literal-in-method or module-level constant), setting DOXA_PROFILE in
    the environment must NOT produce a per-setting override in the env
    layer. DOXA_PROFILE is a Stage 1 selector (read by
    ``resolve_profile_selection``), not a Stage 2 per-setting value.
    """
    monkeypatch.setenv("DOXA_PROFILE", "ghost-profile")
    cm = ConfigManager()
    overrides = cm._get_env_overrides()
    # The selector value must not appear anywhere in the env-override layer.
    assert "ghost-profile" not in repr(overrides), (
        f"DOXA_PROFILE leaked into env overrides as a per-setting value: {overrides!r}"
    )


def test_root_profile_reaches_config_get(isolated_doxa_home: Path) -> None:
    from doxa_research.paths import user_config_file

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


def test_unknown_root_profile_errors_before_config_get(isolated_doxa_home: Path) -> None:
    result = CliRunner().invoke(
        cli,
        ["--profile", "missing", "config", "get", "general.default_mode"],
    )

    assert result.exit_code == 1
    assert "Profile 'missing' not found" in result.output
