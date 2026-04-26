"""`thoth init` Click subcommand.

Thin wrapper around CommandHandler.init_command(). Behavior is unchanged
from the pre-P16 imperative dispatch (cli.py:298-300).
"""

from __future__ import annotations

import click

from thoth.commands import CommandHandler
from thoth.config import ConfigManager


@click.command(name="init")
@click.pass_context
def init(ctx: click.Context) -> None:
    """Initialize thoth configuration."""
    config_path = ctx.obj.get("config_path") if ctx.obj else None

    config_manager = ConfigManager()
    config_manager.load_all_layers({"config_path": config_path})
    handler = CommandHandler(config_manager)
    handler.init_command(config_path=config_path)
