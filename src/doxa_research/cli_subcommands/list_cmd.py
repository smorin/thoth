"""`doxa list` Click subcommand. File named list_cmd.py to avoid Python
keyword shadow; the registered command name is "list"."""

from __future__ import annotations

import asyncio

import click

from doxa_research.cli_subcommands._config_context import load_config_from_ctx
from doxa_research.cli_subcommands._option_policy import DEFAULT_HONOR, validate_inherited_options
from doxa_research.commands import CommandHandler, get_list_data
from doxa_research.json_output import emit_json, run_json_doxa_boundary


@click.command(name="list")
@click.option("--all", "show_all", is_flag=True, help="Include completed operations")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def list_cmd(ctx: click.Context, show_all: bool, as_json: bool) -> None:
    """List research operations."""
    validate_inherited_options(ctx, "list", DEFAULT_HONOR)

    if as_json:
        config_manager = run_json_doxa_boundary(lambda: load_config_from_ctx(ctx))
        emit_json(asyncio.run(get_list_data(show_all=show_all, config=config_manager)))

    config_manager = load_config_from_ctx(ctx)
    handler = CommandHandler(config_manager)
    handler.list_command(show_all=show_all)
