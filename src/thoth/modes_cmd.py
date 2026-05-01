"""CLI surface for the `thoth modes` subcommand.

Single source of truth for mode enumeration: `list_all_modes(cm)` returns a
list of `ModeInfo` objects covering built-in modes (from `BUILTIN_MODES`),
user-defined modes (from `[modes.*]` in user/project TOML), and modes that
override a builtin (present in both).
"""

from __future__ import annotations

import inspect
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, cast

from rich.console import Console
from rich.table import Table

from thoth._secrets import _mask_tree
from thoth.config import BUILTIN_MODES, ConfigManager, mode_kind

SCHEMA_VERSION = "1"


@dataclass
class _TargetFlags:
    """Resolved targeting flags shared by every modes mutator.

    `project` and `config_path` form the file axis (mutually exclusive).
    `profile` selects the destination tier (`[profiles.<X>.modes.<NAME>]`
    when set, `[modes.<NAME>]` otherwise). `from_profile` is the SRC-tier
    selector for `copy` only — every other op rejects it as USAGE_ERROR.
    `override` is the builtin-shadow opt-in for add/copy; every other op
    rejects it as USAGE_ERROR.
    """

    project: bool = False
    config_path: str | None = None
    profile: str | None = None
    from_profile: str | None = None
    force_string: bool = False
    override: bool = False


def _parse_target_flags(
    args: list[str],
) -> tuple[_TargetFlags, list[str], int]:
    """Pull targeting flags out of `args`. Returns (flags, remaining, rc).

    rc == 0 → ok; rc == 2 → USAGE_ERROR (caller emits the message).
    Validates `--project` ⊥ `--config PATH`.
    Does NOT validate that an op accepts `--from-profile` or `--override` —
    that's per-op.
    """
    flags = _TargetFlags()
    remaining: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--project":
            flags.project = True
            i += 1
        elif a == "--config":
            if i + 1 >= len(args):
                return flags, remaining, 2
            flags.config_path = args[i + 1]
            i += 2
        elif a == "--profile":
            if i + 1 >= len(args):
                return flags, remaining, 2
            flags.profile = args[i + 1]
            i += 2
        elif a == "--from-profile":
            if i + 1 >= len(args):
                return flags, remaining, 2
            flags.from_profile = args[i + 1]
            i += 2
        elif a == "--string":
            flags.force_string = True
            i += 1
        elif a == "--override":
            flags.override = True
            i += 1
        else:
            remaining.append(a)
            i += 1

    if flags.project and flags.config_path is not None:
        return flags, remaining, 2

    return flags, remaining, 0


@dataclass(frozen=True)
class _ModesOpSpec:
    """Static CLI-surface description of one `thoth modes <op>` mutator.

    Drives both `get_modes_data_from_args` (JSON path) and the click-leaf
    factory `_make_modes_leaf` (human path). Per-command tasks register
    their spec via `_OP_SPECS[op_name] = _ModesOpSpec(...)`.
    """

    name: str
    positionals: tuple[str, ...]
    # Op-specific keyword flags: maps `--flag-name` to attribute name on the
    # parsed-kwargs dict. Example for `add`: {"--model": "model",
    # "--provider": "provider", "--description": "description", "--kind":
    # "kind"}.
    op_flags: dict[str, str]
    required_op_flags: frozenset[str]
    accepts_from_profile: bool = False  # only `copy`
    accepts_override: bool = False  # only `add` and `copy`
    accepts_string: bool = False  # only `set`


_OP_SPECS: dict[str, _ModesOpSpec] = {}
_OP_DATA_FNS: dict[str, Callable[..., dict]] = {}


def _resolve_write_target(
    flags: _TargetFlags, *, config_path: str | None
) -> tuple[Any | None, dict | None]:
    """Resolve the file write target. Returns (context, error_envelope).

    Caller-supplied `config_path` (from inherited root flag) overrides
    `flags.config_path` only when the latter is None — this matches
    `cli_subcommands/_config_context` semantics.
    """
    from thoth.config_write_context import (
        ConfigTargetConflictError,
        ConfigWriteContext,
    )

    target_path = flags.config_path or config_path
    try:
        context = ConfigWriteContext.resolve(project=flags.project, config_path=target_path)
    except ConfigTargetConflictError as e:
        return None, {
            "error": "PROJECT_CONFIG_CONFLICT",
            "message": str(e),
        }
    return context, None


def _check_builtin_guard(name: str, *, override: bool, op_name: str) -> dict | None:
    """Return an error envelope if NAME is reserved for the op, else None.

    `add`: refuse builtin unless `override`. `copy(dst)`: refuse builtin
    DST unless `override`. `remove` / `rename`: refuse builtin period
    (override does not bypass — those ops are not "shadow-create" ops).
    `set` / `unset`: never refuses on name; this helper isn't called.
    """
    from thoth.config import BUILTIN_MODES

    if name not in BUILTIN_MODES:
        return None

    if op_name in ("add", "copy") and override:
        return None

    return {
        "error": "BUILTIN_NAME_RESERVED",
        "message": f"'{name}' is a builtin mode and cannot be {op_name}'d directly.",
    }


def _check_override_strict(name: str, *, override: bool, op_name: str) -> dict | None:
    """Return an error envelope if `--override` is passed on a non-builtin.

    Per BQ resolution: `--override` exists only to bypass the builtin
    guard. Passing it where there's no guard to bypass is a USAGE_ERROR.
    Applies symmetrically to `add NAME --override` (where NAME isn't
    builtin) and `copy SRC DST --override` (where DST isn't builtin).
    """
    from thoth.config import BUILTIN_MODES

    if not override:
        return None
    if name in BUILTIN_MODES:
        return None
    return {
        "error": "USAGE_ERROR",
        "message": (
            f"--override is only valid when {op_name.upper()}'s target name "
            f"shadows a builtin mode ({name!r} is not a builtin; "
            f"remove --override or use a different name)."
        ),
    }


def _dst_taken_envelope(dst: str, *, profile: str | None, op_name: str) -> dict:
    """Return the standard DST_NAME_TAKEN error envelope.

    Used by `rename` and `copy` after the caller has confirmed via
    `_table_at` that DST already exists in the destination tier. This
    helper only formats the error — the existence check is the caller's
    responsibility (per-command tasks 8 and 9).
    """
    return {
        "error": "DST_NAME_TAKEN",
        "message": (
            f"destination {dst!r} already exists "
            f"in {'profile ' + profile if profile else 'base'} tier"
        ),
    }


def _target_descriptor(path: Path, profile: str | None) -> dict[str, str]:
    """Standard `target: {file, tier}` envelope sub-object."""
    return {
        "file": str(path),
        "tier": f"profiles.{profile}.modes" if profile else "modes",
    }


def parse_modes_args(
    op_name: str, args: list[str]
) -> tuple[dict[str, Any], _TargetFlags, dict | None]:
    """Parse `args` against `_OP_SPECS[op_name]`.

    Returns (op_kwargs, target_flags, error_envelope_or_none).
    `op_kwargs` is a dict of op-specific values (positionals + op flags),
    keyed by the spec's positional names and op_flags values.

    Validates: targeting flags via `_parse_target_flags`; positional
    arity matches spec; only spec-allowed op-specific flags appear;
    required op-flags are present; --from-profile / --override / --string
    only appear on ops that accept them.
    """
    spec = _OP_SPECS.get(op_name)
    if spec is None:
        return (
            {},
            _TargetFlags(),
            {"error": "USAGE_ERROR", "message": f"unknown op: {op_name}"},
        )

    target_flags, remaining, rc = _parse_target_flags(args)
    if rc != 0:
        return (
            {},
            target_flags,
            {"error": "USAGE_ERROR", "message": "invalid flag combination"},
        )

    # Per-spec gating of targeting flags that aren't universally accepted.
    if target_flags.from_profile is not None and not spec.accepts_from_profile:
        return (
            {},
            target_flags,
            {
                "error": "USAGE_ERROR",
                "message": f"--from-profile is not valid for `{op_name}`",
            },
        )
    if target_flags.override and not spec.accepts_override:
        return (
            {},
            target_flags,
            {
                "error": "USAGE_ERROR",
                "message": f"--override is not valid for `{op_name}`",
            },
        )
    if target_flags.force_string and not spec.accepts_string:
        return (
            {},
            target_flags,
            {
                "error": "USAGE_ERROR",
                "message": f"--string is not valid for `{op_name}`",
            },
        )

    # Parse op-specific flags + positionals from `remaining`.
    op_kwargs: dict[str, Any] = {}
    positionals: list[str] = []
    i = 0
    while i < len(remaining):
        a = remaining[i]
        if a in spec.op_flags:
            if i + 1 >= len(remaining):
                return (
                    {},
                    target_flags,
                    {"error": "USAGE_ERROR", "message": f"{a} requires a value"},
                )
            op_kwargs[spec.op_flags[a]] = remaining[i + 1]
            i += 2
        elif a.startswith("--"):
            return (
                {},
                target_flags,
                {
                    "error": "USAGE_ERROR",
                    "message": f"unknown flag for `{op_name}`: {a}",
                },
            )
        else:
            positionals.append(a)
            i += 1

    if len(positionals) != len(spec.positionals):
        return (
            {},
            target_flags,
            {
                "error": "USAGE_ERROR",
                "message": f"`modes {op_name}` takes {' '.join(spec.positionals)}",
            },
        )
    for pname, pvalue in zip(spec.positionals, positionals, strict=True):
        op_kwargs[pname.lower()] = pvalue

    missing = spec.required_op_flags - set(op_kwargs.keys())
    if missing:
        return (
            {},
            target_flags,
            {
                "error": "USAGE_ERROR",
                "message": f"`modes {op_name}` requires {', '.join(sorted(missing))}",
            },
        )

    return op_kwargs, target_flags, None


# ---------------------------------------------------------------------------
# `thoth modes add` — P12 Task 4
# ---------------------------------------------------------------------------


def get_modes_add_data(
    name: str,
    *,
    model: str,
    provider: str = "openai",
    description: str | None = None,
    kind: str = "immediate",
    project: bool = False,
    config_path: str | None = None,
    profile: str | None = None,
    override: bool = False,
) -> dict:
    """Pure data function for `thoth modes add`. Returns a receipt dict.

    Idempotency: same NAME + same model = no-op exit 0; different model =
    `MODE_EXISTS_DIFFERENT_MODEL` exit 1. Other flags ignored on re-add.

    Builtin-name guard: refuses unless `--override` is set. `--override`
    writes a builtin-name override in the selected tier (base by default,
    profile overlay when `profile` is set). Strict-on-non-builtin rule
    (BQ resolution): `--override` without a builtin guard to bypass is
    USAGE_ERROR.
    """
    # Validate kind
    if kind not in ("immediate", "background"):
        return {
            "schema_version": SCHEMA_VERSION,
            "op": "add",
            "mode": name,
            "error": "USAGE_ERROR",
            "message": f"--kind must be one of immediate, background (got {kind!r})",
        }

    # Strict-on-non-builtin: --override on a non-builtin name is USAGE_ERROR
    err = _check_override_strict(name, override=override, op_name="add")
    if err is not None:
        return {
            "schema_version": SCHEMA_VERSION,
            "op": "add",
            "mode": name,
            **err,
        }

    # Builtin-name guard
    err = _check_builtin_guard(name, override=override, op_name="add")
    if err is not None:
        return {
            "schema_version": SCHEMA_VERSION,
            "op": "add",
            "mode": name,
            **err,
        }

    # Resolve write target (handles --project + --config PATH conflict)
    flags = _TargetFlags(project=project, config_path=config_path)
    context, err = _resolve_write_target(flags, config_path=None)
    if err is not None:
        return {
            "schema_version": SCHEMA_VERSION,
            "op": "add",
            "mode": name,
            **err,
        }

    assert context is not None  # guaranteed by err is None
    doc = context.load_document()
    existing = doc.get_mode(name, profile=profile)

    if existing is not None:
        existing_model = existing.get("model")
        if existing_model is None:
            return {
                "schema_version": SCHEMA_VERSION,
                "op": "add",
                "mode": name,
                "error": "MODE_EXISTS_NO_MODEL",
                "message": (
                    f"mode {name!r} already exists in TOML but has no `model` field "
                    f"(possibly mid-edit). Use `thoth modes set {name} model {model}` "
                    f"to repair, or `thoth modes remove {name}` to delete and re-add."
                ),
            }
        if existing_model == model:
            return {
                "schema_version": SCHEMA_VERSION,
                "op": "add",
                "mode": name,
                "created": False,
                "model": model,
                "provider": existing.get("provider"),
                "kind": existing.get("kind"),
                "target": _target_descriptor(context.target_path, profile),
            }
        return {
            "schema_version": SCHEMA_VERSION,
            "op": "add",
            "mode": name,
            "error": "MODE_EXISTS_DIFFERENT_MODEL",
            "message": (
                f"mode {name!r} already exists with model "
                f"{existing_model!r} (you passed {model!r}). "
                f"Use `thoth modes set {name} model {model}` to update."
            ),
        }

    # Create
    doc.ensure_mode(name, profile=profile)
    doc.set_mode_value(name, "model", model, profile=profile)
    doc.set_mode_value(name, "provider", provider, profile=profile)
    doc.set_mode_value(name, "kind", kind, profile=profile)
    if description is not None:
        doc.set_mode_value(name, "description", description, profile=profile)
    doc.save()

    return {
        "schema_version": SCHEMA_VERSION,
        "op": "add",
        "mode": name,
        "created": True,
        "model": model,
        "provider": provider,
        "kind": kind,
        "target": _target_descriptor(context.target_path, profile),
    }


_OP_SPECS["add"] = _ModesOpSpec(
    name="add",
    positionals=("NAME",),
    op_flags={
        "--model": "model",
        "--provider": "provider",
        "--description": "description",
        "--kind": "kind",
    },
    required_op_flags=frozenset({"model"}),
    accepts_override=True,
)
_OP_DATA_FNS["add"] = get_modes_add_data


# ---------------------------------------------------------------------------
# `thoth modes set` — P12 Task 5
# ---------------------------------------------------------------------------


def get_modes_set_data(
    name: str,
    key: str,
    value: str,
    *,
    project: bool = False,
    force_string: bool = False,
    config_path: str | None = None,
    profile: str | None = None,
) -> dict:
    """Pure data function for `thoth modes set`. Returns a receipt dict.

    Setting on a builtin name implicitly creates an overriding mode
    table in the chosen tier (`[modes.<NAME>]` or `[profiles.<X>.modes.<NAME>]`).
    Absent non-builtin names are rejected with MODE_NOT_FOUND.

    Type coercion via `_parse_value` (bool/int/float/string). `--string`
    flag forces string parsing. Secret-like keys are masked in the JSON
    receipt (`value` field) but written verbatim to the TOML file.

    The `value` parameter is the raw string from the CLI; coercion happens
    inside this function via `_parse_value`. (The kwarg name matches the
    `VALUE` positional in `_OP_SPECS["set"]` so the dispatcher can spread
    parsed positionals directly.)
    """
    from thoth._secrets import _is_secret_key, _mask_secret
    from thoth.config import BUILTIN_MODES
    from thoth.config_cmd import _parse_value

    flags = _TargetFlags(project=project, config_path=config_path)
    context, err = _resolve_write_target(flags, config_path=None)
    if err is not None:
        return {
            "schema_version": SCHEMA_VERSION,
            "op": "set",
            "mode": name,
            **err,
        }
    assert context is not None  # err is None ⇒ context is not None

    doc = context.load_document()

    # Builtin names always allowed (implicit override creation).
    # Non-builtin names must already exist in the chosen tier.
    if name not in BUILTIN_MODES and doc.get_mode(name, profile=profile) is None:
        return {
            "schema_version": SCHEMA_VERSION,
            "op": "set",
            "mode": name,
            "error": "MODE_NOT_FOUND",
            "message": f"mode {name!r} not found",
        }

    parsed_value = _parse_value(value, force_string)
    doc.set_mode_value(name, key, parsed_value, profile=profile)
    doc.save()
    receipt_value = _mask_secret(parsed_value) if _is_secret_key(key) else parsed_value

    return {
        "schema_version": SCHEMA_VERSION,
        "op": "set",
        "mode": name,
        "key": key,
        "value": receipt_value,
        "wrote": True,
        "target": _target_descriptor(context.target_path, profile),
    }


_OP_SPECS["set"] = _ModesOpSpec(
    name="set",
    positionals=("NAME", "KEY", "VALUE"),
    op_flags={},
    required_op_flags=frozenset(),
    accepts_string=True,
)
_OP_DATA_FNS["set"] = get_modes_set_data


# ---------------------------------------------------------------------------
# `thoth modes unset` — P12 Task 6
# ---------------------------------------------------------------------------


def get_modes_unset_data(
    name: str,
    key: str,
    *,
    project: bool = False,
    config_path: str | None = None,
    profile: str | None = None,
) -> dict:
    """Pure data function for `thoth modes unset`. Returns receipt dict.

    Removes a single key from the mode's table in the chosen tier. Empty
    parent table is pruned automatically (Task 2's `unset_mode_value`
    handles this — divergence from `unset_profile_value` per B17).

    Pure-builtin NAME (no user-side override in chosen tier) →
    MODE_NOT_FOUND. Absent KEY on a present mode → no-op exit 0
    (`removed: False`).
    """
    flags = _TargetFlags(project=project, config_path=config_path)
    context, err = _resolve_write_target(flags, config_path=None)
    if err is not None:
        return {
            "schema_version": SCHEMA_VERSION,
            "op": "unset",
            "mode": name,
            **err,
        }
    assert context is not None

    doc = context.load_document()

    # Pure-builtin NAME (no user-side override in chosen tier) → MODE_NOT_FOUND.
    # Builtin names that have an override in the chosen tier are valid targets.
    if doc.get_mode(name, profile=profile) is None:
        return {
            "schema_version": SCHEMA_VERSION,
            "op": "unset",
            "mode": name,
            "error": "MODE_NOT_FOUND",
            "message": (
                f"mode {name!r} has no user-side table to unset from"
                + (f" (in profile {profile!r})" if profile else "")
            ),
        }

    removed, table_pruned = doc.unset_mode_value(name, key, profile=profile)
    if removed or table_pruned:
        doc.save()

    return {
        "schema_version": SCHEMA_VERSION,
        "op": "unset",
        "mode": name,
        "key": key,
        "removed": removed,
        "table_pruned": table_pruned,
        "target": _target_descriptor(context.target_path, profile),
    }


_OP_SPECS["unset"] = _ModesOpSpec(
    name="unset",
    positionals=("NAME", "KEY"),
    op_flags={},
    required_op_flags=frozenset(),
)
_OP_DATA_FNS["unset"] = get_modes_unset_data


# ---------------------------------------------------------------------------
# `thoth modes remove` — P12 Task 7
# ---------------------------------------------------------------------------


def get_modes_remove_data(
    name: str,
    *,
    project: bool = False,
    config_path: str | None = None,
    profile: str | None = None,
) -> dict:
    """Pure data function for `thoth modes remove`. Returns receipt dict.

    Builtin guard is absolute — `--override` does NOT bypass remove.
    Pure-builtin (no user-side override) → BUILTIN_NAME_RESERVED.
    Overridden builtin → drops the override and reports
    `reverted_to_builtin=True`. User-only mode → drops the table.
    Absent (non-builtin) → idempotent no-op exit 0.
    """
    from thoth.config import BUILTIN_MODES

    flags = _TargetFlags(project=project, config_path=config_path)
    context, err = _resolve_write_target(flags, config_path=None)
    if err is not None:
        return {
            "schema_version": SCHEMA_VERSION,
            "op": "remove",
            "mode": name,
            **err,
        }
    assert context is not None

    doc = context.load_document()
    has_user_table = doc.get_mode(name, profile=profile) is not None

    # Pure-builtin guard: builtin name with no user-side override → reserved.
    if name in BUILTIN_MODES and not has_user_table:
        return {
            "schema_version": SCHEMA_VERSION,
            "op": "remove",
            "mode": name,
            "error": "BUILTIN_NAME_RESERVED",
            "message": (f"'{name}' is a builtin mode and has no user-side override to remove."),
        }

    was_builtin_override = name in BUILTIN_MODES and has_user_table
    removed = doc.remove_mode(name, profile=profile)
    if removed:
        doc.save()

    return {
        "schema_version": SCHEMA_VERSION,
        "op": "remove",
        "mode": name,
        "removed": removed,
        "reverted_to_builtin": removed and was_builtin_override,
        "target": _target_descriptor(context.target_path, profile),
    }


_OP_SPECS["remove"] = _ModesOpSpec(
    name="remove",
    positionals=("NAME",),
    op_flags={},
    required_op_flags=frozenset(),
)
_OP_DATA_FNS["remove"] = get_modes_remove_data


# ---------------------------------------------------------------------------
# `thoth modes rename` — P12 Task 8
# ---------------------------------------------------------------------------


def get_modes_rename_data(
    old: str,
    new: str,
    *,
    project: bool = False,
    config_path: str | None = None,
    profile: str | None = None,
) -> dict:
    """Rename OLD → NEW within the chosen tier. No --override; rename
    on builtins is always refused. NEW must be a free non-builtin."""
    from thoth.config import BUILTIN_MODES

    base = {
        "schema_version": SCHEMA_VERSION,
        "op": "rename",
        "mode": new,
        "from": old,
        "to": new,
    }

    if old in BUILTIN_MODES:
        return {
            **base,
            "error": "BUILTIN_NAME_RESERVED",
            "message": (
                f"'{old}' is a builtin mode and cannot be renamed. "
                f"Drop any user-side override first (`thoth modes remove {old}`) "
                f"and create a new mode at {new!r} via `thoth modes add`."
            ),
        }
    if new in BUILTIN_MODES:
        return {
            **base,
            "error": "DST_NAME_TAKEN",
            "message": (
                f"destination {new!r} is a builtin mode name; "
                f"rename does not accept --override. Use a different name."
            ),
        }

    flags = _TargetFlags(project=project, config_path=config_path)
    context, err = _resolve_write_target(flags, config_path=None)
    if err is not None:
        return {**base, **err}
    assert context is not None

    doc = context.load_document()

    if doc.get_mode(old, profile=profile) is None:
        return {
            **base,
            "error": "MODE_NOT_FOUND",
            "message": (
                f"mode {old!r} not found" + (f" in profile {profile!r}" if profile else "")
            ),
        }

    if doc.get_mode(new, profile=profile) is not None:
        return {
            **base,
            **_dst_taken_envelope(new, profile=profile, op_name="rename"),
        }

    renamed = doc.rename_mode(old, new, profile=profile)
    assert renamed, "rename_mode should return True after pre-checks (OLD exists, NEW free)"
    doc.save()

    return {
        **base,
        "renamed": renamed,
        "target": _target_descriptor(context.target_path, profile),
    }


_OP_SPECS["rename"] = _ModesOpSpec(
    name="rename",
    positionals=("OLD", "NEW"),
    op_flags={},
    required_op_flags=frozenset(),
)
_OP_DATA_FNS["rename"] = get_modes_rename_data


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
    """Resolve a mode's display kind for the `thoth modes` table.

    P18: prefer the declared `kind` field; fall back to `mode_kind` (which
    handles the legacy `async` key + substring sniff). Missing model AND no
    declared kind AND no async → kind=unknown with a warning.
    """
    if "kind" in cfg:
        kind_raw = cfg["kind"]
        if kind_raw == "immediate":
            return "immediate"
        if kind_raw == "background":
            return "background"
        warnings.append(f"invalid `kind` value {kind_raw!r} — must be 'immediate' or 'background'")
        return "unknown"
    if not cfg.get("model") and "async" not in cfg:
        warnings.append("missing `model` and no explicit `kind`/`async` — kind unknown")
        return "unknown"
    # Legacy fallback path; mode_kind() emits its own DeprecationWarning if `async` is set.
    resolved = mode_kind(cfg)
    return "background" if resolved == "background" else "immediate"


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


_VALID_KINDS = ("immediate", "background")


def _parse_list_flags(
    args: list[str],
) -> tuple[bool, bool, str, str | None, bool, str | None, int]:
    """Return (as_json, show_secrets, source, name, full, kind, error_rc). rc=0 means ok."""
    as_json = False
    show_secrets = False
    source = "all"
    name: str | None = None
    full = False
    kind: str | None = None
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
                return as_json, show_secrets, source, name, full, kind, 2
            source = args[i + 1]
            if source not in _VALID_SOURCES:
                _get_console().print(
                    f"[red]Error:[/red] --source must be one of {', '.join(_VALID_SOURCES)}"
                )
                return as_json, show_secrets, source, name, full, kind, 2
            i += 2
        elif a == "--name":
            if i + 1 >= len(args):
                _get_console().print("[red]Error:[/red] --name requires a value")
                return as_json, show_secrets, source, name, full, kind, 2
            name = args[i + 1]
            i += 2
        elif a == "--kind":
            if i + 1 >= len(args):
                _get_console().print("[red]Error:[/red] --kind requires a value")
                return as_json, show_secrets, source, name, full, kind, 2
            kind = args[i + 1]
            if kind not in _VALID_KINDS:
                _get_console().print(
                    f"[red]Error:[/red] --kind must be one of {', '.join(_VALID_KINDS)}"
                )
                return as_json, show_secrets, source, name, full, kind, 2
            i += 2
        else:
            _get_console().print(f"[red]Error:[/red] unknown arg: {a}")
            return as_json, show_secrets, source, name, full, kind, 2
    return as_json, show_secrets, source, name, full, kind, 0


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
    profile: str | None = None,
    kind: str | None = None,
) -> dict:
    """Pure data function for `thoth modes list`.

    Returns:
        - {"modes": [...]} when `name` is None
        - {"mode": {...} | None} when `name` is set

    P18 Phase D: optional `kind` filter (`"immediate"` | `"background"`).

    Per spec §7.2, this function NEVER takes an `as_json` flag — the
    JSON-vs-Rich choice lives at the subcommand-wrapper layer.
    """
    cm = ConfigManager(Path(config_path).expanduser().resolve() if config_path else None)
    cli_args: dict[str, object] = {}
    if profile:
        cli_args["_profile"] = profile
    cm.load_all_layers(cli_args)
    infos = list_all_modes(cm)

    if source != "all":
        infos = [m for m in infos if m.source == source]
    if kind is not None:
        infos = [m for m in infos if m.kind == kind]

    if name is not None:
        match = next((m for m in infos if m.name == name), None)
        return {"mode": _info_to_dict(match, show_secrets) if match else None}

    infos = sorted(infos, key=_sort_key)
    return {
        "schema_version": "1",
        "modes": [_info_to_dict(m, show_secrets) for m in infos],
    }


def _op_list(args: list[str], *, config_path: str | None = None) -> int:
    as_json, show_secrets, source, name, full, kind, rc = _parse_list_flags(args)
    if rc != 0:
        return rc

    cm = ConfigManager(Path(config_path).expanduser().resolve() if config_path else None)
    cm.load_all_layers({})
    infos = list_all_modes(cm)

    # Q5-A row 11.i: source filter is applied BEFORE the --name short-circuit
    # so `--name X --source Y` is a true intersection (empty result if X is
    # not in source Y). The same applies to --kind (P18 Phase D).
    if source != "all":
        infos = [m for m in infos if m.source == source]
    if kind is not None:
        infos = [m for m in infos if m.kind == kind]

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


def get_modes_data_from_args(
    op_name: str, args: list[str], *, config_path: str | None = None
) -> tuple[dict, int]:
    """Single JSON-path entry point: parse `args`, call op data fn, return
    `(data_envelope, exit_code)`. Used by Click wrappers.
    """
    op_kwargs, target_flags, err = parse_modes_args(op_name, args)
    if err is not None:
        envelope = {
            "schema_version": SCHEMA_VERSION,
            "op": op_name,
            **err,
        }
        return envelope, 2 if err["error"] == "USAGE_ERROR" else 1

    data_fn = _OP_DATA_FNS.get(op_name)
    if data_fn is None:
        envelope = {
            "schema_version": SCHEMA_VERSION,
            "op": op_name,
            "error": "USAGE_ERROR",
            "message": f"op {op_name!r} has no registered data function",
        }
        return envelope, 2
    # Build the full kwarg dict the dispatcher would inject, then filter
    # by what the data fn actually accepts. Keeps per-command data fns
    # free to omit kwargs they don't use (force_string for non-set ops,
    # from_profile for non-copy ops, override for non-add/copy ops).
    all_kwargs = {
        **op_kwargs,
        "project": target_flags.project,
        "config_path": target_flags.config_path or config_path,
        "profile": target_flags.profile,
        "from_profile": target_flags.from_profile,
        "force_string": target_flags.force_string,
        "override": target_flags.override,
    }
    sig = inspect.signature(data_fn)
    accepted = {k: v for k, v in all_kwargs.items() if k in sig.parameters}
    data = data_fn(**accepted)
    if data.get("error"):
        exit_code = 2 if data["error"] in ("USAGE_ERROR", "PROJECT_CONFIG_CONFLICT") else 1
    else:
        exit_code = 0
    return data, exit_code


def _op(op_name: str, args: list[str], *, config_path: str | None = None) -> int:
    """Single human-path entry point. Calls `get_modes_data_from_args` and
    emits a one-line confirmation via `_emit_human_receipt`. Returns
    process exit code.
    """
    data, exit_code = get_modes_data_from_args(op_name, args, config_path=config_path)
    return _emit_human_receipt(data, exit_code)


def _emit_usage_error(message: str) -> None:
    _get_console().print(f"[red]Error:[/red] {message}")


def _emit_human_receipt(data: dict, exit_code: int) -> int:
    """Emit a one-line confirmation. JSON emission is owned by
    cli_subcommands/modes.py via emit_json/emit_error — this helper is
    human-only.

    Per-op confirmation strings are extended in each per-command task:
    - add → `Added mode '{name}' (model={model}, kind={kind})`
    - set → `Set {name}.{key} = {value!r}`
    - unset → `Unset {name}.{key}` (+ "(table pruned)" if applicable)
    - remove → `Removed mode '{name}'` (+ "(reverted to builtin)" if applicable)
    - rename → `Renamed '{from}' → '{to}'`
    - copy → `Copied '{from}' → '{to}'`
    """
    if data.get("error"):
        _emit_usage_error(data.get("message", data["error"]))
        return exit_code

    op = data.get("op")
    name = data.get("mode")
    target = data.get("target", {})
    suffix = f" → {target['file']} [{target['tier']}.{name}]" if target else ""

    # Per-op switch — extended by per-command tasks (4-9).
    if op == "add":
        if data.get("created"):
            print(f"Added mode '{name}' (model={data['model']}, kind={data['kind']}){suffix}")
        else:
            print(f"Already exists: mode '{name}' (model={data['model']}){suffix}")
    elif op == "set":
        print(f"Set {name}.{data['key']} = {data['value']!r}{suffix}")
    elif op == "unset":
        pruned = " (table pruned)" if data.get("table_pruned") else ""
        if data.get("removed"):
            print(f"Unset {name}.{data['key']}{pruned}{suffix}")
        else:
            print(f"No-op: {name}.{data['key']} not present")
    elif op == "remove":
        reverted = " (reverted to builtin)" if data.get("reverted_to_builtin") else ""
        if data.get("removed"):
            print(f"Removed mode '{name}'{reverted}")
        else:
            print(f"No-op: mode '{name}' not present")
    elif op == "rename":
        print(f"Renamed '{data['from']}' → '{data['to']}'{suffix}")
    elif op == "copy":
        print(f"Copied '{data['from']}' → '{data['to']}'{suffix}")
    else:
        _emit_usage_error(f"internal error: unknown op {op!r} in receipt emitter")
        return 1
    return 0


def modes_command(op: str | None, args: list[str], *, config_path: str | None = None) -> int:
    """Dispatch `thoth modes <op>`. Returns a process exit code."""
    if op is None:
        return _op_list(args, config_path=config_path)
    if op == "list":
        return _op_list(args, config_path=config_path)
    if op in _OP_SPECS:
        return _op(op, args, config_path=config_path)
    _get_console().print(f"[red]Error:[/red] unknown modes op: {op}")
    return 2


__all__ = ["ModeInfo", "get_modes_list_data", "list_all_modes", "modes_command"]
