"""Shared policy for root options inherited by Click subcommands.

The top-level ``thoth`` group declares the full research option stack, so
Click accepts those options before any subcommand name. Each subcommand must
then explicitly declare which inherited values it honors; everything else is
rejected here to avoid silent no-ops.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import click

ROOT_OPTION_LABELS: dict[str, str] = {
    "mode_opt": "--mode",
    "prompt_opt": "--prompt",
    "prompt_file": "--prompt-file",
    "async_mode": "--async",
    "project": "--project",
    "output_dir": "--output-dir",
    "provider": "--provider",
    "input_file": "--input-file",
    "auto": "--auto",
    "verbose": "--verbose",
    "version": "--version",
    "api_key_openai": "--api-key-openai",
    "api_key_perplexity": "--api-key-perplexity",
    "api_key_gemini": "--api-key-gemini",
    "api_key_mock": "--api-key-mock",
    "config_path": "--config",
    "profile": "--profile",
    "combined": "--combined",
    "quiet": "--quiet",
    "no_metadata": "--no-metadata",
    "timeout": "--timeout",
    "out": "--out",
    "append": "--append",
    "interactive": "--interactive",
    "clarify": "--clarify",
    "pick_model": "--pick-model",
    "model": "--model",
    "cancel_on_interrupt": "--cancel-on-interrupt/--no-cancel-on-interrupt",
}

ROOT_OPTION_ORDER: tuple[str, ...] = tuple(ROOT_OPTION_LABELS)

# The smallest cross-command default: a custom config file can be honored by
# command handlers that load configuration. Other inherited options must opt in.
DEFAULT_HONOR: frozenset[str] = frozenset({"config_path", "profile"})
NO_INHERITED_OPTIONS: frozenset[str] = frozenset()


def inherited_value(ctx: click.Context, key: str) -> Any:
    """Return a value parsed by the root command, if any."""
    return (ctx.obj or {}).get(key)


def inherited_api_keys(ctx: click.Context) -> dict[str, str | None]:
    """Return provider API-key overrides parsed by the root command."""
    return {
        "openai": inherited_value(ctx, "api_key_openai"),
        "perplexity": inherited_value(ctx, "api_key_perplexity"),
        "gemini": inherited_value(ctx, "api_key_gemini"),
        "mock": inherited_value(ctx, "api_key_mock"),
    }


def pick_value(local: Any, ctx: click.Context, key: str) -> Any:
    """Prefer a subcommand-local value, falling back to the root value."""
    return local if local is not None else inherited_value(ctx, key)


def supplied_root_options(ctx: click.Context) -> set[str]:
    """Return root option parameter names supplied by the user.

    Click's parameter source is the robust signal here: flag defaults like
    ``False`` and value defaults like ``None`` are not treated as supplied.
    """
    root = ctx.find_root()
    supplied: set[str] = set()
    for key in ROOT_OPTION_ORDER:
        source = root.get_parameter_source(key)
        if source is not None and source is not click.core.ParameterSource.DEFAULT:
            supplied.add(key)
    return supplied


def validate_inherited_options(
    ctx: click.Context,
    command_path: str,
    honored_options: Iterable[str] = DEFAULT_HONOR,
) -> None:
    """Reject root options supplied before a subcommand unless explicitly honored."""
    honored = set(honored_options)
    disallowed = supplied_root_options(ctx) - honored - {"version"}
    if not disallowed:
        return

    labels = [ROOT_OPTION_LABELS[key] for key in ROOT_OPTION_ORDER if key in disallowed]
    option_word = "option" if len(labels) == 1 else "options"
    raise click.UsageError(
        f"no such {option_word} for 'thoth {command_path}': {', '.join(labels)}. "
        "This root option is not honored by that command."
    )


__all__ = [
    "DEFAULT_HONOR",
    "NO_INHERITED_OPTIONS",
    "inherited_api_keys",
    "inherited_value",
    "pick_value",
    "supplied_root_options",
    "validate_inherited_options",
]
