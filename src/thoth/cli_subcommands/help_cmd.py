"""`thoth help [TOPIC]` thin alias. Forwards to `thoth [TOPIC] --help`
except for the `auth` topic, which has no corresponding subcommand and
maps to show_auth_help() directly."""

from __future__ import annotations

import click


@click.command(name="help")
@click.argument("topic", required=False)
@click.pass_context
def help_cmd(ctx: click.Context, topic: str | None) -> None:
    """Show help (general or for a specific topic)."""
    if topic is None:
        # Show top-level group help
        click.echo(ctx.parent.get_help())
        return

    if topic == "auth":
        from thoth.help import show_auth_help
        show_auth_help()
        return

    # Forward to the subcommand's --help
    parent = ctx.parent
    target_cmd = parent.command.get_command(parent, topic)
    if target_cmd is None:
        click.echo(f"Unknown help topic: {topic}", err=True)
        click.echo(f"Available topics: {', '.join(sorted(parent.command.commands.keys()))}, auth", err=True)
        ctx.exit(2)

    sub_ctx = click.Context(target_cmd, info_name=topic, parent=parent)
    click.echo(sub_ctx.get_help())
