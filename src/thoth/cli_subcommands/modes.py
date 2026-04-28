"""`thoth modes` Click subgroup. PR2 ships `list` only.

PR2 removes the PR1.5 `ModesGroup` unknown-arg dispatcher, the
bare-`modes` shortcut, and the five hidden `--json/--show-secrets/
--full/--name/--source` legacy commands per Q2-PR2-A. Each removed
flag is gated to its `thoth modes list <flag>` canonical via Q6-C1
using the same hidden-subcommand pattern as `providers` (T6) — Click
treats post-group tokens as subcommand-name lookups, so an in-callback
gate alone does not intercept.

P12 will add `add`, `set`, `unset` leaves here.
"""

from __future__ import annotations

import sys

import click

from thoth.cli_subcommands._option_policy import (
    DEFAULT_HONOR,
    NO_INHERITED_OPTIONS,
    inherited_value,
    validate_inherited_options,
)
from thoth.completion.sources import mode_names as _mode_names_completer

_PASSTHROUGH_CONTEXT = {"ignore_unknown_options": True, "allow_extra_args": True}

_LEGACY_FLAG_TO_NEW_FORM: dict[str, str] = {
    "--json": "thoth modes list --json",
    "--show-secrets": "thoth modes list --show-secrets",
    "--full": "thoth modes list --full",
    "--name": "thoth modes list --name",
    "--source": "thoth modes list --source",
}


@click.group(
    name="modes",
    invoke_without_command=True,
    context_settings={"ignore_unknown_options": True},
)
@click.pass_context
def modes(ctx: click.Context) -> None:
    """List research modes with provider/model/kind."""
    if ctx.invoked_subcommand is not None:
        return
    validate_inherited_options(ctx, "modes", NO_INHERITED_OPTIONS)
    # Q5-A row 5: bare `thoth modes` exits 2 (no leaf default).
    click.echo(ctx.get_help())
    ctx.exit(2)


def _make_legacy_gate(flag: str, new_form: str):
    @modes.command(
        name=flag,
        hidden=True,
        context_settings=_PASSTHROUGH_CONTEXT,
    )
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    @click.pass_context
    def _gate(ctx: click.Context, args: tuple[str, ...]) -> None:
        ctx.fail(f"no such option: {flag} (use '{new_form}')")

    return _gate


for _flag, _new_form in _LEGACY_FLAG_TO_NEW_FORM.items():
    _make_legacy_gate(_flag, _new_form)


@modes.command(name="list", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.option(
    "--name",
    "name",
    default=None,
    help="Show detail for a single mode",
    shell_complete=_mode_names_completer,
)
@click.pass_context
def modes_list(ctx: click.Context, args: tuple[str, ...], name: str | None) -> None:
    """List research modes."""
    validate_inherited_options(ctx, "modes list", DEFAULT_HONOR)

    from thoth.modes_cmd import modes_command

    # Re-emit --name back into the passthrough args so modes_command parses it.
    rebuilt = list(args)
    if name is not None:
        rebuilt.extend(["--name", name])

    config_path = inherited_value(ctx, "config_path")
    if config_path is None:
        rc = modes_command("list", rebuilt)
    else:
        rc = modes_command("list", rebuilt, config_path=config_path)
    sys.exit(rc)


# Future: P12 adds `add`, `set`, `unset` leaves here.
