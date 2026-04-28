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


@config.command(name="get")
@click.argument("key")
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
def config_get(key: str, layer: str | None, raw: bool, as_json: bool, show_secrets: bool) -> None:
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
    _dispatch("get", tuple(rebuilt))


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
