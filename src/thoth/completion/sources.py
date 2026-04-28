"""Pure data functions for Click `shell_complete=` callbacks.

Each function takes Click's `(ctx, param, incomplete)` signature and
returns a `list[str]` of candidate completions filtered by `incomplete`
prefix. The functions are pure (no side effects) so they can also be
imported by `interactive.py::SlashCommandCompleter` in a future PR.

Per spec §6.4: `mode_kind` is committed as dead code (~5 LOC) for P18
forward-compat — P18 will wire `--kind` later.
"""

from __future__ import annotations

from typing import Any

from thoth.config import BUILTIN_MODES, ConfigManager, ConfigSchema
from thoth.paths import user_checkpoints_dir


def _starts_with(items: list[str], incomplete: str) -> list[str]:
    if not incomplete:
        return sorted(items)
    return sorted(item for item in items if item.startswith(incomplete))


def operation_ids(ctx: Any, param: Any, incomplete: str) -> list[str]:
    """Live operation IDs from the user's checkpoint store."""
    checkpoint_dir = user_checkpoints_dir()
    if not checkpoint_dir.exists():
        return []
    ids = [p.stem for p in checkpoint_dir.glob("*.json")]
    return _starts_with(ids, incomplete)


def mode_names(ctx: Any, param: Any, incomplete: str) -> list[str]:
    """Built-in + user-defined mode names.

    User modes are loaded lazily from a fresh ConfigManager; this is a
    completion path so the small extra IO is acceptable.
    """
    names = list(BUILTIN_MODES.keys())
    try:
        cm = ConfigManager()
        cm.load_all_layers({})
        user_modes = (cm.data.get("modes") or {}).keys()
        names.extend(str(name) for name in user_modes)
    except Exception:
        # Completion must never raise — degrade to builtins.
        pass
    return _starts_with(sorted(set(names)), incomplete)


def _flatten_keys(data: dict[str, Any], prefix: str = "") -> list[str]:
    out: list[str] = []
    for key, value in data.items():
        full = key if not prefix else f"{prefix}.{key}"
        if isinstance(value, dict):
            out.extend(_flatten_keys(value, full))
        else:
            out.append(full)
    return out


def config_keys(ctx: Any, param: Any, incomplete: str) -> list[str]:
    """Dotted config keys derived from ConfigSchema defaults."""
    try:
        defaults = ConfigSchema.get_defaults()
    except Exception:
        return []
    keys = _flatten_keys(defaults)
    return _starts_with(keys, incomplete)


def provider_names(ctx: Any, param: Any, incomplete: str) -> list[str]:
    """Static provider names — matches PROVIDER_CHOICES in providers.py."""
    return _starts_with(["openai", "perplexity", "mock"], incomplete)


def mode_kind(ctx: Any, param: Any, incomplete: str) -> list[str]:
    """P18 forward-compat — currently dead code per spec §6.4."""
    return _starts_with(["immediate", "background"], incomplete)


__all__ = [
    "config_keys",
    "mode_kind",
    "mode_names",
    "operation_ids",
    "provider_names",
]
