"""`thoth init` Click subcommand.

Thin wrapper around CommandHandler.init_command(). Behavior is unchanged
from the pre-P16 imperative dispatch (cli.py:298-300).
"""

from __future__ import annotations

import click

from thoth.cli_subcommands._option_policy import DEFAULT_HONOR, validate_inherited_options
from thoth.commands import CommandHandler, get_init_data
from thoth.config import ConfigManager
from thoth.json_output import emit_error, emit_json


@click.command(name="init")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.option(
    "--non-interactive",
    is_flag=True,
    help="Skip interactive prompts (required with --json)",
)
@click.pass_context
def init(ctx: click.Context, as_json: bool, non_interactive: bool) -> None:
    """Initialize thoth configuration."""
    validate_inherited_options(ctx, "init", DEFAULT_HONOR)

    config_path = ctx.obj.get("config_path") if ctx.obj else None

    if as_json:
        if not non_interactive:
            emit_error(
                "JSON_REQUIRES_NONINTERACTIVE",
                "thoth init --json requires --non-interactive",
                exit_code=2,
            )
        emit_json(get_init_data(non_interactive=True, config_path=config_path))

    profile = ctx.obj.get("profile") if ctx.obj else None
    config_manager = ConfigManager()
    cli_args: dict[str, object] = {"config_path": config_path}
    if profile:
        cli_args["_profile"] = profile
    config_manager.load_all_layers(cli_args)
    handler = CommandHandler(config_manager)
    handler.init_command(config_path=config_path)
