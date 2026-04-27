"""`thoth providers` Click subgroup with leaves: list, models, check.

PR2 removes the legacy `providers --` separator shim AND the in-group
`--list/--models/--keys/--check/--refresh-cache/--no-cache` hidden
subcommands per Q6-PR2-C1. Every removed form is gated to its new
canonical via a `ctx.fail(...)` Click-native error.

Per Option A from PR2 brainstorming: the new leaves route to the existing
async `providers_command` (in commands.py) so user-visible output stays
bit-stable across the migration. Each leaf is a thin Click wrapper that
translates options -> `providers_command` kwargs.

Click treats any token after the group name (including `--list`) as a
subcommand-name lookup. To gate the legacy forms with our migration hint,
we register hidden subcommands whose only job is to `ctx.fail(...)`.
"""

from __future__ import annotations

import asyncio
import sys

import click

PROVIDER_CHOICES = ("openai", "perplexity", "mock")

_LEGACY_FLAG_TO_NEW_FORM: dict[str, str] = {
    "--list": "thoth providers list",
    "--models": "thoth providers models",
    "--keys": "thoth providers check",
    "--check": "thoth providers check",
    "--refresh-cache": "thoth providers models --refresh-cache",
    "--no-cache": "thoth providers models --no-cache",
}


@click.group(
    name="providers",
    invoke_without_command=True,
    context_settings={"ignore_unknown_options": True},
)
@click.pass_context
def providers(ctx: click.Context) -> None:
    """Manage provider models and API keys."""
    if ctx.invoked_subcommand is not None:
        return

    # Q5-A row 4: bare `thoth providers` exits 2 (Click default for required subgroup).
    click.echo(ctx.get_help())
    ctx.exit(2)


def _make_legacy_gate(flag: str, new_form: str):
    @providers.command(
        name=flag,
        hidden=True,
        context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
    )
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    @click.pass_context
    def _gate(ctx: click.Context, args: tuple[str, ...]) -> None:
        ctx.fail(f"no such option: {flag} (use '{new_form}')")

    return _gate


for _flag, _new_form in _LEGACY_FLAG_TO_NEW_FORM.items():
    _make_legacy_gate(_flag, _new_form)


@providers.command(name="list")
@click.option(
    "--provider",
    "-P",
    "filter_provider",
    type=click.Choice(PROVIDER_CHOICES),
    help="Filter by provider",
)
@click.pass_context
def providers_list_cmd(ctx: click.Context, filter_provider: str | None) -> None:
    """List available providers."""
    from thoth import commands as _commands

    sys.exit(
        asyncio.run(
            _commands.providers_command(
                show_list=True,
                filter_provider=filter_provider,
            )
        )
    )


@providers.command(name="models")
@click.option(
    "--provider",
    "-P",
    "filter_provider",
    type=click.Choice(PROVIDER_CHOICES),
    help="Filter by provider",
)
@click.option("--refresh-cache", is_flag=True, help="Force-refresh the model cache")
@click.option("--no-cache", is_flag=True, help="Bypass the model cache for this call")
@click.pass_context
def providers_models_cmd(
    ctx: click.Context,
    filter_provider: str | None,
    refresh_cache: bool,
    no_cache: bool,
) -> None:
    """List provider models."""
    # Q5-A row 1: --refresh-cache and --no-cache are mutually exclusive.
    if refresh_cache and no_cache:
        raise click.BadParameter(
            "--refresh-cache and --no-cache are mutually exclusive",
            param_hint="--refresh-cache / --no-cache",
        )
    from thoth import commands as _commands

    sys.exit(
        asyncio.run(
            _commands.providers_command(
                show_models=True,
                filter_provider=filter_provider,
                refresh_cache=refresh_cache,
                no_cache=no_cache,
            )
        )
    )


@providers.command(name="check")
@click.pass_context
def providers_check_cmd(ctx: click.Context) -> None:
    """Check provider API key configuration."""
    from thoth import commands as _commands

    sys.exit(
        asyncio.run(
            _commands.providers_command(
                show_keys=True,
            )
        )
    )
