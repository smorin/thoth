"""CLI surface for the `thoth modes` subcommand.

Single source of truth for mode enumeration: `list_all_modes(cm)` returns a
list of `ModeInfo` objects covering built-in modes (from `BUILTIN_MODES`),
user-defined modes (from `[modes.*]` in user/project TOML), and modes that
override a builtin (present in both).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, cast

from rich.console import Console
from rich.table import Table

from thoth._secrets import _mask_tree
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
_VALID_SOURCES = ("builtin", "user", "overridden", "all")
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


def _info_to_dict(m: ModeInfo, show_secrets: bool) -> dict[str, Any]:
    d = asdict(m)
    if not show_secrets:
        d["raw"] = _mask_tree(d["raw"])
        d["overrides"] = _mask_tree(d["overrides"])
    return d


def _parse_list_flags(
    args: list[str],
) -> tuple[bool, bool, str, str | None, bool, int]:
    """Return (as_json, show_secrets, source, name, full, error_rc). rc=0 means ok."""
    as_json = False
    show_secrets = False
    source = "all"
    name: str | None = None
    full = False
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--json":
            as_json = True
            i += 1
        elif a == "--show-secrets":
            show_secrets = True
            i += 1
        elif a == "--full":
            full = True
            i += 1
        elif a == "--source":
            if i + 1 >= len(args):
                _get_console().print("[red]Error:[/red] --source requires a value")
                return as_json, show_secrets, source, name, full, 2
            source = args[i + 1]
            if source not in _VALID_SOURCES:
                _get_console().print(
                    f"[red]Error:[/red] --source must be one of {', '.join(_VALID_SOURCES)}"
                )
                return as_json, show_secrets, source, name, full, 2
            i += 2
        elif a == "--name":
            if i + 1 >= len(args):
                _get_console().print("[red]Error:[/red] --name requires a value")
                return as_json, show_secrets, source, name, full, 2
            name = args[i + 1]
            i += 2
        else:
            _get_console().print(f"[red]Error:[/red] unknown arg: {a}")
            return as_json, show_secrets, source, name, full, 2
    return as_json, show_secrets, source, name, full, 0


def _render_detail(m: ModeInfo, full: bool, show_secrets: bool) -> None:
    console = _get_console()
    providers = ",".join(m.providers) if m.providers else "-"
    console.print(f"Mode: {m.name}")
    console.print(f"Source: {m.source}")
    console.print(f"Providers: {providers}")
    console.print(f"Model: {m.model or '-'}")
    console.print(f"Kind: {m.kind}")
    if m.description:
        console.print(f"Description: {m.description}")
    if m.warnings:
        for w in m.warnings:
            console.print(f"[yellow]Warning:[/yellow] {w}")
    if m.overrides:
        console.print("Overrides (builtin → effective):")
        rendered = _mask_tree(m.overrides) if not show_secrets else m.overrides
        for key, diff in rendered.items():
            console.print(f"  {key}: {diff['builtin']!r} → {diff['effective']!r}")
    system_prompt = m.raw.get("system_prompt")
    if system_prompt:
        if full:
            console.print("System prompt:")
            console.print(system_prompt)
        else:
            preview = _truncate(str(system_prompt), 200)
            console.print(f"System prompt: {preview} [dim](use --full to see)[/dim]")


def get_modes_list_data(
    *,
    name: str | None,
    source: str,
    show_secrets: bool,
    config_path: str | None = None,
) -> dict:
    """Pure data function for `thoth modes list`.

    Returns:
        - {"modes": [...]} when `name` is None
        - {"mode": {...} | None} when `name` is set
    Per spec §7.2, this function NEVER takes an `as_json` flag — the
    JSON-vs-Rich choice lives at the subcommand-wrapper layer.
    """
    cm = ConfigManager(Path(config_path).expanduser().resolve() if config_path else None)
    cm.load_all_layers({})
    infos = list_all_modes(cm)

    if source != "all":
        infos = [m for m in infos if m.source == source]

    if name is not None:
        match = next((m for m in infos if m.name == name), None)
        return {"mode": _info_to_dict(match, show_secrets) if match else None}

    infos = sorted(infos, key=_sort_key)
    return {
        "schema_version": "1",
        "modes": [_info_to_dict(m, show_secrets) for m in infos],
    }


def _op_list(args: list[str], *, config_path: str | None = None) -> int:
    as_json, show_secrets, source, name, full, rc = _parse_list_flags(args)
    if rc != 0:
        return rc

    cm = ConfigManager(Path(config_path).expanduser().resolve() if config_path else None)
    cm.load_all_layers({})
    infos = list_all_modes(cm)

    # Q5-A row 11.i: source filter is applied BEFORE the --name short-circuit
    # so `--name X --source Y` is a true intersection (empty result if X is
    # not in source Y).
    if source != "all":
        infos = [m for m in infos if m.source == source]

    if name is not None:
        match = next((m for m in infos if m.name == name), None)
        if match is None:
            if as_json:
                print(
                    json.dumps(
                        {"schema_version": "1", "mode": None},
                        indent=2,
                        sort_keys=True,
                    )
                )
            return 0
        if as_json:
            print(
                json.dumps(
                    {
                        "schema_version": "1",
                        "mode": _info_to_dict(match, show_secrets),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            _render_detail(match, full, show_secrets)
        return 0

    infos = sorted(infos, key=_sort_key)

    if as_json:
        payload = {
            "schema_version": "1",
            "modes": [_info_to_dict(m, show_secrets) for m in infos],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    _render_table(infos)
    return 0


def modes_command(op: str | None, args: list[str], *, config_path: str | None = None) -> int:
    """Dispatch `thoth modes <op>`. Returns a process exit code."""
    if op is None:
        return _op_list(args, config_path=config_path)
    ops = {"list": _op_list}
    if op not in ops:
        _get_console().print(f"[red]Error:[/red] unknown modes op: {op}")
        return 2
    return ops[op](args, config_path=config_path)


__all__ = ["ModeInfo", "get_modes_list_data", "list_all_modes", "modes_command"]
