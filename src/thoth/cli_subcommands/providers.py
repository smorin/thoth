"""`thoth providers` Click subgroup with leaves: list, models, check.

PR1 preserves the existing `providers -- --list` legacy shim path by
NOT routing the bare `thoth providers` invocation through this subgroup —
that bare-no-leaf path falls through to the imperative dispatch in cli.py
which still handles the legacy form. PR2 removes that shim entirely.
"""

from __future__ import annotations

import sys

import click

from thoth.config import ConfigManager


@click.group(name="providers")
def providers() -> None:
    """Manage provider models and API keys."""


@providers.command(name="list")
@click.pass_context
def providers_list_cmd(ctx: click.Context) -> None:
    """List available providers."""
    from thoth import commands as _commands
    cfg = ConfigManager()
    cfg.load_all_layers({})
    sys.exit(_commands.providers_list(cfg))


@providers.command(name="models")
@click.pass_context
def providers_models_cmd(ctx: click.Context) -> None:
    """List provider models."""
    from thoth import commands as _commands
    cfg = ConfigManager()
    cfg.load_all_layers({})
    sys.exit(_commands.providers_models(cfg))


@providers.command(name="check")
@click.pass_context
def providers_check_cmd(ctx: click.Context) -> None:
    """Check provider API key configuration."""
    from thoth import commands as _commands
    cfg = ConfigManager()
    cfg.load_all_layers({})
    sys.exit(_commands.providers_check(cfg))
