"""Tests for thoth.modes_cmd.list_all_modes and ModeInfo."""

from __future__ import annotations

from pathlib import Path

import pytest

from thoth.config import ConfigManager
from thoth.modes_cmd import ModeInfo, list_all_modes


def _cm(isolated_thoth_home: Path, toml: str | None = None) -> ConfigManager:
    if toml is not None:
        cfg = Path(isolated_thoth_home) / "config" / "thoth" / "config.toml"
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_text(toml)
    cm = ConfigManager()
    cm.load_all_layers({})
    return cm


def test_returns_all_builtin_modes(isolated_thoth_home: Path) -> None:
    modes = list_all_modes(_cm(isolated_thoth_home))
    names = {m.name for m in modes}
    assert {"default", "clarification", "thinking", "deep_research"} <= names


def test_builtin_mode_fields_populated(isolated_thoth_home: Path) -> None:
    modes = list_all_modes(_cm(isolated_thoth_home))
    default = next(m for m in modes if m.name == "default")
    assert default.source == "builtin"
    assert default.providers == ["openai"]
    assert default.model == "o3"
    assert default.kind == "immediate"
    assert default.overrides == {}


def test_deep_research_mode_is_background(isolated_thoth_home: Path) -> None:
    modes = list_all_modes(_cm(isolated_thoth_home))
    dr = next(m for m in modes if m.name == "deep_research")
    assert dr.kind == "background"


def test_providers_list_normalization(isolated_thoth_home: Path) -> None:
    # deep_research uses `providers: ["openai"]` (list form) — must normalize.
    modes = list_all_modes(_cm(isolated_thoth_home))
    dr = next(m for m in modes if m.name == "deep_research")
    assert isinstance(dr.providers, list)
    assert dr.providers == ["openai"]


def test_user_only_mode(isolated_thoth_home: Path) -> None:
    toml = (
        'version = "2.0"\n'
        "[modes.my_brief]\n"
        'provider = "openai"\n'
        'model = "gpt-4o-mini"\n'
        'description = "my user-only mode"\n'
    )
    modes = list_all_modes(_cm(isolated_thoth_home, toml))
    mine = next(m for m in modes if m.name == "my_brief")
    assert mine.source == "user"
    assert mine.model == "gpt-4o-mini"
    assert mine.kind == "immediate"
    assert mine.overrides == {}


def test_overridden_mode_reports_diff(isolated_thoth_home: Path) -> None:
    toml = 'version = "2.0"\n[modes.deep_research]\nparallel = false\n'
    modes = list_all_modes(_cm(isolated_thoth_home, toml))
    dr = next(m for m in modes if m.name == "deep_research")
    assert dr.source == "overridden"
    assert "parallel" in dr.overrides
    assert dr.overrides["parallel"] == {"builtin": True, "effective": False}


def test_malformed_user_mode_kind_unknown(isolated_thoth_home: Path) -> None:
    # No model, no provider — must NOT crash; must surface as unknown.
    toml = 'version = "2.0"\n[modes.broken]\ndescription = "missing model and provider"\n'
    modes = list_all_modes(_cm(isolated_thoth_home, toml))
    broken = next(m for m in modes if m.name == "broken")
    assert broken.source == "user"
    assert broken.kind == "unknown"
    assert broken.warnings  # non-empty list of warning strings


def test_modeinfo_is_frozen_dataclass() -> None:
    m = ModeInfo(
        name="x",
        source="builtin",
        providers=["openai"],
        model="o3",
        kind="immediate",
        description="",
        overrides={},
        warnings=[],
        raw={},
    )
    import dataclasses

    with pytest.raises(dataclasses.FrozenInstanceError):
        m.name = "y"  # type: ignore[misc]  # ty: ignore[invalid-assignment]
