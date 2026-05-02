"""Tests for `thoth modes unset-default` — data layer (P35)."""

from __future__ import annotations

import tomllib
from pathlib import Path

from thoth.config_cmd import (
    get_config_profile_add_data,
    get_modes_set_default_data,
    get_modes_unset_default_data,
)


def test_unset_default_general_removes_key(isolated_thoth_home: Path) -> None:
    get_modes_set_default_data("deep_research", project=False, profile=None, config_path=None)
    out = get_modes_unset_default_data(project=False, profile=None, config_path=None)
    assert out["removed"] is True

    from thoth.paths import user_config_file

    data = tomllib.loads(user_config_file().read_text())
    assert "default_mode" not in data.get("general", {})
    # B17: empty [general] table is preserved.
    assert "general" in data


def test_unset_default_general_no_file_returns_no_file(tmp_path: Path) -> None:
    custom = tmp_path / "absent.toml"
    out = get_modes_unset_default_data(project=False, profile=None, config_path=custom)
    assert out["removed"] is False
    assert out["reason"] == "NO_FILE"


def test_unset_default_general_key_absent_returns_not_found(
    isolated_thoth_home: Path,
) -> None:
    # Pre-create user config without default_mode.
    from thoth.config_document import ConfigDocument
    from thoth.paths import user_config_file

    doc = ConfigDocument.load(user_config_file())
    doc.save()  # writes empty doc
    out = get_modes_unset_default_data(project=False, profile=None, config_path=None)
    assert out["removed"] is False
    assert out["reason"] == "NOT_FOUND"


def test_unset_default_profile_removes_key(isolated_thoth_home: Path) -> None:
    get_config_profile_add_data("work", project=False, config_path=None)
    get_modes_set_default_data("deep_research", project=False, profile="work", config_path=None)
    out = get_modes_unset_default_data(project=False, profile="work", config_path=None)
    assert out["removed"] is True
    assert out["profile"] == "work"


def test_unset_default_profile_idempotent_without_profile_check(
    isolated_thoth_home: Path,
) -> None:
    """δ: unset does NOT enforce same-tier profile-existence."""
    out = get_modes_unset_default_data(project=False, profile="never-existed", config_path=None)
    assert out["removed"] is False
    # No ConfigProfileError raised.


def test_unset_default_project_conflicts_with_config_path(tmp_path: Path) -> None:
    out = get_modes_unset_default_data(
        project=True,
        profile=None,
        config_path=tmp_path / "x.toml",
    )
    assert out["error"] == "PROJECT_CONFIG_CONFLICT"
