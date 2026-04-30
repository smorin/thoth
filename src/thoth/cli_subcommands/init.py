"""`thoth init` Click subcommand.

Thin wrapper around CommandHandler.init_command(). Behavior is unchanged
from the pre-P16 imperative dispatch (cli.py:298-300).
"""

from __future__ import annotations

import click

from thoth.cli_subcommands._option_policy import DEFAULT_HONOR, validate_inherited_options
from thoth.commands import CommandHandler, get_init_data
from thoth.config import ConfigManager
from thoth.json_output import emit_error, emit_json, run_json_thoth_boundary


@click.command(name="init")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.option(
    "--non-interactive",
    is_flag=True,
    help="Skip interactive prompts (required with --json)",
)
@click.option(
    "--user",
    "user",
    is_flag=True,
    help="Write to the user-tier config (XDG)",
)
@click.option(
    "--hidden",
    "hidden",
    is_flag=True,
    help="Write to ./.thoth.config.toml instead of ./thoth.config.toml",
)
@click.option(
    "--force",
    "force",
    is_flag=True,
    help="Overwrite an existing config file",
)
@click.pass_context
def init(
    ctx: click.Context,
    as_json: bool,
    non_interactive: bool,
    user: bool,
    hidden: bool,
    force: bool,
) -> None:
    """Initialize thoth configuration."""
    validate_inherited_options(ctx, "init", DEFAULT_HONOR)

    if user and hidden:
        raise click.UsageError("--user and --hidden are mutually exclusive")

    config_path = ctx.obj.get("config_path") if ctx.obj else None

    # Default CLI behavior writes the visible project file ./thoth.config.toml.
    # `--user` / `--hidden` / explicit `--config` override. The direct
    # `init_command()` / `get_init_data()` API keeps the legacy "no args ->
    # user XDG config" semantics, so the project-file default is materialized
    # here at the CLI boundary.
    if config_path is None and not user and not hidden:
        config_path = "./thoth.config.toml"

    if as_json:
        if not non_interactive:
            emit_error(
                "JSON_REQUIRES_NONINTERACTIVE",
                "thoth init --json requires --non-interactive",
                exit_code=2,
            )
        data = run_json_thoth_boundary(
            lambda: get_init_data(
                non_interactive=True,
                config_path=config_path,
                user=user,
                hidden=hidden,
                force=force,
            )
        )
        emit_json(data)

    # `init` writes a target file and must not pre-load user/project config:
    # `init --user` should still repair or create the XDG config when the
    # current project has an unrelated config ambiguity.
    handler = CommandHandler(ConfigManager())
    # Only thread the new flags through when they're set, so monkeypatched
    # init_command stubs that predate P21c (signature `(self, config_path=None)`)
    # keep working.
    extra_kwargs: dict[str, bool] = {}
    if user:
        extra_kwargs["user"] = True
    if hidden:
        extra_kwargs["hidden"] = True
    if force:
        extra_kwargs["force"] = True
    handler.init_command(config_path=config_path, **extra_kwargs)
