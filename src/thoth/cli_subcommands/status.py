"""`thoth status OP_ID` Click subcommand."""

from __future__ import annotations

import click

from thoth.cli_subcommands._option_policy import DEFAULT_HONOR, validate_inherited_options
from thoth.commands import CommandHandler
from thoth.completion.sources import operation_ids as _operation_ids_completer
from thoth.config import ConfigManager


@click.command(name="status")
@click.argument(
    "operation_id",
    metavar="OP_ID",
    required=False,
    shell_complete=_operation_ids_completer,
)
@click.pass_context
def status(ctx: click.Context, operation_id: str | None) -> None:
    """Check status of a research operation by ID."""
    validate_inherited_options(ctx, "status", DEFAULT_HONOR)

    if operation_id is None:
        click.echo("Error: status command requires an operation ID", err=True)
        ctx.exit(2)
    config_path = ctx.obj.get("config_path") if ctx.obj else None
    config_manager = ConfigManager()
    config_manager.load_all_layers({"config_path": config_path})
    handler = CommandHandler(config_manager)
    handler.status_command(operation_id=operation_id)
