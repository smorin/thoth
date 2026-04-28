"""`thoth config` Click subgroup with leaves: get, set, unset, list, path, edit."""

from __future__ import annotations

import sys

import click

from thoth.cli_subcommands._option_policy import (
    DEFAULT_HONOR,
    NO_INHERITED_OPTIONS,
    inherited_value,
    validate_inherited_options,
)
from thoth.completion.sources import config_keys as _config_keys_completer

_PASSTHROUGH_CONTEXT = {"ignore_unknown_options": True, "allow_extra_args": True}


@click.group(name="config", invoke_without_command=True)
@click.pass_context
def config(ctx: click.Context) -> None:
    """Inspect and edit configuration."""
    if ctx.invoked_subcommand is None:
        validate_inherited_options(ctx, "config", NO_INHERITED_OPTIONS)
        click.echo(
            "Error: config command requires an op (get|set|unset|list|path|edit|help)",
            err=True,
        )
        ctx.exit(2)


def _dispatch(
    ctx: click.Context,
    op: str,
    args: tuple[str, ...],
    honored_options=DEFAULT_HONOR,
) -> None:
    from thoth.config_cmd import config_command

    validate_inherited_options(ctx, f"config {op}", honored_options)
    config_path = inherited_value(ctx, "config_path")
    if config_path is None:
        rc = config_command(op, list(args))
    else:
        rc = config_command(op, list(args), config_path=config_path)
    sys.exit(rc)


@config.command(name="get")
@click.argument("key", shell_complete=_config_keys_completer)
@click.option(
    "--layer",
    "layer",
    type=click.Choice(("defaults", "user", "project", "env", "cli")),
    default=None,
    help="Read from a specific config layer",
)
@click.option(
    "--raw",
    is_flag=True,
    help="Read pre-merge layer data (formatting only; does NOT bypass masking)",
)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON")
@click.option(
    "--show-secrets",
    is_flag=True,
    help="Reveal masked secret values (security-sensitive)",
)
@click.pass_context
def config_get(
    ctx: click.Context,
    key: str,
    layer: str | None,
    raw: bool,
    as_json: bool,
    show_secrets: bool,
) -> None:
    """Get a configuration value."""
    rebuilt: list[str] = [key]
    if layer is not None:
        rebuilt.extend(["--layer", layer])
    if raw:
        rebuilt.append("--raw")
    if as_json:
        rebuilt.append("--json")
    if show_secrets:
        rebuilt.append("--show-secrets")
    _dispatch(ctx, "get", tuple(rebuilt))


@config.command(name="set", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def config_set(ctx: click.Context, args: tuple[str, ...]) -> None:
    """Set a configuration value."""
    _dispatch(ctx, "set", args)


@config.command(name="unset", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def config_unset(ctx: click.Context, args: tuple[str, ...]) -> None:
    """Unset a configuration value."""
    _dispatch(ctx, "unset", args)


@config.command(name="list", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def config_list(ctx: click.Context, args: tuple[str, ...]) -> None:
    """List all configuration values. Supports --json."""
    _dispatch(ctx, "list", args)


@config.command(name="path", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def config_path(ctx: click.Context, args: tuple[str, ...]) -> None:
    """Show config file path."""
    _dispatch(ctx, "path", args)


@config.command(name="edit", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def config_edit(ctx: click.Context, args: tuple[str, ...]) -> None:
    """Open config file in $EDITOR."""
    _dispatch(ctx, "edit", args)


@config.command(name="help", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def config_help(ctx: click.Context, args: tuple[str, ...]) -> None:
    """Show config command help."""
    _dispatch(ctx, "help", args, NO_INHERITED_OPTIONS)
