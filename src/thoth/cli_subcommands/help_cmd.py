"""`thoth help [TOPIC]` thin alias. Forwards to `thoth [TOPIC] --help`."""

from __future__ import annotations

from typing import cast

import click

from thoth.cli_subcommands._option_policy import (
    NO_INHERITED_OPTIONS,
    validate_inherited_options,
)


@click.command(name="help")
@click.argument("topic", required=False)
@click.pass_context
def help_cmd(ctx: click.Context, topic: str | None) -> None:
    """Show help (general or for a specific topic)."""
    validate_inherited_options(ctx, "help", NO_INHERITED_OPTIONS)

    parent = cast(click.Context, ctx.parent)
    parent_group = cast(click.Group, parent.command)

    if topic is None:
        # Show top-level group help
        click.echo(parent.get_help())
        return

    # Forward to the subcommand's --help
    target_cmd = parent_group.get_command(parent, topic)
    if target_cmd is None:
        click.echo(f"Unknown help topic: {topic}", err=True)
        click.echo(f"Available topics: {', '.join(sorted(parent_group.commands.keys()))}", err=True)
        ctx.exit(2)
        return

    sub_ctx = click.Context(target_cmd, info_name=topic, parent=parent)
    click.echo(sub_ctx.get_help())
