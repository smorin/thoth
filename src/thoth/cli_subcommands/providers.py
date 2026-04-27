"""`thoth providers` Click subgroup with leaves: list, models, check.

PR1 preserves the existing `providers -- --list` legacy shim path by
NOT routing the bare `thoth providers` invocation through this subgroup —
that bare-no-leaf path falls through to the imperative dispatch in cli.py
which still handles the legacy form. PR2 removes that shim entirely.
"""

from __future__ import annotations

import asyncio
import sys

import click

from thoth.config import get_config

PROVIDER_CHOICES = ("openai", "perplexity", "mock")


@click.group(
    name="providers",
    invoke_without_command=True,
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
    epilog=(
        "\b\n"
        "--models              List available models\n"
        "--provider, -P        Filter by specific provider\n"
        "thoth providers models  List available models\n"
        "OpenAI models are fetched dynamically and cached locally."
    ),
)
@click.pass_context
def providers(ctx: click.Context) -> None:
    """Manage provider models and API keys. OpenAI models are fetched dynamically."""
    if ctx.invoked_subcommand is not None:
        return

    args = list(ctx.args)
    legacy_flags = {"--list", "--models", "--keys", "--refresh-cache", "--no-cache"}
    if any(arg in legacy_flags for arg in args):
        click.echo(
            "warning: 'thoth providers -- ...' is deprecated; "
            "use 'thoth providers list|models|check'",
        )
        from thoth import commands as _commands

        cfg = get_config()
        if "--list" in args:
            sys.exit(_commands.providers_list(cfg))
        if "--models" in args:
            sys.exit(_commands.providers_models(cfg))
        if "--keys" in args or "--check" in args:
            sys.exit(_commands.providers_check(cfg))
        sys.exit(0)

    if args:
        click.echo(f"Unknown providers arguments: {' '.join(args)}", err=True)
        ctx.exit(2)

    click.echo(ctx.get_help())
    ctx.exit(0)


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

    cfg = get_config()
    sys.exit(_commands.providers_list(cfg, filter_provider=filter_provider))


@providers.command(name="models")
@click.option(
    "--provider",
    "-P",
    "filter_provider",
    type=click.Choice(PROVIDER_CHOICES),
    help="Filter by provider",
)
@click.pass_context
def providers_models_cmd(ctx: click.Context, filter_provider: str | None) -> None:
    """List provider models."""
    from thoth import commands as _commands

    cfg = get_config()
    sys.exit(_commands.providers_models(cfg, filter_provider=filter_provider))


@providers.command(name="check")
@click.pass_context
def providers_check_cmd(ctx: click.Context) -> None:
    """Check provider API key configuration."""
    from thoth import commands as _commands

    cfg = get_config()
    sys.exit(_commands.providers_check(cfg))


def _legacy_warning() -> None:
    click.echo(
        "warning: 'thoth providers -- ...' is deprecated; use 'thoth providers list|models|check'",
    )


def _run_legacy(args: list[str]) -> None:
    from thoth import commands as _commands

    refresh_cache = "--refresh-cache" in args
    no_cache = "--no-cache" in args
    filter_provider = None
    for i, arg in enumerate(args):
        if arg in ("--provider", "-P") and i + 1 < len(args):
            filter_provider = args[i + 1]
            break
        if arg.startswith("--provider="):
            filter_provider = arg.split("=", 1)[1]
            break
    asyncio.run(
        _commands.providers_command(
            show_models="--models" in args,
            show_list="--list" in args,
            show_keys="--keys" in args,
            filter_provider=filter_provider,
            refresh_cache=refresh_cache,
            no_cache=no_cache,
        )
    )


@providers.command(
    name="--list",
    hidden=True,
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def providers_legacy_list_cmd(ctx: click.Context, args: tuple[str, ...]) -> None:
    _legacy_warning()
    _run_legacy(["--list", *args])


@providers.command(
    name="--models",
    hidden=True,
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def providers_legacy_models_cmd(ctx: click.Context, args: tuple[str, ...]) -> None:
    _legacy_warning()
    _run_legacy(["--models", *args])


@providers.command(
    name="--keys",
    hidden=True,
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def providers_legacy_keys_cmd(ctx: click.Context, args: tuple[str, ...]) -> None:
    _legacy_warning()
    _run_legacy(["--keys", *args])
