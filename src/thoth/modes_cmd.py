"""CLI surface for the `thoth modes` subcommand.

Single source of truth for mode enumeration: `list_all_modes(cm)` returns a
list of `ModeInfo` objects covering built-in modes (from `BUILTIN_MODES`),
user-defined modes (from `[modes.*]` in user/project TOML), and modes that
override a builtin (present in both).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Literal, cast

from rich.console import Console
from rich.table import Table

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


_SOURCE_ORDER = {"builtin": 0, "overridden": 1, "user": 2}
_KIND_ORDER = {"immediate": 0, "background": 1, "unknown": 2}


def _get_console() -> Console:
    """Construct a Rich Console at each render call so width is resolved
    dynamically (respects terminal width in production and the COLUMNS env
    var in tests)."""
    return Console()


def _sort_key(m: ModeInfo) -> tuple[int, int, str, str, str]:
    return (
        _SOURCE_ORDER.get(m.source, 99),
        _KIND_ORDER.get(m.kind, 99),
        ",".join(m.providers),
        m.model or "",
        m.name,
    )


def _truncate(text: str, limit: int = 60) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _render_table(infos: list[ModeInfo]) -> None:
    table = Table(show_header=True, header_style="bold")
    table.add_column("Mode", no_wrap=True)
    table.add_column("Source")
    table.add_column("Provider")
    table.add_column("Model")
    table.add_column("Kind")
    table.add_column("Description")

    for m in sorted(infos, key=_sort_key):
        table.add_row(
            f" {m.name} ",
            m.source,
            ",".join(m.providers) if m.providers else "-",
            m.model or "-",
            m.kind,
            _truncate(m.description),
        )
    _get_console().print(table)


_SECRET_KEY_SUFFIX = "api_key"


def _is_secret_key(key: str) -> bool:
    return key.split(".")[-1] == _SECRET_KEY_SUFFIX


def _mask_secret(value: Any) -> Any:
    if not isinstance(value, str) or not value:
        return value
    if value.startswith("${") and value.endswith("}"):
        return value
    tail = value[-4:] if len(value) >= 4 else value
    return f"****{tail}"


def _mask_tree(data: Any, prefix: str = "") -> Any:
    if isinstance(data, dict):
        return {k: _mask_tree(v, f"{prefix}.{k}" if prefix else k) for k, v in data.items()}
    if isinstance(data, list):
        return [_mask_tree(v, prefix) for v in data]
    if prefix and _is_secret_key(prefix):
        return _mask_secret(data)
    return data


def _info_to_dict(m: ModeInfo, show_secrets: bool) -> dict[str, Any]:
    d = asdict(m)
    if not show_secrets:
        d["raw"] = _mask_tree(d["raw"])
        d["overrides"] = _mask_tree(d["overrides"])
    return d


def _parse_list_flags(args: list[str]) -> tuple[bool, bool]:
    as_json = "--json" in args
    show_secrets = "--show-secrets" in args
    return as_json, show_secrets


def _op_list(args: list[str]) -> int:
    as_json, show_secrets = _parse_list_flags(args)
    cm = ConfigManager()
    cm.load_all_layers({})
    infos = sorted(list_all_modes(cm), key=_sort_key)

    if as_json:
        payload = {
            "schema_version": "1",
            "modes": [_info_to_dict(m, show_secrets) for m in infos],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    _render_table(infos)
    return 0


def modes_command(op: str | None, args: list[str]) -> int:
    """Dispatch `thoth modes <op>`. Returns a process exit code."""
    if op is None:
        return _op_list(args)
    ops = {"list": _op_list}
    if op not in ops:
        _get_console().print(f"[red]Error:[/red] unknown modes op: {op}")
        return 2
    return ops[op](args)


__all__ = ["ModeInfo", "list_all_modes", "modes_command"]
