"""Click CLI command definition and entry-point wiring.

Houses the top-level `cli()` click command plus `main()` (the
`[project.scripts] thoth` entry point). Also owns `handle_error`,
the top-level exception presenter.
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys
from pathlib import Path

import click

import thoth.config as _thoth_config
import thoth.run as _thoth_run
import thoth.signals as _thoth_signals
from thoth.commands import (
    CommandHandler,
    providers_check,
    providers_command,
    providers_list,
    providers_models,
)
from thoth.config import BUILTIN_MODES, THOTH_VERSION, ConfigManager
from thoth.context import AppContext
from thoth.errors import ThothError
from thoth.help import (
    COMMAND_NAMES,
    HELP_TOPICS,
    ThothGroup,
    show_auth_help,
    show_config_help,
    show_init_help,
    show_list_help,
    show_modes_help,
    show_providers_help,
    show_status_help,
)
from thoth.interactive import enter_interactive_mode
from thoth.models import InteractiveInitialSettings
from thoth.run import console, resume_operation
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
    import inspect

    if inspect.iscoroutine(_result):
        asyncio.run(_result)


@click.group(
    cls=ThothGroup,
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.pass_context
@click.option("--mode", "-m", "mode_opt", help="Research mode")
@click.option("--prompt", "-q", "prompt_opt", help="Research prompt")
@click.option("--prompt-file", "-F", help="Read prompt from file (use - for stdin)")
@click.option("--async", "-A", "async_mode", is_flag=True, help="Submit and exit")
@click.option("--resume", "-R", "resume_id", help="Resume operation by ID")
@click.option("--project", "-p", help="Project name")
@click.option("--output-dir", "-o", help="Override output directory")
@click.option(
    "--provider",
    "-P",
    type=click.Choice(["openai", "perplexity", "mock"]),
    help="Single provider",
)
@click.option(
    "--input-file",
    help=(
        "Use the file at PATH as input for this mode. Use when feeding a "
        "non-thoth document, an older run, or a file from a different project."
    ),
)
@click.option(
    "--auto",
    is_flag=True,
    help=(
        "Pick up the latest output from the previous mode in the same "
        "--project directory. The happy path for chaining modes."
    ),
)
@click.option("--verbose", "-v", is_flag=True, help="Enable debug output")
@click.option("--version", "-V", is_flag=True, help="Show version and exit")
@click.option(
    "--api-key-openai", help="API key for OpenAI provider (not recommended; prefer env vars)"
)
@click.option(
    "--api-key-perplexity",
    help="API key for Perplexity provider (not recommended; prefer env vars)",
)
@click.option("--api-key-mock", help="API key for Mock provider (not recommended; prefer env vars)")
@click.option("--config", "-c", "config_path", help="Path to custom config file")
@click.option("--combined", is_flag=True, help="Generate combined report from multiple providers")
@click.option("--quiet", "-Q", is_flag=True, help="Minimal output during execution")
@click.option(
    "--no-metadata",
    is_flag=True,
    help="Disable metadata headers and prompt section in output files",
)
@click.option("--timeout", "-T", type=float, help="Override request timeout in seconds")
@click.option("--interactive", "-i", is_flag=True, help="Enter interactive prompt mode")
@click.option("--clarify", is_flag=True, help="Start interactive mode in Clarification Mode")
@click.option(
    "--pick-model",
    "-M",
    "pick_model",
    is_flag=True,
    help="Interactively pick a model (immediate modes only)",
)
def cli(
    ctx,
    mode_opt,
    prompt_opt,
    prompt_file,
    async_mode,
    resume_id,
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
    ctx.obj["resume_id"] = resume_id
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

    if config_path:
        _thoth_config._config_path = Path(config_path).expanduser().resolve()

    if version:
        console.print(f"Thoth v{THOTH_VERSION}")
        sys.exit(0)

    # Group-level mutex validators. These assume --async / --resume /
    # --prompt-file / --prompt / --input-file / --auto remain top-level
    # global options on the @click.group. If a subcommand later takes
    # ownership of one of these flags (e.g., --resume migrating to a
    # `thoth resume` subcommand in PR2), move the corresponding check
    # to that subcommand's callback.
    if async_mode and resume_id:
        raise click.BadParameter("Cannot use --async with --resume")

    if prompt_file and prompt_opt:
        raise click.BadParameter("Cannot use --prompt-file with --prompt")

    if input_file and auto:
        raise click.BadParameter("Cannot use --input-file with --auto")

    if False:  # P16 PR1: imperative dispatch removed in Task 14
        # The block below is the pre-refactor body verbatim. `args` was the
        # `nargs=-1` positional that we removed from the @click.group decorator
        # — referenced here only to keep the historical logic visible during
        # PR review. Tasks 4-10 register subcommands; Task 14 deletes this.
        args: tuple[str, ...] = ()
        final_mode = None
        final_prompt = None

        if not (args and args[0] in COMMAND_NAMES):
            if len(args) >= 2:
                if args[0] in BUILTIN_MODES:
                    final_mode = args[0]
                    final_prompt = " ".join(args[1:])
                else:
                    if len(args[0].split()) == 1 and not args[0].startswith("-"):
                        console.print(f"[red]Error:[/red] Unknown mode: {args[0]}")
                        console.print(
                            f"[yellow]Available modes:[/yellow] {', '.join(BUILTIN_MODES.keys())}"
                        )
                        sys.exit(1)
                    final_mode = "default"
                    final_prompt = " ".join(args)
            elif len(args) == 1:
                if prompt_opt:
                    final_mode = args[0]
                    final_prompt = prompt_opt
                else:
                    final_mode = "default"
                    final_prompt = args[0]
            else:
                final_mode = mode_opt or "default"
                final_prompt = prompt_opt

        if prompt_file:
            from thoth.config import get_config

            prompt_cfg = get_config()
            max_bytes = int(
                prompt_cfg.data.get("execution", {}).get("prompt_max_bytes", 1024 * 1024)
            )
            final_prompt = _read_prompt_input(prompt_file, max_bytes)

        if pick_model and (
            resume_id or interactive or (args and args[0] in COMMAND_NAMES) or not final_prompt
        ):
            raise click.BadParameter(
                "--pick-model only applies to research runs "
                "(not with --resume, --interactive, commands, or without a prompt)"
            )

        if interactive:
            cli_api_keys = {
                "openai": api_key_openai,
                "perplexity": api_key_perplexity,
                "mock": api_key_mock,
            }

            initial_settings = InteractiveInitialSettings(
                mode=final_mode,
                provider=provider,
                prompt=final_prompt,
                async_mode=async_mode,
                cli_api_keys=cli_api_keys,
                clarify_mode=clarify,
            )

            asyncio.run(
                enter_interactive_mode(
                    initial_settings=initial_settings,
                    project=project,
                    output_dir=output_dir,
                    config_path=config_path,
                    verbose=verbose,
                    quiet=quiet,
                    no_metadata=no_metadata,
                    timeout=timeout,
                )
            )
            return

        if args and args[0] in COMMAND_NAMES:
            config_manager = ConfigManager()
            config_manager.load_all_layers({"config_path": config_path})
            handler = CommandHandler(config_manager)

            command = args[0]
            if command == "init":
                handler.init_command(config_path=config_path)
                return
            elif command == "status":
                if len(args) < 2:
                    console.print("[red]Error:[/red] status command requires an operation ID")
                    sys.exit(1)
                handler.status_command(operation_id=args[1])
                return
            elif command == "list":
                show_all = "--all" in args
                handler.list_command(show_all=show_all)
                return
            elif command == "providers":
                sub = args[1] if len(args) >= 2 else None
                config_manager = ConfigManager()
                config_manager.load_all_layers({"config_path": config_path})
                cfg = config_manager
                # New subcommand forms
                if sub == "list":
                    sys.exit(providers_list(cfg))
                elif sub == "models":
                    sys.exit(providers_models(cfg))
                elif sub == "check":
                    sys.exit(providers_check(cfg))
                elif sub in (None, "--help", "help"):
                    show_providers_help()
                    sys.exit(0)
                else:
                    # Legacy forms: thoth providers -- --list / --models / etc.
                    # Click strips the '--' separator so sub is the flag itself.
                    all_args = list(args[1:]) + list(ctx.args)
                    is_legacy = any(
                        a in ("--list", "--models", "--keys", "--refresh-cache", "--no-cache")
                        for a in all_args
                    )
                    if is_legacy:
                        click.echo(
                            "warning: 'thoth providers -- ...' is deprecated; "
                            "use 'thoth providers list|models|check'",
                        )
                        show_models = "--models" in all_args
                        show_list = "--list" in all_args
                        show_keys = "--keys" in all_args
                        refresh_cache = "--refresh-cache" in all_args
                        no_cache = "--no-cache" in all_args
                        filter_provider = None

                        if refresh_cache and no_cache:
                            console.print(
                                "[red]Error:[/red] Cannot use --refresh-cache and "
                                "--no-cache together"
                            )
                            sys.exit(1)

                        for i, arg in enumerate(all_args):
                            if arg in ["--provider", "-P"] and i + 1 < len(all_args):
                                filter_provider = all_args[i + 1]
                                break

                        if not filter_provider and provider:
                            filter_provider = provider

                        asyncio.run(
                            providers_command(
                                show_models=show_models,
                                show_list=show_list,
                                show_keys=show_keys,
                                filter_provider=filter_provider,
                                refresh_cache=refresh_cache,
                                no_cache=no_cache,
                            )
                        )
                        return
                    else:
                        click.echo(f"Unknown providers subcommand: {sub}", err=True)
                        sys.exit(2)
            elif command == "config":
                from thoth.config_cmd import config_command

                if len(args) < 2:
                    console.print(
                        "[red]Error:[/red] config command requires an op "
                        "(get|set|unset|list|path|edit|help)"
                    )
                    sys.exit(2)
                op = args[1]
                rest = list(args[2:]) + list(ctx.args)
                rc = config_command(op, rest)
                sys.exit(rc)
            elif command == "modes":
                from thoth.modes_cmd import modes_command

                if len(args) >= 2 and not args[1].startswith("-"):
                    op = args[1]
                    rest = list(args[2:]) + list(ctx.args)
                else:
                    op = None
                    rest = list(args[1:]) + list(ctx.args)
                rc = modes_command(op, rest)
                sys.exit(rc)
            elif command == "help":
                if len(args) > 1:
                    help_command = args[1]
                    if help_command == "init":
                        show_init_help()
                    elif help_command == "status":
                        show_status_help()
                    elif help_command == "list":
                        show_list_help()
                    elif help_command == "providers":
                        show_providers_help()
                    elif help_command == "config":
                        show_config_help()
                    elif help_command == "modes":
                        show_modes_help()
                    elif help_command == "auth":
                        show_auth_help()
                    else:
                        console.print(f"[red]Error:[/red] Unknown command: {help_command}")
                        console.print(
                            f"[yellow]Available commands:[/yellow] {', '.join(HELP_TOPICS)}"
                        )
                        console.print("\nUse 'thoth help' for general help")
                else:
                    console.print(ctx.get_help())
                return

        if final_prompt is not None and final_prompt.strip() == "":
            raise click.BadParameter("Prompt cannot be empty")

        model_override = None
        if pick_model and final_mode and final_prompt:
            from thoth.config import get_config, is_background_model

            mode_cfg = BUILTIN_MODES.get(final_mode, {})
            raw_model = mode_cfg.get("model")
            model_name = raw_model if isinstance(raw_model, str) else None
            if is_background_model(model_name):
                click.echo(
                    "Error: --pick-model is only supported for quick (non-deep-research) modes.\n"
                    f"       Mode '{final_mode}' uses {model_name}.\n"
                    "       Interactive model selection for deep-research models would change\n"
                    "       the research quality and cost profile; edit ~/.thoth/config.toml\n"
                    "       to override the model for a deep-research mode.",
                    err=True,
                )
                ctx.exit(2)
            else:
                from thoth.interactive_picker import (
                    immediate_models_for_provider,
                )
                from thoth.interactive_picker import (
                    pick_model as _pick,
                )

                raw_provider = mode_cfg.get("provider", "openai")
                provider_name = raw_provider if isinstance(raw_provider, str) else "openai"
                model_override = _pick(immediate_models_for_provider(provider_name, get_config()))

        if resume_id:
            app_ctx = _build_app_context(verbose)
            asyncio.run(resume_operation(resume_id, verbose, ctx=app_ctx))
        elif final_mode and final_prompt:
            cli_api_keys = {
                "openai": api_key_openai,
                "perplexity": api_key_perplexity,
                "mock": api_key_mock,
            }
            _run_research_default(
                mode=final_mode,
                prompt=final_prompt,
                async_mode=async_mode,
                project=project,
                output_dir=output_dir,
                provider=provider,
                input_file=input_file,
                auto=auto,
                verbose=verbose,
                cli_api_keys=cli_api_keys,
                combined=combined,
                quiet=quiet,
                no_metadata=no_metadata,
                timeout_override=timeout,
                model_override=model_override,
            )
        else:
            console.print(ctx.get_help())


# === Subcommand registrations ===
# T5-T10 will append additional `cli.add_command(...)` lines below as each
# admin subcommand migrates into `cli_subcommands/`. Keep imports here
# (after the @click.group callback, before main()) so module-level import
# order stays predictable.
from thoth.cli_subcommands import init as _init_mod  # noqa: E402

cli.add_command(_init_mod.init)

from thoth.cli_subcommands import status as _status_mod  # noqa: E402

cli.add_command(_status_mod.status)

from thoth.cli_subcommands import list_cmd as _list_mod  # noqa: E402

cli.add_command(_list_mod.list_cmd)


def main():
    signal.signal(signal.SIGINT, handle_sigint)

    try:
        cli()
    except Exception as e:
        import traceback

        traceback.print_exc()
        handle_error(e)


__all__ = ["cli", "handle_error", "main"]
