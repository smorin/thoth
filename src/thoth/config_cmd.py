"""CLI surface for the `thoth config` subcommand."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import tomlkit
from rich.console import Console

from thoth._secrets import _is_secret_key, _mask_secret
from thoth._secrets import _mask_tree as _mask_in_tree
from thoth.config import ConfigManager
from thoth.config_write_context import ConfigWriteContext

console = Console()

_VALID_LAYERS = ("defaults", "user", "project", "profile", "env", "cli")
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
    return ConfigWriteContext.resolve(project=project, config_path=config_path).target_path


def _write_context(project: bool, config_path: str | Path | None = None) -> ConfigWriteContext:
    return ConfigWriteContext.resolve(project=project, config_path=config_path)


def _reject_config_project_conflict(project: bool, config_path: str | Path | None) -> bool:
    if project and config_path is not None:
        console.print("[red]Error:[/red] --config cannot be used with --project")
        return True
    return False


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
    context = _write_context(project, config_path)
    doc = context.load_document()
    doc.set_config_value(key, value)
    doc.save()
    return {"key": key, "value": value, "wrote": True, "path": str(context.target_path)}


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

    context = _write_context(project, config_path)
    path = context.target_path
    if not path.exists():
        return {"key": key, "removed": False, "path": str(path), "reason": "NO_FILE"}

    doc = context.load_document()
    removed = doc.unset_config_value(key, prune_empty=True)
    if not removed:
        return {"key": key, "removed": False, "path": str(path), "reason": "NOT_FOUND"}

    doc.save()
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

    context = _write_context(project, config_path)
    path = context.target_path
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        context.load_document().save()

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


def get_config_profile_add_data(
    name: str,
    *,
    project: bool,
    config_path: str | Path | None = None,
) -> dict:
    """Pure data function for `thoth config profiles add NAME`.

    Idempotent: if the profile already exists, returns
    ``{"created": False, ...}`` without touching the file.
    """
    if project and config_path is not None:
        return {
            "profile": name,
            "created": False,
            "path": None,
            "error": "PROJECT_CONFIG_CONFLICT",
        }

    context = _write_context(project, config_path)
    doc = context.load_document()
    created = doc.ensure_profile(name)
    if not created:
        return {"profile": name, "created": False, "path": str(context.target_path)}

    doc.save()
    return {"profile": name, "created": True, "path": str(context.target_path)}


def get_config_profile_remove_data(
    name: str,
    *,
    project: bool,
    config_path: str | Path | None = None,
) -> dict:
    """Pure data function for `thoth config profiles remove NAME`.

    Idempotent: if the profile doesn't exist, returns
    ``{"removed": False, ...}`` without touching the file.
    """
    if project and config_path is not None:
        return {
            "profile": name,
            "removed": False,
            "path": None,
            "error": "PROJECT_CONFIG_CONFLICT",
        }

    context = _write_context(project, config_path)
    path = context.target_path
    if not path.exists():
        return {
            "profile": name,
            "removed": False,
            "unset_default_profile": False,
            "path": str(path),
        }

    doc = context.load_document()
    removed = doc.remove_profile(name)
    if not removed:
        return {
            "profile": name,
            "removed": False,
            "unset_default_profile": False,
            "path": str(path),
        }

    unset_default = doc.unset_default_profile_if(name)
    doc.save()
    return {
        "profile": name,
        "removed": True,
        "unset_default_profile": unset_default,
        "path": str(path),
    }


def get_config_profile_set_data(
    name: str,
    key: str,
    raw_value: str,
    *,
    project: bool,
    force_string: bool,
    config_path: str | Path | None = None,
) -> dict:
    """Pure data function for `thoth config profiles set NAME KEY VALUE`."""
    if project and config_path is not None:
        return {
            "profile": name,
            "key": key,
            "value": None,
            "wrote": False,
            "path": None,
            "error": "PROJECT_CONFIG_CONFLICT",
        }

    value = _parse_value(raw_value, force_string)
    context = _write_context(project, config_path)
    doc = context.load_document()
    doc.set_profile_value(name, key, value)
    doc.save()
    return {
        "profile": name,
        "key": key,
        "value": value,
        "wrote": True,
        "path": str(context.target_path),
    }


def get_config_profile_unset_data(
    name: str,
    key: str,
    *,
    project: bool,
    config_path: str | Path | None = None,
) -> dict:
    """Pure data function for `thoth config profiles unset NAME KEY`.

    Removes only the named leaf; empty parent tables are left in place
    (B17). The ConfigDocument profile API keeps the profile name literal
    and only treats KEY as a dotted config path.
    """
    if project and config_path is not None:
        return {
            "profile": name,
            "key": key,
            "removed": False,
            "path": None,
            "error": "PROJECT_CONFIG_CONFLICT",
        }

    context = _write_context(project, config_path)
    path = context.target_path
    if not path.exists():
        return {
            "profile": name,
            "key": key,
            "removed": False,
            "path": str(path),
            "reason": "NO_FILE",
        }

    doc = context.load_document()
    removed = doc.unset_profile_value(name, key)
    if not removed:
        return {
            "profile": name,
            "key": key,
            "removed": False,
            "path": str(path),
            "reason": "NOT_FOUND",
        }

    doc.save()
    return {"profile": name, "key": key, "removed": True, "path": str(path)}


def get_config_profile_show_data(
    name: str,
    *,
    show_secrets: bool,
    config_path: str | Path | None = None,
) -> dict:
    """Pure data function for `thoth config profiles show NAME`.

    Returns the profile's raw contents from the resolved layer. Honors
    inherited ``--config PATH`` and ``--profile`` (read-only leaf).
    """
    cm = _load_manager(config_path)
    # Apply the same precedence rule as `resolve_profile_layer`: project beats
    # user. ``cm.profile_catalog`` lists user entries first, then project.
    matches = [entry for entry in cm.profile_catalog if entry.name == name]
    project_matches = [entry for entry in matches if entry.tier == "project"]
    layer = (project_matches or matches)[-1] if matches else None
    if layer is None:
        available = sorted({entry.name for entry in cm.profile_catalog})
        return {
            "name": name,
            "profile": None,
            "found": False,
            "available_profiles": available,
            "error": "PROFILE_NOT_FOUND",
        }

    rendered = _to_plain(layer.data)
    if not show_secrets:
        rendered = _mask_in_tree(rendered)
    return {
        "name": name,
        "found": True,
        "tier": layer.tier,
        "path": str(layer.path),
        "profile": rendered,
    }


def get_config_profile_current_data(
    *,
    config_path: str | Path | None = None,
    profile: str | None = None,
) -> dict:
    """Pure data function for `thoth config profiles current`.

    Reports the runtime active selection plus its source. Honors
    inherited ``--config PATH`` and ``--profile``.
    """
    cm = _load_manager(config_path, profile=profile)
    return {
        "active_profile": cm.profile_selection.name,
        "selection_source": cm.profile_selection.source,
        "selection_detail": cm.profile_selection.source_detail,
    }


def get_config_profile_set_default_data(
    name: str,
    *,
    project: bool,
    config_path: str | Path | None = None,
) -> dict:
    """Pure data function for `thoth config profiles set-default NAME`.

    Validates ``name`` against the resolved profile catalog (B16) before
    writing ``general.default_profile = NAME`` to the target file.
    """
    from thoth.errors import ConfigProfileError

    if project and config_path is not None:
        return {
            "default_profile": None,
            "wrote": False,
            "path": None,
            "error": "PROJECT_CONFIG_CONFLICT",
        }

    # Build a transient ConfigManager pointed at the same target view the
    # command will write. We pass `config_path` to the constructor (NOT
    # through `load_all_layers`, which intentionally rejects metadata keys).
    context = _write_context(project, config_path)
    catalog_names = {entry.name for entry in context.raw_profile_catalog()}
    if name not in catalog_names:
        raise ConfigProfileError(
            f"Profile {name!r} not found",
            available_profiles=sorted(catalog_names),
            source="thoth config profiles set-default",
        )

    doc = context.load_document()
    doc.set_default_profile(name)
    doc.save()
    return {
        "default_profile": name,
        "wrote": True,
        "path": str(context.target_path),
    }


def get_config_profile_unset_default_data(
    *,
    project: bool,
    config_path: str | Path | None = None,
) -> dict:
    """Pure data function for `thoth config profiles unset-default`.

    Removes ``general.default_profile`` from the target file. Leaves the
    surrounding ``[general]`` table intact even if it becomes empty (B17).
    """
    if project and config_path is not None:
        return {
            "removed": False,
            "path": None,
            "error": "PROJECT_CONFIG_CONFLICT",
        }

    context = _write_context(project, config_path)
    path = context.target_path
    if not path.exists():
        return {"removed": False, "path": str(path), "reason": "NO_FILE"}

    doc = context.load_document()
    removed = doc.unset_default_profile()
    if not removed:
        return {"removed": False, "path": str(path), "reason": "NOT_FOUND"}

    doc.save()
    return {"removed": True, "path": str(path)}


def get_modes_set_default_data(
    name: str,
    *,
    project: bool,
    profile: str | None = None,
    config_path: str | Path | None = None,
) -> dict:
    """Pure data function for `thoth modes set-default NAME`.

    Validation:
      1. --project + --config PATH → PROJECT_CONFIG_CONFLICT (exit 2).
      2. --profile X → X must exist in the target tier (same-tier rule).
         Else ConfigProfileError (exit 1).
      3. NAME must be resolvable when the default fires:
         general scope → builtins ∪ base [modes.*];
         profile scope → builtins ∪ base [modes.*] ∪ [profiles.X.modes.*].
    """
    from thoth.config import BUILTIN_MODES
    from thoth.errors import ConfigProfileError, ThothError

    if project and config_path is not None:
        envelope: dict[str, Any] = {
            "default_mode": None,
            "wrote": False,
            "path": None,
            "error": "PROJECT_CONFIG_CONFLICT",
        }
        if profile is not None:
            envelope["profile"] = profile
        return envelope

    context = _write_context(project, config_path)

    # Same-tier profile-existence rule (P35).
    if profile is not None and not context.target_has_profile(profile):
        # Build the available list scoped to the target tier so the error
        # message is actionable.
        if context.target_path.exists():
            target_doc = context.load_document()
            target_profiles = sorted(_names_under_table(target_doc, ("profiles",)))
        else:
            target_profiles = []
        tier_label = (
            "project config"
            if project
            else f"config file {context.target_path}"
            if config_path
            else "user config"
        )
        raise ConfigProfileError(
            f"Profile {profile!r} not found in {tier_label}",
            available_profiles=target_profiles,
            source="thoth modes set-default",
        )

    # Mode NAME resolvability check (cross-tier — β rule).
    cm = _load_manager(config_path, profile=profile)
    resolvable = set(BUILTIN_MODES.keys())
    base_modes = cm.get("modes")
    if isinstance(base_modes, dict):
        resolvable.update(base_modes.keys())

    if name not in resolvable:
        raise ThothError(
            f"Mode {name!r} not found",
            suggestion=f"Available modes: {', '.join(sorted(resolvable))}",
        )

    doc = context.load_document()
    doc.set_default_mode(name, profile=profile)
    doc.save()

    out: dict[str, Any] = {
        "default_mode": name,
        "wrote": True,
        "path": str(context.target_path),
    }
    if profile is not None:
        out["profile"] = profile
    return out


def _names_under_table(doc: Any, segments: tuple[str, ...]) -> list[str]:
    """Helper: list the keys of a nested table, or [] if absent."""
    table = doc._table_at(segments)
    if table is None:
        return []
    return [str(k) for k in table.keys()]


def get_config_profile_list_data(
    *,
    config_path: str | Path | None = None,
    profile: str | None = None,
    show_shadowed: bool = False,
) -> dict:
    """Pure data function for `thoth config profiles list`.

    Default output collapses duplicate names to the winning layer that
    `resolve_profile_layer(...)` would choose (project beats user).
    With ``show_shadowed=True``, lower-precedence same-name rows are
    included with ``shadowed=True`` and ``shadowed_by`` metadata.
    """
    cm = _load_manager(config_path, profile=profile)
    selected = cm.profile_selection.name

    # Group catalog entries by name preserving precedence: project beats user.
    by_name: dict[str, dict[str, Any]] = {}
    for entry in cm.profile_catalog:
        slot = by_name.setdefault(entry.name, {"project": [], "user": []})
        slot[entry.tier].append(entry)

    rows: list[dict[str, Any]] = []
    for name in sorted(by_name):
        slot = by_name[name]
        winner = (slot["project"][-1:] or slot["user"][-1:])[0]
        winner_active = name == selected
        winner_row = {
            "name": winner.name,
            "tier": winner.tier,
            "path": str(winner.path),
            "active": winner_active,
            "shadowed": False,
            "shadowed_by": None,
        }
        rows.append(winner_row)
        if not show_shadowed:
            continue
        # Emit shadowed rows immediately after the winner.
        shadowed_entries: list[Any] = []
        if slot["project"] and slot["user"]:
            # User entries are shadowed by the project winner.
            shadowed_entries.extend(slot["user"])
        # Older same-tier duplicates within a single file are also shadowed.
        same_tier = slot[winner.tier]
        if len(same_tier) > 1:
            shadowed_entries.extend(same_tier[:-1])
        for shadow in shadowed_entries:
            rows.append(
                {
                    "name": shadow.name,
                    "tier": shadow.tier,
                    "path": str(shadow.path),
                    "active": False,
                    "shadowed": True,
                    "shadowed_by": {
                        "tier": winner.tier,
                        "path": str(winner.path),
                    },
                }
            )

    return {
        "active_profile": cm.profile_selection.name,
        "selection_source": cm.profile_selection.source,
        "selection_detail": cm.profile_selection.source_detail,
        "profiles": rows,
    }


__all__ = [
    "config_command",
    "get_config_edit_data",
    "get_config_get_data",
    "get_config_list_data",
    "get_config_path_data",
    "get_config_profile_add_data",
    "get_config_profile_current_data",
    "get_config_profile_list_data",
    "get_config_profile_remove_data",
    "get_config_profile_set_data",
    "get_config_profile_set_default_data",
    "get_config_profile_show_data",
    "get_config_profile_unset_data",
    "get_config_profile_unset_default_data",
    "get_config_set_data",
    "get_config_unset_data",
    "get_modes_set_default_data",
]
