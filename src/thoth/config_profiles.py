"""Configuration profile resolution for Thoth."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from thoth.errors import ConfigProfileError

ProfileSelectionSource = Literal["flag", "env", "config", "none"]
ProfileTier = Literal["project", "user"]


@dataclass(frozen=True)
class ProfileSelection:
    name: str | None
    source: ProfileSelectionSource
    source_detail: str | None


@dataclass(frozen=True)
class ProfileLayer:
    name: str
    tier: ProfileTier
    path: Path
    data: dict[str, Any]


def _profiles_from(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = config.get("profiles") or {}
    if not isinstance(raw, dict):
        return {}
    return {str(name): value for name, value in raw.items() if isinstance(value, dict)}


def collect_profile_catalog(
    *,
    user_config: dict[str, Any],
    project_config: dict[str, Any],
    user_path: Path,
    project_path: Path | None,
) -> list[ProfileLayer]:
    catalog: list[ProfileLayer] = []
    for name, data in _profiles_from(user_config).items():
        catalog.append(ProfileLayer(name=name, tier="user", path=user_path, data=data))
    if project_path is not None:
        for name, data in _profiles_from(project_config).items():
            catalog.append(ProfileLayer(name=name, tier="project", path=project_path, data=data))
    return catalog


def resolve_profile_selection(
    *,
    cli_profile: str | None,
    base_config: dict[str, Any],
) -> ProfileSelection:
    if cli_profile:
        return ProfileSelection(cli_profile, "flag", "--profile flag")
    env_profile = os.getenv("THOTH_PROFILE")
    if env_profile:
        return ProfileSelection(env_profile, "env", "THOTH_PROFILE")
    general = base_config.get("general") or {}
    config_profile = general.get("default_profile") if isinstance(general, dict) else None
    if config_profile:
        return ProfileSelection(str(config_profile), "config", "general.default_profile")
    return ProfileSelection(None, "none", None)


def resolve_profile_layer(
    selection: ProfileSelection,
    catalog: list[ProfileLayer],
) -> ProfileLayer | None:
    if selection.name is None:
        return None

    matches = [entry for entry in catalog if entry.name == selection.name]
    if not matches:
        available = sorted({entry.name for entry in catalog})
        raise ConfigProfileError(
            f"Profile {selection.name!r} not found",
            available_profiles=available,
            source=selection.source_detail,
        )

    project_matches = [entry for entry in matches if entry.tier == "project"]
    if project_matches:
        return project_matches[-1]
    return matches[-1]


def without_profiles(config: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in config.items() if key != "profiles"}
