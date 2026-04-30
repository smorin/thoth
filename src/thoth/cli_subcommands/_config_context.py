"""Shared config loading helpers for Click subcommand wrappers."""

from __future__ import annotations

from pathlib import Path

import click

from thoth.cli_subcommands._option_policy import inherited_value
from thoth.config import ConfigManager


def load_config(config_path: str | None = None, profile: str | None = None) -> ConfigManager:
    """Load a ConfigManager from explicit CLI context values."""
    manager = ConfigManager(Path(config_path).expanduser().resolve() if config_path else None)
    cli_args: dict[str, object] = {}
    if profile:
        cli_args["_profile"] = profile
    manager.load_all_layers(cli_args)
    return manager


def load_config_from_ctx(ctx: click.Context) -> ConfigManager:
    """Load config honoring root-level --config and --profile."""
    return load_config(
        config_path=inherited_value(ctx, "config_path"),
        profile=inherited_value(ctx, "profile"),
    )


__all__ = ["load_config", "load_config_from_ctx"]
