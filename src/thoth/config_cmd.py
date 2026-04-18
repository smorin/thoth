"""CLI surface for the `thoth config` subcommand."""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console

from thoth.config import ConfigManager

console = Console()

_VALID_LAYERS = ("defaults", "user", "project", "env", "cli")


def _load_manager() -> ConfigManager:
    cm = ConfigManager()
    cm.load_all_layers({})
    return cm


def _dotted_get(data: dict[str, Any], key: str) -> tuple[bool, Any]:
    current: Any = data
    for part in key.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return False, None
    return True, current


def _render_scalar(value: Any, as_json: bool) -> str:
    if as_json:
        return json.dumps(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value
    return str(value)


def _op_get(args: list[str]) -> int:
    layer: str | None = None
    raw = False
    as_json = False
    positional: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--layer":
            if i + 1 >= len(args):
                console.print("[red]Error:[/red] --layer requires a value")
                return 2
            layer = args[i + 1]
            i += 2
        elif a == "--raw":
            raw = True
            i += 1
        elif a == "--json":
            as_json = True
            i += 1
        else:
            positional.append(a)
            i += 1

    if len(positional) != 1:
        console.print("[red]Error:[/red] config get takes exactly one KEY")
        return 2
    key = positional[0]

    cm = _load_manager()

    if layer is not None:
        if layer not in _VALID_LAYERS:
            console.print(f"[red]Error:[/red] --layer must be one of {', '.join(_VALID_LAYERS)}")
            return 2
        data = cm.layers.get(layer, {})
    elif raw:
        merged: dict[str, Any] = {}
        for name in _VALID_LAYERS:
            layer_data = cm.layers.get(name) or {}
            merged = cm._deep_merge(merged, layer_data)
        data = merged
    else:
        data = cm.data

    found, value = _dotted_get(data, key)
    if not found:
        console.print(f"[red]Error:[/red] key not found: {key}")
        return 1

    print(_render_scalar(value, as_json))
    return 0


def config_command(op: str, args: list[str]) -> int:
    """Dispatch `thoth config <op>`. Returns a process exit code."""
    ops = {
        "get": _op_get,
    }
    if op not in ops:
        console.print(f"[red]Error:[/red] unknown config op: {op}")
        return 2
    return ops[op](args)


__all__ = ["config_command"]
