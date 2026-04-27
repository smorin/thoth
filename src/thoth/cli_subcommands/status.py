"""`thoth status OP_ID` Click subcommand."""

from __future__ import annotations

import click

from thoth.commands import CommandHandler
from thoth.config import ConfigManager


@click.command(name="status")
@click.argument("operation_id", metavar="OP_ID", required=False)
@click.pass_context
def status(ctx: click.Context, operation_id: str | None) -> None:
    """Check status of a research operation by ID."""
    if operation_id is None:
        click.echo("Error: status command requires an operation ID")
        ctx.exit(1)
    config_path = ctx.obj.get("config_path") if ctx.obj else None
    config_manager = ConfigManager()
    config_manager.load_all_layers({"config_path": config_path})
    handler = CommandHandler(config_manager)
    handler.status_command(operation_id=operation_id)
