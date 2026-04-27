"""`thoth modes` Click subgroup. PR1 ships `list` only (= current default
behavior); P12 will add `add`, `set`, `unset`."""

from __future__ import annotations

import sys
import warnings

import click

_PASSTHROUGH_CONTEXT = {"ignore_unknown_options": True, "allow_extra_args": True}


class ModesGroup(click.Group):
    def invoke(self, ctx: click.Context):
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r".*protected_args.*",
                category=DeprecationWarning,
            )
            args = list(ctx.protected_args) + list(ctx.args)
        if args and args[0] not in self.commands:
            from thoth.modes_cmd import modes_command

            rc = modes_command(args[0], args[1:])
            sys.exit(rc)
        return super().invoke(ctx)


@click.group(
    name="modes",
    cls=ModesGroup,
    invoke_without_command=True,
    context_settings=_PASSTHROUGH_CONTEXT,
    epilog='JSON output uses schema_version: "1".',
)
@click.pass_context
def modes(ctx: click.Context) -> None:
    """List research modes with provider/model/kind.

    Use `thoth modes list --json` for machine-readable output.
    """
    if ctx.invoked_subcommand is None:
        # No leaf: behave as `modes list` (current default)
        from thoth.modes_cmd import modes_command

        rc = modes_command(None, list(ctx.args))
        sys.exit(rc)


@modes.command(
    name="list",
    context_settings=_PASSTHROUGH_CONTEXT,
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def modes_list(args: tuple[str, ...]) -> None:
    """List research modes."""
    from thoth.modes_cmd import modes_command

    rc = modes_command("list", list(args))
    sys.exit(rc)


def _dispatch_default(args: list[str]) -> None:
    from thoth.modes_cmd import modes_command

    rc = modes_command(None, args)
    sys.exit(rc)


@modes.command(name="--json", hidden=True, context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def modes_legacy_json(args: tuple[str, ...]) -> None:
    _dispatch_default(["--json", *args])


@modes.command(name="--show-secrets", hidden=True, context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def modes_legacy_show_secrets(args: tuple[str, ...]) -> None:
    _dispatch_default(["--show-secrets", *args])


@modes.command(name="--full", hidden=True, context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def modes_legacy_full(args: tuple[str, ...]) -> None:
    _dispatch_default(["--full", *args])


@modes.command(name="--name", hidden=True, context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("name", required=False)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def modes_legacy_name(name: str | None, args: tuple[str, ...]) -> None:
    forwarded = ["--name"]
    if name is not None:
        forwarded.append(name)
    forwarded.extend(args)
    _dispatch_default(forwarded)


@modes.command(name="--source", hidden=True, context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("source", required=False)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def modes_legacy_source(source: str | None, args: tuple[str, ...]) -> None:
    forwarded = ["--source"]
    if source is not None:
        forwarded.append(source)
    forwarded.extend(args)
    _dispatch_default(forwarded)


# Future: P12 adds `add`, `set`, `unset` leaves here.
