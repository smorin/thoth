"""`thoth list` Click subcommand. File named list_cmd.py to avoid Python
keyword shadow; the registered command name is "list"."""

from __future__ import annotations

import asyncio

import click

from thoth.cli_subcommands._option_policy import DEFAULT_HONOR, validate_inherited_options
from thoth.commands import CommandHandler, get_list_data
from thoth.config import ConfigManager
from thoth.json_output import emit_json


@click.command(name="list")
@click.option("--all", "show_all", is_flag=True, help="Include completed operations")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def list_cmd(ctx: click.Context, show_all: bool, as_json: bool) -> None:
    """List research operations."""
    validate_inherited_options(ctx, "list", DEFAULT_HONOR)

    config_path = ctx.obj.get("config_path") if ctx.obj else None
    profile = ctx.obj.get("profile") if ctx.obj else None
    config_manager = ConfigManager()
    cli_args: dict[str, object] = {"config_path": config_path}
    if profile:
        cli_args["_profile"] = profile
    config_manager.load_all_layers(cli_args)

    if as_json:
        emit_json(asyncio.run(get_list_data(show_all=show_all)))

    handler = CommandHandler(config_manager)
    handler.list_command(show_all=show_all)
