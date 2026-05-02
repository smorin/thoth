"""Tests for `thoth modes set-default NAME` — data layer (P35)."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from thoth.config_cmd import (
    get_config_profile_add_data,
    get_modes_set_default_data,
)
from thoth.errors import ConfigProfileError


def test_set_default_general_writes_user_config(isolated_thoth_home: Path) -> None:
    out = get_modes_set_default_data("deep_research", project=False, profile=None, config_path=None)
    assert out["wrote"] is True
    assert out["default_mode"] == "deep_research"
    assert "profile" not in out

    from thoth.paths import user_config_file

    data = tomllib.loads(user_config_file().read_text())
    assert data["general"]["default_mode"] == "deep_research"


def test_set_default_general_accepts_builtin(isolated_thoth_home: Path) -> None:
    out = get_modes_set_default_data("default", project=False, profile=None, config_path=None)
    assert out["wrote"] is True


def test_set_default_general_rejects_unknown_mode(isolated_thoth_home: Path) -> None:
    with pytest.raises(Exception) as excinfo:
        get_modes_set_default_data(
            "no-such-mode",
            project=False,
            profile=None,
            config_path=None,
        )
    msg = str(excinfo.value)
    assert "no-such-mode" in msg or "not found" in msg.lower()


def test_set_default_project_conflicts_with_config_path(tmp_path: Path) -> None:
    out = get_modes_set_default_data(
        "deep_research",
        project=True,
        profile=None,
        config_path=tmp_path / "custom.toml",
    )
    assert out["error"] == "PROJECT_CONFIG_CONFLICT"
    assert out["wrote"] is False


def test_set_default_to_custom_config_path(tmp_path: Path) -> None:
    custom = tmp_path / "custom.toml"
    out = get_modes_set_default_data(
        "deep_research", project=False, profile=None, config_path=custom
    )
    assert out["wrote"] is True
    data = tomllib.loads(custom.read_text())
    assert data["general"]["default_mode"] == "deep_research"


# --- Profile scope: same-tier rule ---


def test_set_default_profile_writes_profile_key(isolated_thoth_home: Path) -> None:
    get_config_profile_add_data("work", project=False, config_path=None)
    out = get_modes_set_default_data(
        "deep_research", project=False, profile="work", config_path=None
    )
    assert out["wrote"] is True
    assert out["default_mode"] == "deep_research"
    assert out["profile"] == "work"

    from thoth.paths import user_config_file

    data = tomllib.loads(user_config_file().read_text())
    assert data["profiles"]["work"]["default_mode"] == "deep_research"


def test_set_default_profile_rejects_when_profile_missing_in_target_user(
    isolated_thoth_home: Path,
) -> None:
    """Same-tier rule: profile must exist in target tier (user, in this case)."""
    with pytest.raises(ConfigProfileError) as excinfo:
        get_modes_set_default_data(
            "deep_research",
            project=False,
            profile="ghost",
            config_path=None,
        )
    assert "ghost" in str(excinfo.value)


def test_set_default_profile_rejects_when_profile_only_in_other_tier(
    isolated_thoth_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Profile defined only in user; writing to --project tier rejects."""
    get_config_profile_add_data("work", project=False, config_path=None)
    # Switch CWD so project config lands in tmp_path.
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigProfileError):
        get_modes_set_default_data(
            "deep_research",
            project=True,
            profile="work",
            config_path=None,
        )


def test_set_default_profile_accepts_builtin_mode_cross_tier(
    isolated_thoth_home: Path,
) -> None:
    """β: mode NAME can be a builtin even in profile scope."""
    get_config_profile_add_data("work", project=False, config_path=None)
    out = get_modes_set_default_data(
        "default",
        project=False,
        profile="work",
        config_path=None,
    )
    assert out["wrote"] is True


def test_set_default_profile_rejects_unknown_mode(isolated_thoth_home: Path) -> None:
    get_config_profile_add_data("work", project=False, config_path=None)
    with pytest.raises(Exception) as excinfo:
        get_modes_set_default_data(
            "ghost-mode",
            project=False,
            profile="work",
            config_path=None,
        )
    assert "ghost-mode" in str(excinfo.value)
