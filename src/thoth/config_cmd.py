"""CLI surface for the `thoth config` subcommand."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, cast

import tomlkit
from rich.console import Console

from thoth._secrets import _is_secret_key, _mask_secret
from thoth._secrets import _mask_tree as _mask_in_tree
from thoth.config import ConfigManager
from thoth.paths import user_config_file

console = Console()

_VALID_LAYERS = ("defaults", "user", "project", "env", "cli")
_ROOT_KEYS_ALLOW_UNKNOWN = ("modes",)


def _normalize_config_path(config_path: str | Path | None) -> Path | None:
    if config_path is None:
        return None
    return Path(config_path).expanduser().resolve()


def _load_manager(
    config_path: str | Path | None = None,
    *,
    profile: str | None = None,
) -> ConfigManager:
    cm = ConfigManager(_normalize_config_path(config_path))
    cli_args: dict[str, Any] = {}
    if profile:
        cli_args["_profile"] = profile
    cm.load_all_layers(cli_args)
    return cm


def _dotted_get(data: dict[str, Any], key: str) -> tuple[bool, Any]:
    current: Any = data
    for part in key.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return False, None
    return True, current


def _render_scalar(value: Any, json_format: bool) -> str:
    if json_format:
        return json.dumps(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value
    return str(value)


def get_config_get_data(
    key: str,
    *,
    layer: str | None,
    raw: bool,
    show_secrets: bool,
    config_path: str | Path | None = None,
    profile: str | None = None,
) -> dict:
    """Pure data function for `thoth config get KEY`.

    Returns a dict with keys: key, found, value, layer, masked. When
    `layer` is invalid, includes `error="INVALID_LAYER"`. Per spec §7.2,
    this function NEVER takes an `as_json` flag.
    """
    cm = _load_manager(config_path, profile=profile)

    if layer is not None:
        if layer not in _VALID_LAYERS:
            return {
                "key": key,
                "found": False,
                "value": None,
                "layer": layer,
                "masked": False,
                "error": "INVALID_LAYER",
            }
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
        return {"key": key, "found": False, "value": None, "layer": layer, "masked": False}

    masked = False
    if _is_secret_key(key) and not show_secrets:
        value = _mask_secret(value)
        masked = True

    return {
        "key": key,
        "found": True,
        "value": value,
        "layer": layer,
        "masked": masked,
    }


def _op_get(
    args: list[str],
    *,
    config_path: str | Path | None = None,
    profile: str | None = None,
) -> int:
    layer: str | None = None
    raw = False
    as_json = False
    show_secrets = False
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
        elif a == "--show-secrets":
            show_secrets = True
            i += 1
        else:
            positional.append(a)
            i += 1

    if len(positional) != 1:
        console.print("[red]Error:[/red] config get takes exactly one KEY")
        return 2
    key = positional[0]

    data = get_config_get_data(
        key,
        layer=layer,
        raw=raw,
        show_secrets=show_secrets,
        config_path=config_path,
        profile=profile,
    )

    if data.get("error") == "INVALID_LAYER":
        console.print(f"[red]Error:[/red] --layer must be one of {', '.join(_VALID_LAYERS)}")
        return 2
    if not data["found"]:
        console.print(f"[red]Error:[/red] key not found: {key}")
        return 1

    print(_render_scalar(data["value"], as_json))
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


def _target_path(project: bool, config_path: str | Path | None = None) -> Path:
    if project:
        return Path.cwd() / "thoth.toml"
    custom = _normalize_config_path(config_path)
    if custom is not None:
        return custom
    return user_config_file()


def _reject_config_project_conflict(project: bool, config_path: str | Path | None) -> bool:
    if project and config_path is not None:
        console.print("[red]Error:[/red] --config cannot be used with --project")
        return True
    return False


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


def get_config_set_data(
    key: str,
    raw_value: str,
    *,
    project: bool,
    force_string: bool,
    config_path: str | Path | None = None,
) -> dict:
    """Pure data function for `thoth config set KEY VALUE`."""
    if project and config_path is not None:
        return {
            "key": key,
            "value": None,
            "wrote": False,
            "path": None,
            "error": "PROJECT_CONFIG_CONFLICT",
        }

    value = _parse_value(raw_value, force_string)
    path = _target_path(project, config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = _load_toml_doc(path)
    _set_in_doc(doc, key, value)
    path.write_text(tomlkit.dumps(doc))
    return {"key": key, "value": value, "wrote": True, "path": str(path)}


def _op_set(args: list[str], *, config_path: str | Path | None = None) -> int:
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
    if _reject_config_project_conflict(project, config_path):
        return 2
    key, raw = positional

    value = _parse_value(raw, force_string)
    _warn_on_validation(key, value)

    data = get_config_set_data(
        key, raw, project=project, force_string=force_string, config_path=config_path
    )
    if data.get("error") == "PROJECT_CONFIG_CONFLICT":
        return 2
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


def get_config_unset_data(
    key: str, *, project: bool, config_path: str | Path | None = None
) -> dict:
    """Pure data function for `thoth config unset KEY`."""
    if project and config_path is not None:
        return {
            "key": key,
            "removed": False,
            "path": None,
            "error": "PROJECT_CONFIG_CONFLICT",
        }

    path = _target_path(project, config_path)
    if not path.exists():
        return {"key": key, "removed": False, "path": str(path), "reason": "NO_FILE"}

    doc = tomlkit.parse(path.read_text())
    removed = _unset_in_doc(doc, key)
    if not removed:
        return {"key": key, "removed": False, "path": str(path), "reason": "NOT_FOUND"}

    path.write_text(tomlkit.dumps(doc))
    return {"key": key, "removed": True, "path": str(path)}


def _op_unset(args: list[str], *, config_path: str | Path | None = None) -> int:
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
    if _reject_config_project_conflict(project, config_path):
        return 2
    key = positional[0]

    data = get_config_unset_data(key, project=project, config_path=config_path)
    if data.get("error") == "PROJECT_CONFIG_CONFLICT":
        return 2
    if data.get("reason") == "NO_FILE":
        print(f"note: {data['path']} does not exist; nothing to unset", file=sys.stderr)
        return 0
    if data.get("reason") == "NOT_FOUND":
        print(f"note: key not found: {key}", file=sys.stderr)
        return 0
    return 0


def _flatten_keys(data: dict[str, Any], prefix: str = "") -> list[str]:
    out: list[str] = []
    for k, v in data.items():
        full = k if not prefix else f"{prefix}.{k}"
        if isinstance(v, dict):
            out.extend(_flatten_keys(v, full))
        else:
            out.append(full)
    return out


def _to_plain(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: _to_plain(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_to_plain(v) for v in data]
    if isinstance(data, Path):
        return str(data)
    return data


def get_config_list_data(
    *,
    layer: str | None,
    keys_only: bool,
    show_secrets: bool,
    config_path: str | Path | None = None,
    profile: str | None = None,
) -> dict:
    """Pure data function for `thoth config list`."""
    cm = _load_manager(config_path, profile=profile)

    if layer is not None:
        if layer not in _VALID_LAYERS:
            return {
                "config": None,
                "keys": None,
                "layer": layer,
                "error": "INVALID_LAYER",
            }
        data: dict[str, Any] = cm.layers.get(layer) or {}
    else:
        data = cm.data

    if keys_only:
        return {"keys": sorted(_flatten_keys(data)), "layer": layer}

    rendered = _to_plain(data)
    if not show_secrets:
        rendered = _mask_in_tree(rendered)
    return {"config": rendered, "layer": layer}


def _op_list(
    args: list[str],
    *,
    config_path: str | Path | None = None,
    profile: str | None = None,
) -> int:
    layer: str | None = None
    keys_only = False
    as_json = False
    show_secrets = False
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--layer":
            if i + 1 >= len(args):
                console.print("[red]Error:[/red] --layer requires a value")
                return 2
            layer = args[i + 1]
            i += 2
        elif a == "--keys":
            keys_only = True
            i += 1
        elif a == "--json":
            as_json = True
            i += 1
        elif a == "--show-secrets":
            show_secrets = True
            i += 1
        elif a == "--raw":
            console.print(
                "[red]Error:[/red] --raw is only supported on 'thoth config get'; "
                "use 'thoth config list --json' for machine-readable output"
            )
            return 2
        else:
            console.print(f"[red]Error:[/red] unknown arg: {a}")
            return 2

    cm = _load_manager(config_path, profile=profile)

    if layer is not None:
        if layer not in _VALID_LAYERS:
            console.print(f"[red]Error:[/red] --layer must be one of {', '.join(_VALID_LAYERS)}")
            return 2
        data: dict[str, Any] = cm.layers.get(layer) or {}
    else:
        data = cm.data

    if keys_only:
        for key in sorted(_flatten_keys(data)):
            print(key)
        return 0

    rendered = _to_plain(data)
    if not show_secrets:
        rendered = _mask_in_tree(rendered)

    if as_json:
        print(json.dumps(rendered, indent=2, sort_keys=True))
        return 0

    print(tomlkit.dumps(rendered))
    return 0


def _parse_project_only(args: list[str], op: str) -> tuple[bool, int]:
    project = False
    for arg in args:
        if arg == "--project":
            project = True
        else:
            console.print(f"[red]Error:[/red] unknown arg for config {op}: {arg}")
            return project, 2
    return project, 0


def get_config_path_data(*, project: bool, config_path: str | Path | None = None) -> dict:
    """Pure data function for `thoth config path`."""
    if project and config_path is not None:
        return {"path": None, "project": project, "error": "PROJECT_CONFIG_CONFLICT"}
    return {"path": str(_target_path(project, config_path)), "project": project}


def _op_path(args: list[str], *, config_path: str | Path | None = None) -> int:
    project, rc = _parse_project_only(args, "path")
    if rc != 0:
        return rc
    if _reject_config_project_conflict(project, config_path):
        return 2
    data = get_config_path_data(project=project, config_path=config_path)
    print(data["path"])
    return 0


def _op_help(args: list[str], *, config_path: str | Path | None = None) -> int:
    if args:
        console.print(f"[red]Error:[/red] unknown arg for config help: {args[0]}")
        return 2
    from thoth.help import show_config_help

    show_config_help()
    return 0


def get_config_edit_data(*, project: bool, config_path: str | Path | None) -> dict:
    """Pure data function for `thoth config edit`.

    Opens `$EDITOR` on the resolved config path and returns a dict with
    the editor's exit code. Caller is responsible for translating a
    non-zero `editor_exit_code` into an EDITOR_FAILED envelope.
    """
    import os
    import shutil
    import subprocess  # noqa: S404

    if project and config_path is not None:
        return {"editor_exit_code": 2, "path": None, "error": "PROJECT_CONFIG_CONFLICT"}

    path = _target_path(project, config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        doc = tomlkit.document()
        doc["version"] = "2.0"
        path.write_text(tomlkit.dumps(doc))

    editor = os.environ.get("EDITOR") or shutil.which("vi") or "vi"
    rc = subprocess.call([editor, str(path)])  # noqa: S603
    return {"editor_exit_code": rc, "path": str(path)}


def _op_edit(args: list[str], *, config_path: str | Path | None = None) -> int:
    project, rc = _parse_project_only(args, "edit")
    if rc != 0:
        return rc
    if _reject_config_project_conflict(project, config_path):
        return 2
    data = get_config_edit_data(project=project, config_path=config_path)
    return int(data["editor_exit_code"])


def config_command(
    op: str,
    args: list[str],
    *,
    config_path: str | Path | None = None,
    profile: str | None = None,
) -> int:
    """Dispatch `thoth config <op>`. Returns a process exit code."""
    if op not in {"get", "set", "unset", "list", "path", "edit", "help"}:
        console.print(f"[red]Error:[/red] unknown config op: {op}")
        return 2

    if op == "get":
        return _op_get(args, config_path=config_path, profile=profile)
    if op == "list":
        return _op_list(args, config_path=config_path, profile=profile)
    if op == "set":
        return _op_set(args, config_path=config_path)
    if op == "unset":
        return _op_unset(args, config_path=config_path)
    if op == "path":
        return _op_path(args, config_path=config_path)
    if op == "edit":
        return _op_edit(args, config_path=config_path)
    return _op_help(args, config_path=config_path)


__all__ = [
    "config_command",
    "get_config_edit_data",
    "get_config_get_data",
    "get_config_list_data",
    "get_config_path_data",
    "get_config_set_data",
    "get_config_unset_data",
]
