"""CLI surface for the `thoth modes` subcommand.

Single source of truth for mode enumeration: `list_all_modes(cm)` returns a
list of `ModeInfo` objects covering built-in modes (from `BUILTIN_MODES`),
user-defined modes (from `[modes.*]` in user/project TOML), and modes that
override a builtin (present in both).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, cast

from thoth.config import BUILTIN_MODES, ConfigManager, is_background_mode

Source = Literal["builtin", "user", "overridden"]
Kind = Literal["immediate", "background", "unknown"]


@dataclass(frozen=True)
class ModeInfo:
    name: str
    source: Source
    providers: list[str]
    model: str | None
    kind: Kind
    description: str
    overrides: dict[str, dict[str, Any]]
    warnings: list[str]
    raw: dict[str, Any]


def _normalize_providers(cfg: dict[str, Any]) -> list[str]:
    if "providers" in cfg and isinstance(cfg["providers"], list):
        return [str(p) for p in cfg["providers"]]
    if "provider" in cfg:
        return [str(cfg["provider"])]
    return []


def _derive_kind(cfg: dict[str, Any], warnings: list[str]) -> Kind:
    if not cfg.get("model") and "async" not in cfg:
        warnings.append("missing `model` and no explicit `async` — kind unknown")
        return "unknown"
    return "background" if is_background_mode(cfg) else "immediate"


def _compute_overrides(builtin: dict[str, Any], user: dict[str, Any]) -> dict[str, dict[str, Any]]:
    diff: dict[str, dict[str, Any]] = {}
    for key in sorted(set(builtin) | set(user)):
        b_val = builtin.get(key)
        u_val = user.get(key, b_val)
        if key in user and u_val != b_val:
            diff[key] = {"builtin": b_val, "effective": u_val}
    return diff


def list_all_modes(cm: ConfigManager) -> list[ModeInfo]:
    """Enumerate every research mode known to Thoth.

    Merges `BUILTIN_MODES` with user `[modes.*]` tables exposed by the
    ConfigManager. Each `ModeInfo` carries enough data for table, JSON, or
    detail-view rendering.
    """
    user_modes: dict[str, Any] = cm.data.get("modes") or {}
    names = sorted(set(BUILTIN_MODES) | set(user_modes))

    infos: list[ModeInfo] = []
    for name in names:
        builtin_cfg = BUILTIN_MODES.get(name, {})
        user_cfg = user_modes.get(name) or {}
        merged: dict[str, Any] = {**builtin_cfg, **user_cfg}

        if name in BUILTIN_MODES and name in user_modes:
            source: Source = "overridden"
        elif name in BUILTIN_MODES:
            source = "builtin"
        else:
            source = "user"

        warnings: list[str] = []
        kind = _derive_kind(merged, warnings)
        providers = _normalize_providers(merged)
        overrides = _compute_overrides(builtin_cfg, user_cfg) if source == "overridden" else {}

        infos.append(
            ModeInfo(
                name=name,
                source=source,
                providers=providers,
                model=cast("str | None", merged.get("model")),
                kind=kind,
                description=str(merged.get("description", "")),
                overrides=overrides,
                warnings=warnings,
                raw=merged,
            )
        )
    return infos


__all__ = ["ModeInfo", "list_all_modes"]
