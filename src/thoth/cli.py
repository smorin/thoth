"""Click CLI command definition and entry-point wiring.

Houses the top-level `cli()` click command plus `main()` (the
`[project.scripts] thoth` entry point). Also owns `handle_error`,
the top-level exception presenter.
"""

from __future__ import annotations

import asyncio
import inspect
import os
import signal
import sys
import warnings
from collections.abc import Callable
from pathlib import Path

import click

import thoth.config as _thoth_config
import thoth.run as _thoth_run
import thoth.signals as _thoth_signals
from thoth.cli_subcommands._options import _research_options
from thoth.config import THOTH_VERSION, ConfigManager
from thoth.context import AppContext
from thoth.errors import ThothError
from thoth.help import (
    ThothGroup,
)
from thoth.run import console
from thoth.signals import handle_sigint


def _read_prompt_input(path_or_dash: str, max_bytes: int) -> str:
    """Read prompt text from a file path or '-' for stdin, capped at max_bytes."""
    if path_or_dash == "-":
        data = sys.stdin.read(max_bytes + 1)
    else:
        try:
            size = Path(path_or_dash).stat().st_size
        except FileNotFoundError as e:
            raise click.BadParameter(f"Prompt file not found: {path_or_dash}") from e
        if size > max_bytes:
            raise click.BadParameter(f"Prompt file exceeds {max_bytes} bytes (size: {size})")
        try:
            with open(path_or_dash, encoding="utf-8") as f:
                data = f.read(max_bytes + 1)
        except UnicodeDecodeError as e:
            raise click.BadParameter(f"Prompt file must be UTF-8: {path_or_dash}") from e
    if len(data) > max_bytes:
        raise click.BadParameter(f"Prompt input exceeds {max_bytes} bytes")
    return data.strip()


def _build_app_context(verbose: bool) -> AppContext:
    """Construct the per-invocation AppContext.

    The returned ctx shares its `interrupt_event` with `thoth.signals` so that
    the cooperative SIGINT handler's `set()` is observable via `ctx`.
    """
    return AppContext(
        config=ConfigManager(),
        console=console,
        interrupt_event=_thoth_signals._interrupt_event,
        verbose=verbose,
    )


def _run_maybe_async(result) -> None:
    if inspect.iscoroutine(result):
        asyncio.run(result)


def _click_remainder_args(ctx: click.Context) -> list[str]:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r".*protected_args.*",
            category=DeprecationWarning,
        )
        return list(ctx.protected_args) + list(ctx.args)


def _apply_config_path(config_path: object) -> None:
    if config_path:
        _thoth_config._config_path = Path(str(config_path)).expanduser().resolve()


def _has_supplied_value(value: object) -> bool:
    return value is not None and value is not False


def _version_conflicts(ctx: click.Context, opts: dict) -> list[str]:
    conflicts: list[str] = []
    if _click_remainder_args(ctx):
        conflicts.append("arguments")

    option_labels = {
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
        "api_key_openai": "--api-key-openai",
        "api_key_perplexity": "--api-key-perplexity",
        "api_key_mock": "--api-key-mock",
        "config_path": "--config",
        "combined": "--combined",
        "quiet": "--quiet",
        "no_metadata": "--no-metadata",
        "timeout": "--timeout",
        "interactive": "--interactive",
        "clarify": "--clarify",
        "pick_model": "--pick-model",
    }
    for key, label in option_labels.items():
        if _has_supplied_value(opts.get(key)):
            conflicts.append(label)
    return conflicts


def _invoke_group_callback(ctx: click.Context) -> None:
    if ctx.meta.get("thoth_group_callback_invoked"):
        return
    if ctx.command.callback is not None:
        ctx.invoke(ctx.command.callback, **ctx.params)
    ctx.meta["thoth_group_callback_invoked"] = True


def _prompt_max_bytes() -> int:
    config = _thoth_config.get_config()
    raw = config.data.get("execution", {}).get("prompt_max_bytes", 1024 * 1024)
    try:
        max_bytes = int(raw)
    except (TypeError, ValueError) as e:
        raise click.BadParameter("execution.prompt_max_bytes must be an integer") from e
    if max_bytes < 1:
        raise click.BadParameter("execution.prompt_max_bytes must be positive")
    return max_bytes


def _resolve_mode_and_prompt(args: list[str], opts: dict) -> tuple[str, str | None]:
    mode_opt = opts.get("mode_opt")
    prompt_opt = opts.get("prompt_opt")
    prompt_file = opts.get("prompt_file")

    if args:
        first = args[0]
        if first in _thoth_config.BUILTIN_MODES:
            mode = first
            prompt = " ".join(args[1:]) if len(args) > 1 else prompt_opt
        elif (
            len(args) >= 2
            and not mode_opt
            and not first.startswith("-")
            and ("-" in first or "_" in first)
        ):
            console.print(f"[red]Error:[/red] Unknown mode: {first}")
            sys.exit(1)
        else:
            mode = mode_opt or "default"
            prompt = " ".join(args)
    else:
        mode = mode_opt or "default"
        prompt = prompt_opt

    if prompt_file:
        prompt = _read_prompt_input(str(prompt_file), _prompt_max_bytes())

    return str(mode), prompt


def _extract_fallback_options(args: list[str], opts: dict) -> tuple[list[str], dict]:
    """Parse global options Click left behind after positional research args."""
    value_options = {
        "--mode": "mode_opt",
        "-m": "mode_opt",
        "--prompt": "prompt_opt",
        "-q": "prompt_opt",
        "--prompt-file": "prompt_file",
        "-F": "prompt_file",
        "--project": "project",
        "-p": "project",
        "--output-dir": "output_dir",
        "-o": "output_dir",
        "--provider": "provider",
        "-P": "provider",
        "--input-file": "input_file",
        "--api-key-openai": "api_key_openai",
        "--api-key-perplexity": "api_key_perplexity",
        "--api-key-mock": "api_key_mock",
        "--config": "config_path",
        "-c": "config_path",
        "--timeout": "timeout",
        "-T": "timeout",
    }

    def _validate_provider(value: str) -> None:
        if value not in {"openai", "perplexity", "mock"}:
            raise click.BadParameter(
                f"'{value}' is not one of 'openai', 'perplexity', 'mock'",
                param_hint="'--provider' / '-P'",
            )

    def _coerce_value(option: str, key: str, value: str) -> object:
        if key == "timeout":
            try:
                return float(value)
            except ValueError as e:
                raise click.BadParameter(
                    f"{option} must be a floating-point number",
                    param_hint=option,
                ) from e
        return value

    flag_options = {
        "--async": "async_mode",
        "-A": "async_mode",
        "--auto": "auto",
        "--verbose": "verbose",
        "-v": "verbose",
        "--combined": "combined",
        "--quiet": "quiet",
        "-Q": "quiet",
        "--no-metadata": "no_metadata",
        "--interactive": "interactive",
        "-i": "interactive",
        "--clarify": "clarify",
        "--pick-model": "pick_model",
        "-M": "pick_model",
    }

    parsed = dict(opts)
    positional: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--":
            positional.extend(args[i + 1 :])
            break
        if arg in value_options:
            if i + 1 >= len(args):
                raise click.BadParameter(f"{arg} requires a value")
            key = value_options[arg]
            value = args[i + 1]
            if key == "provider":
                _validate_provider(value)
            parsed[key] = _coerce_value(arg, key, value)
            i += 2
            continue
        if arg in flag_options:
            parsed[flag_options[arg]] = True
            i += 1
            continue
        matched_equals = False
        for option, key in value_options.items():
            prefix = f"{option}="
            if arg.startswith(prefix):
                value = arg[len(prefix) :]
                if key == "provider":
                    _validate_provider(value)
                parsed[key] = _coerce_value(option, key, value)
                matched_equals = True
                break
        if matched_equals:
            i += 1
            continue
        positional.append(arg)
        i += 1

    return positional, parsed


def _pick_model_override(mode: str, config: ConfigManager) -> str:
    mode_cfg = config.get_mode_config(mode)
    raw_model = mode_cfg.get("model")
    model_name = raw_model if isinstance(raw_model, str) else None
    # P18: gate on declared `kind` first (mode_cfg in scope here); falls back
    # through `mode_kind` to the substring heuristic for legacy user modes.
    if _thoth_config.mode_kind(mode_cfg) == "background":
        raise click.BadParameter(
            "--pick-model is only supported for modes with kind='immediate'. "
            f"Mode '{mode}' uses {model_name} (kind='background')."
        )

    from thoth.interactive_picker import immediate_models_for_provider
    from thoth.interactive_picker import pick_model as _pick

    raw_provider = mode_cfg.get("provider", "openai")
    provider_name = raw_provider if isinstance(raw_provider, str) else "openai"
    return _pick(immediate_models_for_provider(provider_name, config))


def _enter_interactive_from_options(
    *,
    mode: str | None,
    prompt: str | None,
    opts: dict,
) -> None:
    from thoth.interactive import enter_interactive_mode
    from thoth.models import InteractiveInitialSettings

    cli_api_keys = {
        "openai": opts.get("api_key_openai"),
        "perplexity": opts.get("api_key_perplexity"),
        "mock": opts.get("api_key_mock"),
    }
    initial_settings = InteractiveInitialSettings(
        mode=mode,
        provider=opts.get("provider"),
        prompt=prompt,
        async_mode=bool(opts.get("async_mode")),
        cli_api_keys=cli_api_keys,
        clarify_mode=bool(opts.get("clarify")),
    )
    _run_maybe_async(
        enter_interactive_mode(
            initial_settings=initial_settings,
            project=opts.get("project"),
            output_dir=opts.get("output_dir"),
            config_path=opts.get("config_path"),
            verbose=bool(opts.get("verbose")),
            quiet=bool(opts.get("quiet")),
            no_metadata=bool(opts.get("no_metadata")),
            timeout=opts.get("timeout"),
        )
    )


def _dispatch_click_fallback(
    ctx: click.Context,
    args: list[str],
    research_runner: Callable[..., object],
) -> None:
    """Run research/resume/interactive fallback after Click has parsed globals."""
    _invoke_group_callback(ctx)
    opts = ctx.obj or {}
    args, opts = _extract_fallback_options(args, opts)
    _apply_config_path(opts.get("config_path"))

    if opts.get("interactive"):
        mode, prompt = _resolve_mode_and_prompt(args, opts)
        _enter_interactive_from_options(mode=mode, prompt=prompt, opts=opts)
        return

    if not args and not opts.get("prompt_opt") and not opts.get("prompt_file"):
        click.echo(ctx.get_help())
        ctx.exit(0)

    mode, prompt = _resolve_mode_and_prompt(args, opts)
    if not prompt:
        raise click.BadParameter("Prompt cannot be empty")

    model_override = None
    if opts.get("pick_model"):
        config = _thoth_config.get_config()
        model_override = _pick_model_override(mode, config)

    cli_api_keys = {
        "openai": opts.get("api_key_openai"),
        "perplexity": opts.get("api_key_perplexity"),
        "mock": opts.get("api_key_mock"),
    }
    research_runner(
        mode=mode,
        prompt=prompt,
        async_mode=bool(opts.get("async_mode")),
        project=opts.get("project"),
        output_dir=opts.get("output_dir"),
        provider=opts.get("provider"),
        input_file=opts.get("input_file"),
        auto=bool(opts.get("auto")),
        verbose=bool(opts.get("verbose")),
        cli_api_keys=cli_api_keys,
        combined=bool(opts.get("combined")),
        quiet=bool(opts.get("quiet")),
        no_metadata=bool(opts.get("no_metadata")),
        timeout_override=opts.get("timeout"),
        model_override=model_override,
        ctx_obj=None,
    )


def handle_error(error: Exception):
    """Display error with appropriate formatting"""
    if isinstance(error, ThothError):
        console.print(f"\n[red]Error:[/red] {error.message}")
        if error.suggestion:
            console.print(f"[yellow]Suggestion:[/yellow] {error.suggestion}")
        sys.exit(error.exit_code)
    elif isinstance(error, KeyboardInterrupt):
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(1)
    else:
        console.print(f"\n[red]Unexpected error:[/red] {str(error)}")
        console.print("[dim]Please report this issue[/dim]")
        if os.getenv("THOTH_DEBUG"):
            console.print_exception()
        sys.exit(127)


def _run_research_default(
    mode: str,
    prompt: str,
    *,
    async_mode: bool = False,
    project: str | None = None,
    output_dir: str | None = None,
    provider: str | None = None,
    input_file: str | None = None,
    auto: bool = False,
    verbose: bool = False,
    cli_api_keys: dict | None = None,
    combined: bool = False,
    quiet: bool = False,
    no_metadata: bool = False,
    timeout_override: float | None = None,
    model_override: str | None = None,
    ctx_obj=None,
) -> None:
    """Execute a research run with the given mode and prompt.

    Extracted from the bare-prompt branch of the pre-refactor cli callback.
    Called by ThothGroup.invoke for both mode-positional and bare-prompt paths.
    """
    app_ctx = _build_app_context(verbose) if ctx_obj is None else ctx_obj
    _result = _thoth_run.run_research(
        mode=mode,
        prompt=prompt,
        async_mode=async_mode,
        project=project,
        output_dir=output_dir,
        provider=provider,
        input_file=input_file,
        auto=auto,
        verbose=verbose,
        cli_api_keys=cli_api_keys or {},
        combined=combined,
        quiet=quiet,
        no_metadata=no_metadata,
        timeout_override=timeout_override,
        ctx=app_ctx,
        model_override=model_override,
    )
    _run_maybe_async(_result)


@click.group(
    cls=ThothGroup,
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.pass_context
@_research_options
@click.option("--version", "-V", is_flag=True, help="Show version and exit; must be used alone")
def cli(
    ctx,
    mode_opt,
    prompt_opt,
    prompt_file,
    async_mode,
    project,
    output_dir,
    provider,
    input_file,
    auto,
    verbose,
    version,
    api_key_openai,
    api_key_perplexity,
    api_key_mock,
    config_path,
    combined,
    quiet,
    no_metadata,
    timeout,
    interactive,
    clarify,
    pick_model,
):
    """thoth — research orchestration.

    Quick usage: thoth "PROMPT"
    Run research:    thoth ask "question" | thoth deep_research "topic" | thoth -m MODE -q PROMPT
    Manage thoth:    thoth init | thoth status OP | thoth list | thoth config ... | thoth providers ...

    For per-command help: thoth COMMAND --help
    """
    # Build shared context object that subcommands access via ctx.obj
    ctx.ensure_object(dict)
    # Store EVERY global option on ctx.obj so subcommands can read inherited state.
    ctx.obj["mode_opt"] = mode_opt
    ctx.obj["prompt_opt"] = prompt_opt
    ctx.obj["prompt_file"] = prompt_file
    ctx.obj["async_mode"] = async_mode
    ctx.obj["project"] = project
    ctx.obj["output_dir"] = output_dir
    ctx.obj["provider"] = provider
    ctx.obj["input_file"] = input_file
    ctx.obj["auto"] = auto
    ctx.obj["verbose"] = verbose
    ctx.obj["version"] = version
    ctx.obj["api_key_openai"] = api_key_openai
    ctx.obj["api_key_perplexity"] = api_key_perplexity
    ctx.obj["api_key_mock"] = api_key_mock
    ctx.obj["config_path"] = config_path
    ctx.obj["combined"] = combined
    ctx.obj["quiet"] = quiet
    ctx.obj["no_metadata"] = no_metadata
    ctx.obj["timeout"] = timeout
    ctx.obj["interactive"] = interactive
    ctx.obj["clarify"] = clarify
    ctx.obj["pick_model"] = pick_model

    if version:
        conflicts = _version_conflicts(ctx, ctx.obj)
        if conflicts:
            raise click.BadParameter(
                "--version must be used alone; remove other arguments/options: "
                + ", ".join(conflicts),
                param_hint="'--version' / '-V'",
            )
        console.print(f"Thoth v{THOTH_VERSION}")
        sys.exit(0)

    _apply_config_path(config_path)

    # Group-level mutex validators. These assume --async / --prompt-file /
    # --prompt / --input-file / --auto remain top-level global options on
    # the @click.group. If a subcommand later takes ownership of one of
    # these flags, move the corresponding check to that subcommand's
    # callback.
    if prompt_file and prompt_opt:
        raise click.BadParameter("Cannot use --prompt-file with --prompt")

    if input_file and auto:
        raise click.BadParameter("Cannot use --input-file with --auto")

    # Q5-A row 7: --clarify is meaningful only inside --interactive.
    if clarify and not interactive:
        raise click.BadParameter(
            "--clarify requires --interactive",
            param_hint="--clarify",
        )

    if pick_model:
        args = _click_remainder_args(ctx)
        first = args[0] if args else None
        if interactive or (first in ctx.command.commands if first else False):
            raise click.BadParameter("--pick-model only applies to research runs")
        if not args and not prompt_opt and not prompt_file:
            raise click.BadParameter("--pick-model only applies to research runs with a prompt")


# === Subcommand registrations ===
# T5-T10 will append additional `cli.add_command(...)` lines below as each
# admin subcommand migrates into `cli_subcommands/`. Keep imports here
# (after the @click.group callback, before main()) so module-level import
# order stays predictable.
from thoth.cli_subcommands import ask as _ask_mod  # noqa: E402

cli.add_command(_ask_mod.ask)

from thoth.cli_subcommands import resume as _resume_mod  # noqa: E402

cli.add_command(_resume_mod.resume)

from thoth.cli_subcommands import cancel as _cancel_mod  # noqa: E402

cli.add_command(_cancel_mod.cancel)

from thoth.cli_subcommands import init as _init_mod  # noqa: E402

cli.add_command(_init_mod.init)

from thoth.cli_subcommands import status as _status_mod  # noqa: E402

cli.add_command(_status_mod.status)

from thoth.cli_subcommands import list_cmd as _list_mod  # noqa: E402

cli.add_command(_list_mod.list_cmd)

from thoth.cli_subcommands import providers as _providers_mod  # noqa: E402

cli.add_command(_providers_mod.providers)

from thoth.cli_subcommands import config as _config_mod  # noqa: E402

cli.add_command(_config_mod.config)

from thoth.cli_subcommands import modes as _modes_mod  # noqa: E402

cli.add_command(_modes_mod.modes)

from thoth.cli_subcommands import help_cmd as _help_mod  # noqa: E402

cli.add_command(_help_mod.help_cmd)

from thoth.cli_subcommands import completion as _completion_mod  # noqa: E402

cli.add_command(_completion_mod.completion)


def main():
    signal.signal(signal.SIGINT, handle_sigint)

    try:
        cli()
    except Exception as e:
        import traceback

        traceback.print_exc()
        handle_error(e)


__all__ = ["cli", "handle_error", "main"]
