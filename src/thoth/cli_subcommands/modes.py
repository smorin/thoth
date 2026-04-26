"""`thoth modes` Click subgroup. PR1 ships `list` only (= current default
behavior); P12 will add `add`, `set`, `unset`."""

from __future__ import annotations

import sys

import click


@click.group(
    name="modes",
    invoke_without_command=True,
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
@click.argument("args", nargs=-1)
@click.pass_context
def modes(ctx: click.Context, args: tuple[str, ...]) -> None:
    """List research modes with provider/model/kind."""
    if ctx.invoked_subcommand is None:
        # No leaf: behave as `modes list` (current default)
        from thoth.modes_cmd import modes_command
        rc = modes_command(None, list(args))
        sys.exit(rc)


# Future: P12 adds `add`, `set`, `unset` leaves here.
