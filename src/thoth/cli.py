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
from thoth.commands import CommandHandler, providers_command
from thoth.config import BUILTIN_MODES, THOTH_VERSION, ConfigManager
from thoth.context import AppContext
from thoth.errors import ThothError
from thoth.help import (
    ThothCommand,
    build_epilog,
    show_config_help,
    show_init_help,
    show_list_help,
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
    context_settings=dict(allow_extra_args=True, allow_interspersed_args=True),
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
@click.option("--input-file", help="Use output from previous mode as input")
@click.option("--auto", is_flag=True, help="Automatically use latest relevant output as input")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug output")
@click.option("--version", "-V", is_flag=True, help="Show version and exit")
@click.option("--api-key-openai", help="API key for OpenAI provider")
@click.option("--api-key-perplexity", help="API key for Perplexity provider")
@click.option("--api-key-mock", help="API key for Mock provider")
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
):
    """Thoth - AI-Powered Research Assistant

    Quick usage: thoth "PROMPT"
    Advanced: thoth MODE "PROMPT"
    Commands: init, status, list, providers, help [COMMAND]

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

    if not (args and args[0] in ["init", "status", "list", "help", "providers", "config"]):
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

    if args and args[0] in ["init", "status", "list", "help", "providers", "config"]:
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
            all_args = list(args) + list(ctx.args)
            show_models = "--models" in all_args or "--models" in sys.argv
            show_list = "--list" in all_args or "--list" in sys.argv
            show_keys = "--keys" in all_args or "--keys" in sys.argv
            refresh_cache = "--refresh-cache" in all_args or "--refresh-cache" in sys.argv
            no_cache = "--no-cache" in all_args or "--no-cache" in sys.argv
            filter_provider = None

            if refresh_cache and no_cache:
                console.print(
                    "[red]Error:[/red] Cannot use --refresh-cache and --no-cache together"
                )
                console.print("  --refresh-cache: Updates the cache with fresh data")
                console.print("  --no-cache: Bypasses cache without updating it")
                sys.exit(1)

            for arg_list in [args, ctx.args, sys.argv]:
                for i, arg in enumerate(arg_list):
                    if arg in ["--provider", "-P"] and i + 1 < len(arg_list):
                        filter_provider = arg_list[i + 1]
                        break
                if filter_provider:
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
                else:
                    console.print(f"[red]Error:[/red] Unknown command: {help_command}")
                    console.print(
                        "[yellow]Available commands:[/yellow] init, status, list, providers, config"
                    )
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
