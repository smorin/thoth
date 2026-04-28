"""Command-specific help text renderers."""

from __future__ import annotations

import warnings

import click
from rich.console import Console

console = Console()


# Two-section split for the Click group help renderer.
RUN_COMMANDS: tuple[str, ...] = ("ask", "resume", "status", "list")
ADMIN_COMMANDS: tuple[str, ...] = (
    "init",
    "config",
    "modes",
    "providers",
    "completion",
    "help",
)


def _run_research_default(*args, **kwargs):
    # Lazy import to avoid circular import (cli.py imports from help.py)
    from thoth.cli import _run_research_default as _impl

    return _impl(*args, **kwargs)


def _dispatch_click_fallback(ctx: click.Context, args: list[str]):
    # Lazy import to avoid circular import (cli.py imports ThothGroup).
    from thoth.cli import _dispatch_click_fallback as _impl

    return _impl(ctx, args, _run_research_default)


class ThothGroup(click.Group):
    """Top-level Click group for `thoth`.

    Adds three behaviors a stock click.Group can't provide:
      1. resolve_command returns None instead of raising on unknown args
         (so invoke can dispatch mode-positional or bare-prompt fallback).
      2. invoke routes positional mode names to the research path.
      3. invoke routes bare prompts to default-mode research.

    The two-section help renderer is added in Task 11.
    """

    def parse_args(self, ctx: click.Context, args: list[str]):
        # Q6-PR2-C1: legacy --resume / -R flag is gated to the new subcommand.
        # Scan the raw argv BEFORE delegating to super().parse_args so we can
        # emit a Click-native error with the migration hint on stderr.
        for token in args:
            if token in ("--resume", "-R") or token.startswith("--resume="):
                ctx.fail("no such option: --resume (use 'thoth resume OP_ID')")
        return super().parse_args(ctx, args)

    def resolve_command(self, ctx: click.Context, args: list[str]):
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError:
            # Caller (invoke) will handle mode-positional and bare-prompt cases.
            return None, None, args

    def invoke(self, ctx: click.Context):
        # Imported lazily so tests can monkeypatch thoth.config.BUILTIN_MODES.
        from thoth.config import BUILTIN_MODES

        # ctx.protected_args is required in Click 8.x for group dispatch (ctx.args
        # only holds the first token). Deprecated in Click 9.0; revisit when we
        # bump Click. Suppressed narrowly to avoid noise in user output / CI logs.
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r".*protected_args.*",
                category=DeprecationWarning,
            )
            args = list(ctx.protected_args) + list(ctx.args)
        if args:
            first = args[0]
            # Path 1: registered subcommand → standard dispatch
            if first in self.commands:
                return super().invoke(ctx)
            # Path 2: positional mode dispatch
            if first in BUILTIN_MODES:
                return _dispatch_click_fallback(ctx, args)
            # Path 3: bare-prompt fallback (whole arg vector is the prompt)
            return _dispatch_click_fallback(ctx, args)
        # No args: option-only research/resume/interactive fallback.
        return _dispatch_click_fallback(ctx, args)

    def format_commands(self, ctx: click.Context, formatter):
        """Render commands in two sections: Run research / Manage thoth."""
        registered = set(self.commands.keys())

        run_rows = [
            (name, self.commands[name].get_short_help_str(limit=60))
            for name in RUN_COMMANDS
            if name in registered
        ]
        admin_rows = [
            (name, self.commands[name].get_short_help_str(limit=60))
            for name in ADMIN_COMMANDS
            if name in registered
        ]

        if run_rows:
            with formatter.section("Run research"):
                formatter.write_dl(run_rows)
        if admin_rows:
            with formatter.section("Manage thoth"):
                formatter.write_dl(admin_rows)

    def format_epilog(self, ctx: click.Context, formatter):
        """Render the modes-positional epilog block + worked examples."""
        from thoth.config import BUILTIN_MODES

        with formatter.section("Modes (positional)"):
            modes_str = ", ".join(sorted(BUILTIN_MODES))
            formatter.write_text(f"Pass as the first positional argument: {modes_str}")
            formatter.write_paragraph()
            formatter.write_text("Run `thoth modes` for provider, model, and kind per mode.")
            formatter.write_paragraph()
            formatter.write_text('Example: thoth deep_research "explain transformers"')

        with formatter.section("Workflow chain"):
            formatter.write_text(
                "clarification → exploration → deep_dive → tutorial → solution → prd → tdd"
            )

        with formatter.section("Examples"):
            formatter.write_text('thoth "how does DNS work"')
            formatter.write_text('thoth clarification "k8s networking" --project k8s')
            formatter.write_text("thoth deep_research --auto --project k8s --async")
            formatter.write_text("thoth resume op_abc123")
            formatter.write_text('Debug API issues: thoth deep_research "topic" -v')

        super().format_epilog(ctx, formatter)


def show_config_help():
    """Show detailed help for the config command."""
    console.print("\n[bold]thoth config[/bold] - Inspect and edit configuration")
    console.print("\n[bold]Usage:[/bold]")
    console.print("  thoth config <OP> [ARGS...]")
    console.print("\n[bold]Ops:[/bold]")
    console.print("  get <KEY> [--layer L] [--raw] [--json] [--show-secrets]")
    console.print("     Print a single value from the merged config.")
    console.print("  set <KEY> <VALUE> [--project] [--string]")
    console.print("     Write a value to the user config (or project with --project).")
    console.print("  unset <KEY> [--project]")
    console.print("     Remove a key from the target file (empty tables are pruned).")
    console.print("  list [--layer L] [--keys] [--json] [--show-secrets]")
    console.print("     Print the merged config (or a single layer).")
    console.print("  path [--project]")
    console.print("     Print the target config file path.")
    console.print("  edit [--project]")
    console.print("     Open the target config file in $EDITOR (fallback: vi).")
    console.print("  help")
    console.print("     Show this help.")
    console.print("\n[bold]Examples:[/bold]")
    console.print("  $ thoth config get general.default_mode")
    console.print("  $ thoth config set general.default_mode exploration")
    console.print("  $ thoth config set --project execution.poll_interval 15")
    console.print("  $ thoth config list --keys")
    console.print("  $ thoth config path")
    console.print("\n[bold]Notable keys:[/bold]")
    console.print("  execution.prompt_max_bytes  Cap on --prompt-file / stdin bytes")
    console.print("                              (default: 1048576 = 1 MiB)")
    console.print("\n[bold]Notes:[/bold]")
    console.print("  API key values are masked by default; use --show-secrets to reveal.")
    console.print("  Writes preserve comments and formatting of the target TOML file.")


def render_auth_help() -> str:
    return (
        "Authentication — recommended order:\n"
        "\n"
        "1. Environment variables (recommended):\n"
        "     export OPENAI_API_KEY=sk-...\n"
        "     export PERPLEXITY_API_KEY=pplx-...\n"
        "\n"
        "2. Config file (persistent, per-machine): ~/.thoth/config.toml\n"
        "     [providers.openai]\n"
        '     api_key = "sk-..."\n'
        "\n"
        "3. CLI flags (last resort — exposes keys in shell history; not recommended):\n"
        '     thoth --api-key-openai sk-... deep_research "..."\n'
    )


def show_auth_help() -> None:
    console.print(render_auth_help(), markup=False)


__all__ = [
    "ADMIN_COMMANDS",
    "RUN_COMMANDS",
    "ThothGroup",
    "render_auth_help",
    "show_auth_help",
    "show_config_help",
]
