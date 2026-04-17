"""Command implementations for the Thoth CLI.

`CommandHandler` is the dispatch facade that ``cli.py`` and the interactive
mode both use. The async functions ``show_status``, ``list_operations``, and
``providers_command`` are the long-form implementations the dispatcher calls
into. Thin sync wrappers ``status_command`` / ``list_command`` exist for
back-compat with older callers.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from platformdirs import user_config_dir
from rich import box
from rich.console import Console
from rich.table import Table

from thoth.checkpoint import CheckpointManager
from thoth.config import CONFIG_VERSION, ConfigManager, get_config
from thoth.errors import APIKeyError, ThothError
from thoth.help import (
    show_init_help,
    show_list_help,
    show_providers_help,
    show_status_help,
)
from thoth.models import ModelCache
from thoth.providers import create_provider
from thoth.run import run_research

console = Console()


class CommandHandler:
    """Unified command execution for CLI and interactive modes"""

    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.commands = {
            "init": self.init_command,
            "status": self.status_command,
            "list": self.list_command,
            "providers": self.providers_command,
            "research": self.research_command,
            "help": self.help_command,
        }

    def execute(self, command: str, **params) -> Any:
        """Execute command with parameters"""
        if command not in self.commands:
            raise ThothError(
                f"Unknown command: {command}",
                f"Available commands: {', '.join(self.commands.keys())}",
            )
        return self.commands[command](**params)

    def init_command(self, config_path: Path | None = None, **params):
        """Initialize Thoth configuration"""
        console.print("[bold]Welcome to Thoth Research Assistant Setup![/bold]\n")

        console.print("Checking environment...")
        console.print(f"✓ Python {sys.version.split()[0]} detected")
        console.print("✓ UV package manager available")
        console.print(f"✓ Operating System: {sys.platform} (supported)\n")

        if config_path is None:
            config_path = Path(user_config_dir("thoth")) / "config.toml"
        console.print(f"Configuration file will be created at: {config_path}\n")

        config_path.parent.mkdir(parents=True, exist_ok=True)

        console.print("[yellow]Interactive setup wizard not yet implemented.[/yellow]")
        console.print("Creating default configuration...")

        config_manager = ConfigManager()
        config_manager.load_all_layers()
        config_data = config_manager.get_effective_config()

        with open(config_path, "w") as f:
            f.write("# Thoth Configuration File\n")
            f.write(f'version = "{CONFIG_VERSION}"\n\n')
            f.write("[general]\n")
            f.write('default_project = ""\n')
            f.write('default_mode = "default"\n\n')
            f.write("[paths]\n")
            f.write('base_output_dir = "./research-outputs"\n')
            f.write(f'checkpoint_dir = "{config_data["paths"]["checkpoint_dir"]}"\n\n')
            f.write("[execution]\n")
            f.write("poll_interval = 30\n")
            f.write("max_wait = 30\n")
            f.write("parallel_providers = true\n")
            f.write("retry_attempts = 3\n")
            f.write("auto_input = true\n\n")
            f.write("[output]\n")
            f.write("combine_reports = false\n")
            f.write('format = "markdown"\n')
            f.write("include_metadata = true\n")
            f.write('timestamp_format = "%Y-%m-%d_%H%M%S"\n\n')
            f.write("[providers.openai]\n")
            f.write('api_key = "${OPENAI_API_KEY}"\n\n')
            f.write("[providers.perplexity]\n")
            f.write('api_key = "${PERPLEXITY_API_KEY}"\n')

        console.print(f"\n[green]✓[/green] Configuration saved to {config_path}")
        console.print('\nYou can now run: thoth deep_research "your prompt"')

    def status_command(self, operation_id: str, **params):
        """Check status of a research operation"""
        return asyncio.run(show_status(operation_id))

    def list_command(self, show_all: bool = False, **params):
        """List research operations"""
        return asyncio.run(list_operations(show_all=show_all))

    def providers_command(self, **params):
        """Show provider information - delegate to existing function"""
        return asyncio.run(providers_command(**params))

    def research_command(self, **params):
        """Execute research operation - delegate to run_research"""
        mode = params.get("mode", "default")
        prompt = params.get("prompt")
        if not prompt:
            raise ThothError("Prompt is required for research command")

        return asyncio.run(
            run_research(
                mode=mode,
                prompt=prompt,
                async_mode=params.get("async_mode", False),
                project=params.get("project"),
                output_dir=params.get("output_dir"),
                provider=params.get("provider"),
                input_file=params.get("input_file"),
                auto=params.get("auto", False),
                verbose=params.get("verbose", False),
                cli_api_keys=params.get("cli_api_keys"),
                combined=params.get("combined", False),
                quiet=params.get("quiet", False),
                no_metadata=params.get("no_metadata", False),
                timeout_override=params.get("timeout_override"),
            )
        )

    def help_command(self, command: str | None = None, **params):
        """Show help for commands"""
        if command == "init":
            show_init_help()
        elif command == "status":
            show_status_help()
        elif command == "list":
            show_list_help()
        elif command == "providers":
            show_providers_help()
        else:
            console.print("Thoth - AI-Powered Research Assistant")
            console.print("\nAvailable commands:")
            for cmd_name in self.commands.keys():
                console.print(f"  {cmd_name}")


def status_command(operation_id):
    """Check status of a research operation"""
    return show_status(operation_id)


def list_command(show_all):
    """List research operations"""
    return list_operations(show_all=show_all)


async def show_status(operation_id: str):
    """Show status of a specific operation"""
    config = get_config()
    checkpoint_manager = CheckpointManager(config)

    operation = await checkpoint_manager.load(operation_id)
    if not operation:
        console.print(f"[red]Error:[/red] Operation {operation_id} not found")
        sys.exit(6)

    console.print("\nOperation Details:")
    console.print("─────────────────")
    console.print(f"ID:        {operation.id}")
    console.print(f"Prompt:    {operation.prompt}")
    console.print(f"Mode:      {operation.mode}")
    console.print(f"Status:    {operation.status}")
    console.print(f"Started:   {operation.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

    if operation.status in ["running", "completed"]:
        elapsed = datetime.now() - operation.created_at
        minutes = int(elapsed.total_seconds() / 60)
        console.print(f"Elapsed:   {minutes} minutes")

    if operation.project:
        console.print(f"Project:   {operation.project}")

    if operation.providers:
        console.print("\nProvider Status:")
        console.print("───────────────")
        for provider_name, provider_info in operation.providers.items():
            status_icon = "✓" if provider_info.get("status") == "completed" else "▶"
            status_text = provider_info.get("status", "unknown").title()
            console.print(f"{provider_name.title()}:  {status_icon} {status_text}")

    if operation.output_paths:
        console.print("\nOutput Files:")
        console.print("────────────")
        if operation.project:
            base_dir = Path(config.data["paths"]["base_output_dir"]) / operation.project
            console.print(f"{base_dir}/")
        else:
            console.print("./")

        for provider_name, path in operation.output_paths.items():
            console.print(f"  ├── {Path(path).name}")


async def list_operations(show_all: bool):
    """List all operations"""
    config = get_config()
    checkpoint_manager = CheckpointManager(config)

    checkpoint_files = list(checkpoint_manager.checkpoint_dir.glob("*.json"))

    if not checkpoint_files:
        console.print("No operations found.")
        return

    operations = []
    for checkpoint_file in checkpoint_files:
        operation_id = checkpoint_file.stem
        operation = await checkpoint_manager.load(operation_id)
        if operation:
            operations.append(operation)

    operations.sort(key=lambda op: op.created_at, reverse=True)

    if not show_all:
        cutoff_time = datetime.now() - timedelta(hours=24)
        operations = [
            op
            for op in operations
            if op.status in ["running", "queued"] or op.created_at > cutoff_time
        ]

    if not operations:
        console.print("No active operations found. Use --all to see all operations.")
        return

    table = Table(title="Research Operations")
    table.add_column("ID", style="dim", width=40)
    table.add_column("Prompt", width=25)
    table.add_column("Status", width=10)
    table.add_column("Elapsed", width=8)
    table.add_column("Mode", width=15)

    for operation in operations:
        prompt_display = (
            operation.prompt[:22] + "..." if len(operation.prompt) > 25 else operation.prompt
        )

        elapsed = datetime.now() - operation.created_at
        if elapsed.total_seconds() < 3600:
            elapsed_str = f"{int(elapsed.total_seconds() / 60)}m"
        else:
            elapsed_str = f"{int(elapsed.total_seconds() / 3600)}h"

        status_style = (
            "green"
            if operation.status == "completed"
            else "yellow"
            if operation.status == "running"
            else "dim"
        )

        table.add_row(
            operation.id,
            prompt_display,
            f"[{status_style}]{operation.status}[/{status_style}]",
            elapsed_str,
            operation.mode,
        )

    console.print(table)
    console.print("\nUse 'thoth status <ID>' for details")


async def providers_command(
    show_models: bool = False,
    show_list: bool = False,
    show_keys: bool = False,
    filter_provider: str | None = None,
    refresh_cache: bool = False,
    no_cache: bool = False,
):
    """Show provider information and available models"""
    if not show_models and not show_list and not show_keys:
        console.print("[yellow]Usage:[/yellow] thoth providers -- [OPTIONS]")
        console.print("\nShow provider information and available models.")
        console.print("\nOptions:")
        console.print("  --list                List available providers and their status")
        console.print("  --models              List available models from providers")
        console.print("  --keys                Show API key configuration for each provider")
        console.print("  --provider, -P        Filter by specific provider (with --models)")
        console.print("  --refresh-cache       Force refresh of cached model lists")
        console.print("  --no-cache            Bypass cache without updating it")
        console.print("\n[dim]Note: Use -- before options to prevent parsing conflicts[/dim]")
        console.print("\nExamples:")
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
        console.print("\n  # Check current models without updating cache")
        console.print("  $ thoth providers -- --models --no-cache")
        return

    config = get_config()

    all_providers = ["openai", "perplexity", "mock"]

    provider_descriptions = {
        "openai": "OpenAI GPT models",
        "perplexity": "Perplexity search AI (not implemented)",
        "mock": "Mock provider for tests",
    }

    if show_list:
        table = Table(title="Available Providers", box=box.ROUNDED)
        table.add_column("Provider", style="cyan", width=13)
        table.add_column("Status", width=10)
        table.add_column("Description", style="dim", width=25)
        table.add_column("Model Cache", style="dim", width=30)

        for provider_name in all_providers:
            try:
                provider = create_provider(provider_name, config)
                status = "[green]✓ Ready[/green]"

                cache_info = "N/A"
                if not provider.is_implemented():
                    status = (
                        f"[yellow]⚠ {provider.implementation_status() or 'Unavailable'}[/yellow]"
                    )
                elif provider_name == "openai":
                    cache = ModelCache(provider_name)
                    age = cache.get_cache_age()
                    if age:
                        days = age.days
                        if days == 0:
                            cache_info = "Cached today"
                        elif days == 1:
                            cache_info = "1 day old"
                        else:
                            refresh_in = 7 - days
                            if refresh_in > 0:
                                cache_info = f"{days} days old (refresh in {refresh_in} days)"
                            else:
                                cache_info = f"{days} days old (needs refresh)"
                    else:
                        cache_info = "Not cached"

            except APIKeyError:
                status = "[red]✗ No key[/red]"
                cache_info = "N/A"
            except Exception:
                status = "[yellow]⚠ Error[/yellow]"
                cache_info = "N/A"

            description = provider_descriptions.get(provider_name, "Unknown provider")
            table.add_row(provider_name, status, description, cache_info)

        console.print(table)
        console.print("\nTo see available models, use: thoth providers -- --models")
        console.print("To refresh model cache, use: thoth providers -- --models --refresh-cache")
        return

    if show_keys:
        env_vars = {
            "openai": "OPENAI_API_KEY",
            "perplexity": "PERPLEXITY_API_KEY",
            "mock": "MOCK_API_KEY",
        }

        table = Table(title="Provider API Key Configuration", box=box.ROUNDED)
        table.add_column("Provider", style="cyan", width=13)
        table.add_column("Environment Variable", style="green", width=22)
        table.add_column("CLI Argument", style="yellow", width=22)

        for provider_name in all_providers:
            env_var = env_vars.get(provider_name, f"{provider_name.upper()}_API_KEY")
            cli_arg = f"--api-key-{provider_name}"
            table.add_row(provider_name, env_var, cli_arg)

        console.print(table)
        console.print("\nExamples:")
        console.print("  # Set via environment variable")
        console.print('  $ export OPENAI_API_KEY="your-key-here"')
        console.print("\n  # Set via command line for single provider")
        console.print('  $ thoth "prompt" --api-key-openai "your-key-here" --provider openai')
        console.print("\n  # Set multiple API keys for multi-provider modes")
        console.print(
            '  $ thoth deep_research "prompt" --api-key-openai "sk-..." --api-key-perplexity "pplx-..."'
        )
        return

    providers = all_providers
    if filter_provider:
        if filter_provider not in providers:
            print(f"Error: Unknown provider: {filter_provider}", file=sys.stderr)
            print(f"Available providers: {', '.join(providers)}", file=sys.stderr)
            sys.exit(1)
        providers = [filter_provider]

    if refresh_cache:
        console.print("Fetching available models (refreshing cache)...\n")
    else:
        console.print("Fetching available models...\n")

    for provider_name in providers:
        try:
            provider = create_provider(provider_name, config)

            if hasattr(provider, "list_models_cached"):
                models = await provider.list_models_cached(
                    force_refresh=refresh_cache, no_cache=no_cache
                )
            else:
                models = await provider.list_models()

            if models:
                max_model_id_length = max(len(model.get("id", "")) for model in models)
                model_id_width = max(max_model_id_length + 2, 20)
            else:
                model_id_width = 25

            if provider_name == "openai":
                table = Table(title="OpenAI Models", box=box.ROUNDED)
                table.add_column("Model ID", style="cyan", width=model_id_width)
                table.add_column("Created", style="green", width=14)
                table.add_column("Owned By", style="yellow", width=16)

                for model in models:
                    created_date = datetime.fromtimestamp(model["created"]).strftime("%Y-%m-%d")
                    table.add_row(model["id"], created_date, model["owned_by"])
            elif provider_name == "perplexity":
                table = Table(title="Perplexity Models", box=box.ROUNDED)
                table.add_column("Model ID", style="cyan", width=model_id_width)

                for model in models:
                    table.add_row(model["id"])
            else:
                table = Table(title="Mock Models", box=box.ROUNDED)
                table.add_column("Model ID", style="cyan", width=model_id_width)

                for model in models:
                    table.add_row(model["id"])

            console.print(table)
            console.print()

        except APIKeyError as e:
            console.print(f"[yellow]Skipping {provider_name}:[/yellow] {e}")
            console.print()
        except Exception as e:
            console.print(f"[red]Error fetching models from {provider_name}:[/red] {str(e)}")
            console.print()


__all__ = [
    "CommandHandler",
    "list_command",
    "list_operations",
    "providers_command",
    "show_status",
    "status_command",
]
