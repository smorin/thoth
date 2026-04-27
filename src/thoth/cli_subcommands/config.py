"""`thoth config` Click subgroup with leaves: get, set, unset, list, path, edit."""

from __future__ import annotations

import sys

import click

_PASSTHROUGH_CONTEXT = {"ignore_unknown_options": True, "allow_extra_args": True}


@click.group(name="config", invoke_without_command=True)
@click.pass_context
def config(ctx: click.Context) -> None:
    """Inspect and edit configuration."""
    if ctx.invoked_subcommand is None:
        click.echo(
            "Error: config command requires an op (get|set|unset|list|path|edit|help)",
            err=True,
        )
        ctx.exit(2)


def _dispatch(op: str, args: tuple[str, ...]) -> None:
    from thoth.config_cmd import config_command

    rc = config_command(op, list(args))
    sys.exit(rc)


@config.command(name="get", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def config_get(args: tuple[str, ...]) -> None:
    """Get a configuration value."""
    _dispatch("get", args)


@config.command(name="set", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def config_set(args: tuple[str, ...]) -> None:
    """Set a configuration value."""
    _dispatch("set", args)


@config.command(name="unset", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def config_unset(args: tuple[str, ...]) -> None:
    """Unset a configuration value."""
    _dispatch("unset", args)


@config.command(name="list", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def config_list(args: tuple[str, ...]) -> None:
    """List all configuration values. Supports --json."""
    _dispatch("list", args)


@config.command(name="path", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def config_path(args: tuple[str, ...]) -> None:
    """Show config file path."""
    _dispatch("path", args)


@config.command(name="edit", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def config_edit(args: tuple[str, ...]) -> None:
    """Open config file in $EDITOR."""
    _dispatch("edit", args)


@config.command(name="help", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def config_help(args: tuple[str, ...]) -> None:
    """Show config command help."""
    _dispatch("help", args)
