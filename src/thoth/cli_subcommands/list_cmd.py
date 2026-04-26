"""`thoth list` Click subcommand. File named list_cmd.py to avoid Python
keyword shadow; the registered command name is "list"."""

from __future__ import annotations

import click

from thoth.commands import CommandHandler
from thoth.config import ConfigManager


@click.command(name="list")
@click.option("--all", "show_all", is_flag=True, help="Include completed operations")
@click.pass_context
def list_cmd(ctx: click.Context, show_all: bool) -> None:
    """List research operations."""
    config_path = ctx.obj.get("config_path") if ctx.obj else None
    config_manager = ConfigManager()
    config_manager.load_all_layers({"config_path": config_path})
    handler = CommandHandler(config_manager)
    handler.list_command(show_all=show_all)
