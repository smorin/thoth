"""`thoth status OP_ID` Click subcommand."""

from __future__ import annotations

import asyncio

import click

from thoth.cli_subcommands._option_policy import DEFAULT_HONOR, validate_inherited_options
from thoth.commands import CommandHandler, get_status_data
from thoth.completion.sources import operation_ids as _operation_ids_completer
from thoth.config import ConfigManager
from thoth.json_output import emit_error, emit_json


@click.command(name="status")
@click.argument(
    "operation_id",
    metavar="OP_ID",
    required=False,
    shell_complete=_operation_ids_completer,
)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def status(ctx: click.Context, operation_id: str | None, as_json: bool) -> None:
    """Check status of a research operation by ID."""
    validate_inherited_options(ctx, "status", DEFAULT_HONOR)

    if operation_id is None:
        if as_json:
            emit_error(
                "MISSING_OP_ID",
                "status command requires an operation ID",
                exit_code=2,
            )
        click.echo("Error: status command requires an operation ID", err=True)
        ctx.exit(2)

    if as_json:
        data = asyncio.run(get_status_data(operation_id))
        if data is None:
            emit_error(
                "OPERATION_NOT_FOUND",
                f"Operation {operation_id} not found",
                {"operation_id": operation_id},
                exit_code=6,
            )
        emit_json(data)

    # Default Rich path
    config_path = ctx.obj.get("config_path") if ctx.obj else None
    config_manager = ConfigManager()
    config_manager.load_all_layers({"config_path": config_path})
    handler = CommandHandler(config_manager)
    handler.status_command(operation_id=operation_id)
