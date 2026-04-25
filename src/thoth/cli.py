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
    ThothCommand,
    build_epilog,
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
from thoth.run import console, resume_operation, run_research
from thoth.signals import handle_sigint


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


@click.command(
    cls=ThothCommand,
    context_settings=dict(
        allow_extra_args=True,
        allow_interspersed_args=True,
        ignore_unknown_options=True,
    ),
    epilog=build_epilog(),
)
@click.pass_context
@click.argument("args", nargs=-1)
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
    args,
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
    """Thoth - AI-Powered Research Assistant

    Quick usage: thoth "PROMPT"
    Advanced: thoth MODE "PROMPT"

    Examples:
      thoth "how does DNS work"
      thoth "best practices for REST APIs"
      thoth exploration "web frameworks"
      thoth help init
      thoth help status
    """
    if config_path:
        _thoth_config._config_path = Path(config_path).expanduser().resolve()

    if version:
        console.print(f"Thoth v{THOTH_VERSION}")
        sys.exit(0)

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
        if prompt_file == "-":
            stdin_data = sys.stdin.read(1024 * 1024)
            if len(stdin_data) >= 1024 * 1024:
                raise click.BadParameter("Stdin input exceeds 1MB limit")
            final_prompt = stdin_data.strip()
        else:
            with open(prompt_file) as f:
                final_prompt = f.read().strip()

    if pick_model:
        from thoth.config import is_background_model

        mode_cfg = BUILTIN_MODES.get(final_mode or "", {})
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
                            "[red]Error:[/red] Cannot use --refresh-cache and --no-cache together"
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
                    console.print(f"[yellow]Available commands:[/yellow] {', '.join(HELP_TOPICS)}")
                    console.print("\nUse 'thoth help' for general help")
            else:
                console.print(ctx.get_help())
            return

    if async_mode and resume_id:
        raise click.BadParameter("Cannot use --async with --resume")

    if prompt_file and prompt_opt:
        raise click.BadParameter("Cannot use --prompt-file with --prompt")

    if input_file and auto:
        raise click.BadParameter("Cannot use --input-file with --auto")

    if final_prompt is not None and final_prompt.strip() == "":
        raise click.BadParameter("Prompt cannot be empty")

    if resume_id:
        app_ctx = _build_app_context(verbose)
        asyncio.run(resume_operation(resume_id, verbose, ctx=app_ctx))
    elif final_mode and final_prompt:
        cli_api_keys = {
            "openai": api_key_openai,
            "perplexity": api_key_perplexity,
            "mock": api_key_mock,
        }
        app_ctx = _build_app_context(verbose)
        asyncio.run(
            run_research(
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
                ctx=app_ctx,
            )
        )
    else:
        console.print(ctx.get_help())


def main():
    signal.signal(signal.SIGINT, handle_sigint)

    try:
        cli()
    except Exception as e:
        import traceback

        traceback.print_exc()
        handle_error(e)


__all__ = ["cli", "handle_error", "main"]
