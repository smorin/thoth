"""`thoth status OP_ID` Click subcommand."""

from __future__ import annotations

import click

from thoth.commands import CommandHandler
from thoth.config import ConfigManager


@click.command(name="status")
@click.argument("operation_id", metavar="OP_ID")
@click.pass_context
def status(ctx: click.Context, operation_id: str) -> None:
    """Check status of a research operation by ID."""
    config_path = ctx.obj.get("config_path") if ctx.obj else None
    config_manager = ConfigManager()
    config_manager.load_all_layers({"config_path": config_path})
    handler = CommandHandler(config_manager)
    handler.status_command(operation_id=operation_id)
