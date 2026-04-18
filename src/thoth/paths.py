"""XDG Base Directory Specification path helpers for Thoth.

Per the spec, when an XDG_* env var is unset or empty, fall back to the
spec default relative to the user's home directory.
"""

from __future__ import annotations

import os
from pathlib import Path

_APP = "thoth"


def _xdg_dir(env_name: str, default_rel: str) -> Path:
    value = os.environ.get(env_name)
    if value:
        return Path(value) / _APP
    return Path.home() / default_rel / _APP


def user_config_dir() -> Path:
    return _xdg_dir("XDG_CONFIG_HOME", ".config")


def user_state_dir() -> Path:
    return _xdg_dir("XDG_STATE_HOME", ".local/state")


def user_cache_dir() -> Path:
    return _xdg_dir("XDG_CACHE_HOME", ".cache")


def user_config_file() -> Path:
    return user_config_dir() / "config.toml"


def user_checkpoints_dir() -> Path:
    return user_state_dir() / "checkpoints"


def user_model_cache_dir() -> Path:
    return user_cache_dir() / "model_cache"


__all__ = [
    "user_cache_dir",
    "user_checkpoints_dir",
    "user_config_dir",
    "user_config_file",
    "user_model_cache_dir",
    "user_state_dir",
]
