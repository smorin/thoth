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

from thoth.cli_subcommands import providers as _providers_mod  # noqa: E402

cli.add_command(_providers_mod.providers)

from thoth.cli_subcommands import config as _config_mod  # noqa: E402

cli.add_command(_config_mod.config)

from thoth.cli_subcommands import modes as _modes_mod  # noqa: E402

cli.add_command(_modes_mod.modes)

from thoth.cli_subcommands import help_cmd as _help_mod  # noqa: E402

cli.add_command(_help_mod.help_cmd)


def main():
    signal.signal(signal.SIGINT, handle_sigint)

    try:
        cli()
    except Exception as e:
        import traceback

        traceback.print_exc()
        handle_error(e)


__all__ = ["cli", "handle_error", "main"]
