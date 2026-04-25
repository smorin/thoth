"""Command-specific help text renderers.

The click-based `ThothCommand` wrapper plus its epilog builder also live here
so the click CLI layer can stay focused on option plumbing.
"""

from __future__ import annotations

import click
from rich.console import Console

from thoth.config import BUILTIN_MODES, THOTH_VERSION
from thoth.paths import user_config_file

console = Console()


COMMANDS: tuple[tuple[str, str, str], ...] = (
    ("init", "", "Initialize configuration"),
    ("status", "<ID>", "Check operation status"),
    ("list", "", "List research operations"),
    ("providers", "", "Manage provider models and keys"),
    ("config", "<OP>", "Inspect and edit configuration"),
    ("modes", "", "List research modes with provider/model/kind"),
    ("help", "[COMMAND]", "Show help (general or command-specific)"),
)
COMMAND_NAMES: frozenset[str] = frozenset(name for name, _, _ in COMMANDS)
HELP_TOPICS: tuple[str, ...] = tuple(name for name, _, _ in COMMANDS if name != "help")


class ThothCommand(click.Command):
    """Custom command class to enhance help display"""

    def parse_args(self, ctx, args):
        """Override to intercept --help with subcommands"""
        if "--help" in args:
            help_index = args.index("--help")

            if help_index + 1 < len(args):
                subcommand = args[help_index + 1]

                if subcommand == "init":
                    show_init_help()
                    ctx.exit(0)
                elif subcommand == "status":
                    show_status_help()
                    ctx.exit(0)
                elif subcommand == "list":
                    show_list_help()
                    ctx.exit(0)
                elif subcommand == "providers":
                    show_providers_help()
                    ctx.exit(0)
                elif subcommand == "config":
                    show_config_help()
                    ctx.exit(0)
                elif subcommand == "modes":
                    show_modes_help()
                    ctx.exit(0)
                elif subcommand == "auth":
                    show_auth_help()
                    ctx.exit(0)

        return super().parse_args(ctx, args)

    def format_epilog(self, ctx, formatter):
        """Override to format epilog without rewrapping"""
        if self.epilog:
            formatter.write_paragraph()
            for line in self.epilog.split("\n"):
                if line:
                    formatter.write_text(line)
                else:
                    formatter.write_paragraph()


def build_epilog():
    """Build the epilog text with modes and examples"""
    lines = []

    lines.append("Commands:")
    label_width = max(len(f"{name} {sig}".rstrip()) for name, sig, _ in COMMANDS)
    for name, sig, desc in COMMANDS:
        label = f"{name} {sig}".rstrip()
        lines.append(f"  {label:<{label_width}}  {desc}")
    lines.append("")

    lines.append("Research Modes:")
    lines.append(f"  {', '.join(BUILTIN_MODES.keys())}")
    lines.append("  Run `thoth modes` for provider, model, and kind per mode.")
    lines.append("")
    lines.append("  Workflow chain (each step feeds the next via --auto):")
    lines.append("    clarification → exploration → deep_dive → tutorial → solution → prd → tdd")
    lines.append("")

    lines.append("Examples:")
    lines.append("  # Quick")
    lines.append('  $ thoth "how does DNS work"')
    lines.append("")
    lines.append("  # Sharpen, then research (chain with --auto)")
    lines.append('  $ thoth clarification "k8s networking" --project k8s')
    lines.append("  $ thoth exploration --auto --project k8s")
    lines.append("  $ thoth deep_research --auto --project k8s --async")
    lines.append("")
    lines.append("  # Resume a backgrounded job")
    lines.append("  $ thoth --resume op_abc123")
    lines.append("")
    lines.append("  # Debug API issues — show model, provider, timeouts, retries")
    lines.append('  $ thoth deep_research "topic" -v')
    lines.append("")
    lines.append("For detailed command help: thoth help [COMMAND]")

    return "\n".join(lines)


def show_init_help():
    """Show detailed help for the init command"""
    console.print("\n[bold]thoth init[/bold] - Initialize Thoth configuration")
    console.print("\n[bold]Description:[/bold]")
    console.print("  Sets up Thoth configuration file and verifies environment.")
    console.print("  Creates default configuration at ~/.thoth/config.toml")
    console.print("\n[bold]Usage:[/bold]")
    console.print("  thoth init")
    console.print("\n[bold]What it does:[/bold]")
    console.print("  • Checks Python and UV package manager")
    console.print("  • Creates configuration directory")
    console.print("  • Generates default config.toml file")
    console.print("  • Sets up provider API key placeholders")
    console.print("\n[bold]Configuration file location:[/bold]")
    console.print(f"  {user_config_file()}")
    console.print("\n[bold]After initialization:[/bold]")
    console.print("  1. Set your API keys as environment variables:")
    console.print("     export OPENAI_API_KEY='your-api-key'")
    console.print("     export PERPLEXITY_API_KEY='your-api-key'")
    console.print("  2. Or edit the config file directly")
    console.print("\n[bold]Examples:[/bold]")
    console.print("  # Initialize configuration")
    console.print("  $ thoth init")
    console.print("\n[bold]Related commands:[/bold]")
    console.print("  thoth help       - Show general help")


def show_status_help():
    """Show detailed help for the status command"""
    console.print("\n[bold]thoth status[/bold] - Check status of a research operation")
    console.print("\n[bold]Description:[/bold]")
    console.print("  Shows detailed status of a specific research operation,")
    console.print("  including progress, providers, and output files.")
    console.print("\n[bold]Usage:[/bold]")
    console.print("  thoth status <OPERATION_ID>")
    console.print("\n[bold]Arguments:[/bold]")
    console.print("  OPERATION_ID    The unique identifier for the operation")
    console.print("                  (e.g., research-20240803-143022-abc123...)")
    console.print("\n[bold]Information displayed:[/bold]")
    console.print("  • Operation ID and prompt")
    console.print("  • Current status (queued/running/completed/failed)")
    console.print("  • Start time and elapsed duration")
    console.print("  • Provider status for each LLM")
    console.print("  • Output file locations")
    console.print("\n[bold]Examples:[/bold]")
    console.print("  # Check status of a specific operation")
    console.print("  $ thoth status research-20240803-143022-1234abcd5678efgh")
    console.print("\n[bold]Related commands:[/bold]")
    console.print("  thoth list       - List all operations")
    console.print("  thoth help       - Show general help")


def show_list_help():
    """Show detailed help for the list command"""
    console.print("\n[bold]thoth list[/bold] - List research operations")
    console.print("\n[bold]Description:[/bold]")
    console.print("  Shows a table of research operations with their status.")
    console.print("  By default, shows only recent and active operations.")
    console.print("\n[bold]Usage:[/bold]")
    console.print("  thoth list [OPTIONS]")
    console.print("\n[bold]Options:[/bold]")
    console.print("  --all           Show all operations (not just recent/active)")
    console.print("\n[bold]Default behavior:[/bold]")
    console.print("  • Shows operations from the last 24 hours")
    console.print("  • Always shows running or queued operations")
    console.print("  • Sorted by creation time (newest first)")
    console.print("\n[bold]Table columns:[/bold]")
    console.print("  • ID       - Unique operation identifier")
    console.print("  • Prompt   - Research prompt (truncated if long)")
    console.print("  • Status   - Current status with color coding")
    console.print("  • Elapsed  - Time since operation started")
    console.print("  • Mode     - Research mode used")
    console.print("\n[bold]Examples:[/bold]")
    console.print("  # List recent operations")
    console.print("  $ thoth list")
    console.print("\n  # List all operations")
    console.print("  $ thoth list --all")
    console.print("\n[bold]Related commands:[/bold]")
    console.print("  thoth status     - Show details for specific operation")
    console.print("  thoth help       - Show general help")


def show_providers_help():
    """Show detailed help for the providers command"""
    console.print("\n[bold]thoth providers[/bold] - List providers and available models")
    console.print("\n[bold]Description:[/bold]")
    console.print("  Shows available providers and their configuration status,")
    console.print("  lists available models from each LLM provider,")
    console.print("  or displays API key configuration information.")
    console.print("  OpenAI models are fetched dynamically via API and cached locally.")
    console.print("  Model cache auto-refreshes after 1 week.")
    console.print("  Perplexity models are returned from a predefined list.")
    console.print("  Perplexity research execution is not implemented yet.")
    console.print("\n[bold]Usage:[/bold]")
    console.print("  thoth providers -- [OPTIONS]")
    console.print("\n[bold]Options:[/bold]")
    console.print("  --list                List available providers and their status")
    console.print("  --models              List available models from providers")
    console.print("  --keys                Show API key configuration for each provider")
    console.print("  --provider, -P        Filter by specific provider (with --models)")
    console.print("  --refresh-cache       Force refresh of cached model lists")
    console.print("  --no-cache            Bypass cache without updating it")
    console.print("\n[bold]Note:[/bold]")
    console.print("  Use -- before options to prevent parsing conflicts")
    console.print("\n[bold]Available providers:[/bold]")
    console.print("  • openai     - OpenAI GPT models (cached)")
    console.print("  • perplexity - Perplexity Sonar models (not implemented)")
    console.print("  • mock       - Mock provider for testing")
    console.print("\n[bold]Examples:[/bold]")
    console.print("  # List all available providers")
    console.print("  $ thoth providers -- --list")
    console.print("\n  # Show API key configuration")
    console.print("  $ thoth providers -- --keys")
    console.print("\n  # List all models from all providers")
    console.print("  $ thoth providers -- --models")
    console.print("\n  # List only OpenAI models")
    console.print("  $ thoth providers -- --models --provider openai")
    console.print("\n  # Force refresh cached models")
    console.print("  $ thoth providers -- --models --refresh-cache")
    console.print("\n  # Bypass cache without updating it")
    console.print("  $ thoth providers -- --models --no-cache")
    console.print("  $ thoth providers -- --models -P openai")
    console.print("\n[bold]Related commands:[/bold]")
    console.print("  thoth help       - Show general help")


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
    console.print("\n[bold]Notes:[/bold]")
    console.print("  API key values are masked by default; use --show-secrets to reveal.")
    console.print("  Writes preserve comments and formatting of the target TOML file.")


def show_modes_help():
    """Show detailed help for the modes command."""
    console.print("\n[bold]thoth modes[/bold] - List research modes with provider, model, and kind")
    console.print("\n[bold]Description:[/bold]")
    console.print("  Shows every research mode Thoth knows about: built-in modes,")
    console.print("  user-defined modes from `[modes.*]` in your config TOML, and")
    console.print("  modes that override a built-in.")
    console.print("\n[bold]Usage:[/bold]")
    console.print("  thoth modes [list] [OPTIONS]")
    console.print("\n[bold]Options:[/bold]")
    console.print("  --json                    Emit machine-readable JSON")
    console.print("  --source builtin|user|overridden|all   Filter by origin")
    console.print("  --name <mode>             Show detail view for one mode")
    console.print("  --full                    With --name, dump full system_prompt")
    console.print("  --show-secrets            Do not mask api_key values")
    console.print("\n[bold]Sort order:[/bold]")
    console.print("  source -> kind -> provider -> model -> name")
    console.print('\n[bold]JSON schema (schema_version: "1"):[/bold]')
    console.print("  { schema_version, modes: [")
    console.print("    { name, source, providers, model, kind, description,")
    console.print("      overrides, warnings, raw } ] }")
    console.print("\n[bold]Kind vs. --async flag:[/bold]")
    console.print("  The Kind column describes the mode's default submit style.")
    console.print("  The per-invocation `thoth --async` flag is orthogonal - it")
    console.print("  controls whether the CLI waits for results, not how the job")
    console.print("  is submitted.")
    console.print("\n[bold]Examples:[/bold]")
    console.print("  $ thoth modes")
    console.print(
        "  $ thoth modes --json | jq '.modes[] | select(.kind == \"background\") | .name'"
    )
    console.print("  $ thoth modes --name deep_research --full")


def show_general_help(ctx):
    """Show enhanced general help with command overview"""
    console.print("\n[bold]Thoth - AI-Powered Research Assistant[/bold]")
    console.print(f"Version {THOTH_VERSION}")
    console.print("\n[bold]Usage:[/bold]")
    console.print("  thoth [COMMAND] [OPTIONS]")
    console.print('  thoth [MODE] "PROMPT" [OPTIONS]')
    console.print('  thoth "PROMPT" [OPTIONS]')
    console.print("\n[bold]Quick Start:[/bold]")
    console.print("  # Simple prompt (uses default mode)")
    console.print('  $ thoth "how does DNS work"')
    console.print("\n  # Specify a research mode")
    console.print('  $ thoth deep_research "explain kubernetes networking"')
    console.print("\n[bold]Commands:[/bold]")
    console.print("  init            Initialize configuration")
    console.print("  status <ID>     Check operation status")
    console.print("  list            List research operations")
    console.print("  config <OP>     Inspect and edit configuration")
    console.print("  help [COMMAND]  Show help (general or command-specific)")
    console.print("\n[bold]Research Modes:[/bold]")
    console.print(f"  {', '.join(BUILTIN_MODES.keys())}")
    console.print("  Run [bold]thoth modes[/bold] for provider, model, and kind per mode.")
    console.print("\n[bold]Common Options:[/bold]")
    console.print("  --mode, -m      Research mode to use")
    console.print("  --prompt, -q     Research prompt")
    console.print("  --async, -A     Submit and exit immediately")
    console.print("  --project, -p   Project name for organized output")
    console.print("  --verbose, -v   Show debug output")
    console.print("  --version, -V   Show version and exit")
    console.print("\n[bold]For detailed command help:[/bold]")
    console.print("  $ thoth help init")
    console.print("  $ thoth help status")
    console.print("  $ thoth help list")
    console.print("\n[bold]For all options:[/bold]")
    console.print("  $ thoth --help")


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
    console.print(render_auth_help())


__all__ = [
    "ThothCommand",
    "build_epilog",
    "render_auth_help",
    "show_auth_help",
    "show_config_help",
    "show_general_help",
    "show_init_help",
    "show_list_help",
    "show_modes_help",
    "show_providers_help",
    "show_status_help",
]
