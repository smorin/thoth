"""CLI surface for the `thoth config` subcommand."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, cast

import tomlkit
from rich.console import Console

from thoth.config import ConfigManager
from thoth.paths import user_config_file

console = Console()

_VALID_LAYERS = ("defaults", "user", "project", "env", "cli")
_ROOT_KEYS_ALLOW_UNKNOWN = ("modes",)


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


def _parse_value(raw: str, force_string: bool) -> Any:
    if force_string:
        return raw
    lower = raw.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except ValueError:
        return raw


def _target_path(project: bool) -> Path:
    if project:
        return Path.cwd() / "thoth.toml"
    return user_config_file()


def _load_toml_doc(path: Path) -> tomlkit.TOMLDocument:
    if path.exists():
        return tomlkit.parse(path.read_text())
    doc = tomlkit.document()
    doc["version"] = "2.0"
    return doc


def _warn_on_validation(key: str, value: Any) -> None:
    from thoth.config import ConfigSchema

    defaults = ConfigSchema.get_defaults()
    parts = key.split(".")
    if parts[0] in _ROOT_KEYS_ALLOW_UNKNOWN:
        return
    if parts[0] not in defaults:
        console.print(f"[yellow]Warning:[/yellow] unknown root key: {parts[0]}")
        return

    current: Any = defaults
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return
    if type(current) is not type(value) and current is not None:
        console.print(
            f"[yellow]Warning:[/yellow] type mismatch: default for {key} "
            f"is {type(current).__name__}, got {type(value).__name__}"
        )


def _set_in_doc(doc: tomlkit.TOMLDocument, key: str, value: Any) -> None:
    parts = key.split(".")
    current = cast(Any, doc)
    for part in parts[:-1]:
        existing = current[part] if part in current else None
        if existing is None or not hasattr(existing, "keys"):
            new_table = tomlkit.table()
            current[part] = new_table
            current = cast(Any, new_table)
        else:
            current = cast(Any, existing)
    current[parts[-1]] = value


def _op_set(args: list[str]) -> int:
    project = False
    force_string = False
    positional: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--project":
            project = True
            i += 1
        elif a == "--string":
            force_string = True
            i += 1
        else:
            positional.append(a)
            i += 1

    if len(positional) != 2:
        console.print("[red]Error:[/red] config set takes KEY VALUE")
        return 2
    key, raw = positional

    value = _parse_value(raw, force_string)
    _warn_on_validation(key, value)

    path = _target_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = _load_toml_doc(path)
    _set_in_doc(doc, key, value)
    path.write_text(tomlkit.dumps(doc))
    return 0


def _unset_in_doc(doc: tomlkit.TOMLDocument, key: str) -> bool:
    parts = key.split(".")
    stack: list[Any] = [cast(Any, doc)]
    current = cast(Any, doc)
    for part in parts[:-1]:
        if part not in current:
            return False
        child = current[part]
        if not hasattr(child, "keys"):
            return False
        current = cast(Any, child)
        stack.append(current)

    leaf = parts[-1]
    if leaf not in current:
        return False
    del current[leaf]

    for container, part in zip(reversed(stack[:-1]), reversed(parts[:-1]), strict=True):
        child = container[part]
        if hasattr(child, "keys") and len(child) == 0:
            del container[part]
        else:
            break
    return True


def _op_unset(args: list[str]) -> int:
    project = False
    positional: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--project":
            project = True
            i += 1
        else:
            positional.append(a)
            i += 1

    if len(positional) != 1:
        console.print("[red]Error:[/red] config unset takes KEY")
        return 2
    key = positional[0]

    path = _target_path(project)
    if not path.exists():
        print(f"note: {path} does not exist; nothing to unset", file=sys.stderr)
        return 0

    doc = tomlkit.parse(path.read_text())
    removed = _unset_in_doc(doc, key)
    if not removed:
        print(f"note: key not found: {key}", file=sys.stderr)
        return 0

    path.write_text(tomlkit.dumps(doc))
    return 0


def config_command(op: str, args: list[str]) -> int:
    """Dispatch `thoth config <op>`. Returns a process exit code."""
    ops = {
        "get": _op_get,
        "set": _op_set,
        "unset": _op_unset,
    }
    if op not in ops:
        console.print(f"[red]Error:[/red] unknown config op: {op}")
        return 2
    return ops[op](args)


__all__ = ["config_command"]
