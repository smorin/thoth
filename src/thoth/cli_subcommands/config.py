"""`thoth config` Click subgroup with leaves: get, set, unset, list, path, edit."""

from __future__ import annotations

import sys

import click


@click.group(name="config")
def config() -> None:
    """Inspect and edit configuration."""


def _dispatch(op: str, args: tuple[str, ...]) -> None:
    from thoth.config_cmd import config_command
    rc = config_command(op, list(args))
    sys.exit(rc)


@config.command(name="get")
@click.argument("args", nargs=-1)
def config_get(args: tuple[str, ...]) -> None:
    """Get a configuration value."""
    _dispatch("get", args)


@config.command(name="set")
@click.argument("args", nargs=-1)
def config_set(args: tuple[str, ...]) -> None:
    """Set a configuration value."""
    _dispatch("set", args)


@config.command(name="unset")
@click.argument("args", nargs=-1)
def config_unset(args: tuple[str, ...]) -> None:
    """Unset a configuration value."""
    _dispatch("unset", args)


@config.command(
    name="list",
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
@click.argument("args", nargs=-1)
def config_list(args: tuple[str, ...]) -> None:
    """List all configuration values. Supports --json."""
    _dispatch("list", args)


@config.command(name="path")
@click.argument("args", nargs=-1)
def config_path(args: tuple[str, ...]) -> None:
    """Show config file path."""
    _dispatch("path", args)


@config.command(name="edit")
@click.argument("args", nargs=-1)
def config_edit(args: tuple[str, ...]) -> None:
    """Open config file in $EDITOR."""
    _dispatch("edit", args)
