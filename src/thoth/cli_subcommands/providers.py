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

from thoth.cli_subcommands._option_policy import (
    DEFAULT_HONOR,
    NO_INHERITED_OPTIONS,
    inherited_api_keys,
    inherited_value,
    pick_value,
    validate_inherited_options,
)
from thoth.completion.sources import provider_names as _provider_names_completer

PROVIDER_CHOICES = ("openai", "perplexity", "mock")

_PROVIDERS_LIST_HONOR = DEFAULT_HONOR | {
    "provider",
    "api_key_openai",
    "api_key_perplexity",
    "api_key_mock",
}
_PROVIDERS_MODELS_HONOR = _PROVIDERS_LIST_HONOR | {"timeout"}
_PROVIDERS_CHECK_HONOR = _PROVIDERS_LIST_HONOR


def _has_api_keys(keys: dict[str, str | None]) -> bool:
    return any(value is not None for value in keys.values())


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
    validate_inherited_options(ctx, "providers", NO_INHERITED_OPTIONS)

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
    shell_complete=_provider_names_completer,
)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def providers_list_cmd(ctx: click.Context, filter_provider: str | None, as_json: bool) -> None:
    """List available providers."""
    validate_inherited_options(ctx, "providers list", _PROVIDERS_LIST_HONOR)

    from thoth import commands as _commands
    from thoth.config import ConfigManager
    from thoth.json_output import emit_error, emit_json

    effective_provider = pick_value(filter_provider, ctx, "provider")

    if as_json:
        config_manager = ConfigManager()
        config_manager.load_all_layers({})
        data = _commands.get_providers_list_data(config_manager, filter_provider=effective_provider)
        if data.get("unknown"):
            emit_error(
                "UNKNOWN_PROVIDER",
                f"Unknown provider: {effective_provider}",
                {"provider": effective_provider},
                exit_code=1,
            )
        emit_json(data)

    keys = inherited_api_keys(ctx)
    if _has_api_keys(keys):
        sys.exit(
            asyncio.run(
                _commands.providers_command(
                    show_list=True,
                    filter_provider=effective_provider,
                    cli_api_keys=keys,
                )
            )
        )
    sys.exit(
        asyncio.run(
            _commands.providers_command(
                show_list=True,
                filter_provider=effective_provider,
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
    shell_complete=_provider_names_completer,
)
@click.option("--refresh-cache", is_flag=True, help="Force-refresh the model cache")
@click.option("--no-cache", is_flag=True, help="Bypass the model cache for this call")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def providers_models_cmd(
    ctx: click.Context,
    filter_provider: str | None,
    refresh_cache: bool,
    no_cache: bool,
    as_json: bool,
) -> None:
    """List provider models."""
    validate_inherited_options(ctx, "providers models", _PROVIDERS_MODELS_HONOR)

    # Q5-A row 1: --refresh-cache and --no-cache are mutually exclusive.
    if refresh_cache and no_cache:
        raise click.BadParameter(
            "--refresh-cache and --no-cache are mutually exclusive",
            param_hint="--refresh-cache / --no-cache",
        )
    from thoth import commands as _commands
    from thoth.config import ConfigManager
    from thoth.json_output import emit_json

    effective_provider = pick_value(filter_provider, ctx, "provider")

    if as_json:
        config_manager = ConfigManager()
        config_manager.load_all_layers({})
        emit_json(
            _commands.get_providers_models_data(config_manager, filter_provider=effective_provider)
        )

    keys = inherited_api_keys(ctx)
    timeout = inherited_value(ctx, "timeout")
    if timeout is not None:
        sys.exit(
            asyncio.run(
                _commands.providers_command(
                    show_models=True,
                    filter_provider=effective_provider,
                    refresh_cache=refresh_cache,
                    no_cache=no_cache,
                    cli_api_keys=keys,
                    timeout_override=timeout,
                )
            )
        )
    if _has_api_keys(keys):
        sys.exit(
            asyncio.run(
                _commands.providers_command(
                    show_models=True,
                    filter_provider=effective_provider,
                    refresh_cache=refresh_cache,
                    no_cache=no_cache,
                    cli_api_keys=keys,
                )
            )
        )
    sys.exit(
        asyncio.run(
            _commands.providers_command(
                show_models=True,
                filter_provider=effective_provider,
                refresh_cache=refresh_cache,
                no_cache=no_cache,
            )
        )
    )


@providers.command(name="check")
@click.option(
    "--provider",
    "-P",
    "filter_provider",
    type=click.Choice(PROVIDER_CHOICES),
    help="Filter by provider",
    shell_complete=_provider_names_completer,
)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def providers_check_cmd(ctx: click.Context, filter_provider: str | None, as_json: bool) -> None:
    """Check provider API key configuration."""
    validate_inherited_options(ctx, "providers check", _PROVIDERS_CHECK_HONOR)

    from thoth import commands as _commands
    from thoth.config import ConfigManager
    from thoth.json_output import emit_json

    effective_provider = pick_value(filter_provider, ctx, "provider")

    if as_json:
        config_manager = ConfigManager()
        config_manager.load_all_layers({})
        # Honor `--provider` by narrowing the providers view before checking.
        if effective_provider is not None:
            full = config_manager.data["providers"]
            config_manager.data["providers"] = {
                effective_provider: full.get(effective_provider, {})
            }
        emit_json(_commands.get_providers_check_data(config_manager))

    keys = inherited_api_keys(ctx)
    if _has_api_keys(keys):
        sys.exit(
            asyncio.run(
                _commands.providers_command(
                    show_keys=True,
                    filter_provider=effective_provider,
                    cli_api_keys=keys,
                )
            )
        )
    sys.exit(
        asyncio.run(
            _commands.providers_command(
                show_keys=True,
                filter_provider=effective_provider,
            )
        )
    )
