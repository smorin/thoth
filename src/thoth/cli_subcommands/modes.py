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
from thoth.completion.sources import mode_kind as _mode_kind_completer
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
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.option("--source", "source", default="all", help="Filter by source")
@click.option(
    "--kind",
    "kind",
    type=click.Choice(["immediate", "background"]),
    default=None,
    help="Filter by execution kind (P18)",
    shell_complete=_mode_kind_completer,
)
@click.option("--show-secrets", "show_secrets", is_flag=True, help="Reveal masked secrets")
@click.pass_context
def modes_list(
    ctx: click.Context,
    args: tuple[str, ...],
    name: str | None,
    as_json: bool,
    source: str,
    kind: str | None,
    show_secrets: bool,
) -> None:
    """List research modes."""
    validate_inherited_options(ctx, "modes list", DEFAULT_HONOR)

    config_path = inherited_value(ctx, "config_path")
    profile = inherited_value(ctx, "profile")

    if as_json:
        from thoth.json_output import emit_json, run_json_thoth_boundary
        from thoth.modes_cmd import get_modes_list_data

        emit_json(
            run_json_thoth_boundary(
                lambda: get_modes_list_data(
                    name=name,
                    source=source,
                    show_secrets=show_secrets,
                    config_path=config_path,
                    profile=profile,
                    kind=kind,
                )
            )
        )

    from thoth.modes_cmd import modes_command

    # Re-emit typed options back into the passthrough args so modes_command
    # parses them via its inline flag parser (Rich-rendering path).
    rebuilt = list(args)
    if name is not None:
        rebuilt.extend(["--name", name])
    if source != "all":
        rebuilt.extend(["--source", source])
    if kind is not None:
        rebuilt.extend(["--kind", kind])
    if show_secrets:
        rebuilt.append("--show-secrets")

    if config_path is None:
        rc = modes_command("list", rebuilt)
    else:
        rc = modes_command("list", rebuilt, config_path=config_path)
    sys.exit(rc)


_MODES_MUTATOR_HONOR: frozenset[str] = frozenset({"config_path", "profile"})


def _make_modes_leaf(op_name: str):
    """Generate a click leaf for `thoth modes <op_name>` driven by
    _OP_SPECS. Mirrors the existing _make_legacy_gate factory pattern.

    The leaf:
    - Uses _PASSTHROUGH_CONTEXT so positional args + op-specific flags
      flow through to modes_cmd's parser
    - Validates inherited options against _MODES_MUTATOR_HONOR (root
      --profile IS honored — overlay-tier writes)
    - Branches on --json: JSON path uses get_modes_data_from_args +
      emit_json/emit_error; human path uses modes_command (which calls
      _op which calls _emit_human_receipt)
    - Inherits root --profile by appending to args when present
    """

    @modes.command(
        name=op_name,
        context_settings=_PASSTHROUGH_CONTEXT,
        help=f"`thoth modes {op_name}` — see `thoth help modes` for examples.",
    )
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    @click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
    @click.pass_context
    def _leaf(ctx: click.Context, args: tuple[str, ...], as_json: bool) -> None:
        validate_inherited_options(ctx, f"modes {op_name}", _MODES_MUTATOR_HONOR)
        config_path = inherited_value(ctx, "config_path")
        profile = inherited_value(ctx, "profile")

        rebuilt = list(args)
        if profile is not None and "--profile" not in rebuilt:
            rebuilt.extend(["--profile", profile])

        if as_json:
            from thoth.json_output import emit_error, emit_json
            from thoth.modes_cmd import get_modes_data_from_args

            data, exit_code = get_modes_data_from_args(op_name, rebuilt, config_path=config_path)
            if data.get("error"):
                emit_error(data["error"], data.get("message", ""), exit_code=exit_code)
            emit_json(data)  # NoReturn
            return  # unreachable; emit_json calls sys.exit
        else:
            from thoth.modes_cmd import modes_command

            if config_path is None:
                rc = modes_command(op_name, rebuilt)
            else:
                rc = modes_command(op_name, rebuilt, config_path=config_path)
            sys.exit(rc)

    return _leaf


# Generate all six mutator leaves at import time. Per-command tasks
# (4-9) register their _OP_SPECS entries; this loop instantiates the
# matching click leaf for each.
for _op_name in ("add", "set", "unset", "remove", "rename", "copy"):
    _make_modes_leaf(_op_name)
