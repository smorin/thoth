"""Layered configuration for Thoth.

Precedence (lowest → highest): defaults → user TOML → project TOML → env → CLI.

- ConfigSchema.get_defaults(): canonical default dict
- ConfigManager: loads + merges layers and exposes dot-notation `.get()`
- get_config(): returns a fully-loaded ConfigManager (respecting _config_path override)
- BUILTIN_MODES: baked-in mode presets merged with `[modes.*]` TOML tables
- Mode dicts may optionally carry `async: bool` to override the default
  background/immediate derivation from the model name (see is_background_mode)
- THOTH_VERSION / CONFIG_VERSION: version constants
- _config_path: process-wide override path, set by the CLI `--config` option
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from rich.console import Console

from thoth import __version__
from thoth.errors import ThothError
from thoth.paths import user_checkpoints_dir, user_config_file

# Console used for config-warning output only.
# Distinct from the CLI's main console instance; both write to the same stdout.
_console = Console()

# Version tracking
THOTH_VERSION = __version__
CONFIG_VERSION = "2.0"

# Process-wide config path override. Set by the CLI `--config` option.
_config_path: Path | None = None


# Built-in mode definitions
BUILTIN_MODES = {
    "default": {
        "provider": "openai",
        "model": "o3",  # Use standard o3 for default
        "system_prompt": None,  # No system prompt - pass prompt directly
        "description": "Default mode - passes prompt directly to LLM without any system prompt",
        "auto_input": False,
    },
    "clarification": {
        "provider": "openai",
        "model": "o3",  # Use standard o3 for clarification
        "system_prompt": """I don't want you to follow the above question and instructions; I want you to tell me the ways this is unclear, point out any ambiguities or anything you don't understand. Follow that by asking questions to help clarify the ambiguous points. Once there are no more unclear, ambiguous or not understood portions, help me draft a clear version of the question/instruction.""",
        "description": "Clarifying takes the prompt to get. Ask clarifying questions to get rid of anything that's ambiguous, unclear, and also make suggestions on what would be a better question.",
        "next": "exploration",
    },
    "mini_research": {  # NEW MODE for quick research
        "provider": "openai",
        "model": "o4-mini-deep-research",
        "system_prompt": "Conduct quick, focused research with key findings and essential information. Be concise but thorough.",
        "description": "Fast, lightweight research mode for quick answers using o4-mini-deep-research.",
        "auto_input": False,
    },
    "exploration": {
        "provider": "openai",
        "model": "o3-deep-research",  # Use deep research for exploration
        "system_prompt": "Explore the topic at hand, looking at options, alternatives, different trade-offs, and make recommendations based on the use case or alternative/related technologies.",
        "description": "Exploration looks at the topic at hand and explores some options and alternatives, different trade-offs, and makes recommendations based on the use case or just alternative and related technologies.",
        "previous": "clarification",
        "next": "deep_dive",
    },
    "deep_dive": {
        "provider": "openai",
        "model": "o3-deep-research",  # Use deep research for deep dive
        "system_prompt": "Deep dive into the specific technology, giving an overview, going deep on it, discussing it, and exploring it. For APIs, cover what the API is, how it works, assumptions, dependencies, if it's deprecated, common pitfalls. For other technologies, cover what the technology is and how it's used.",
        "description": "This deep dives into a specific technology, giving an overview of it, going deep on it, discussing it, and exploring it.",
        "previous": "exploration",
        "next": "tutorial",
    },
    "tutorial": {
        "provider": "openai",
        "model": "o3-deep-research",  # Use deep research for tutorial
        "system_prompt": "Create a detailed tutorial with examples of how the technologies are used in common scenarios to get started, along with code samples, command-line execution process, and other useful information.",
        "description": "The tutorial goes into a detailed explanation with examples of how the technologies are used in common scenarios to get started.",
        "previous": "deep_dive",
        "next": "solution",
    },
    "solution": {
        "provider": "openai",
        "model": "o3-deep-research",  # Use deep research for solution
        "system_prompt": "Design a specific solution to solve the given problem using appropriate technology. Focus on practical implementation.",
        "description": "A solution generally goes into a specific solution to solve a specific problem using technology.",
        "previous": "tutorial",
        "next": "prd",
    },
    "prd": {
        "provider": "openai",
        "model": "o3-deep-research",  # Use deep research for PRD
        "system_prompt": "Create a Product Requirements Document based on prior research. Use previous research on solutions and technologies to create a comprehensive requirements document.",
        "description": "Product Requirements Document based on prior research, we'll create the PRD looking at previous research on solutions to technologies.",
        "previous": "solution",
        "next": "tdd",
    },
    "tdd": {
        "provider": "openai",
        "model": "o3-deep-research",  # Use deep research for TDD
        "system_prompt": "Create a Technical Design Document based on the PRD and prior research. Consider best practices on architecture and good abstractions to make things maintainable and well-structured in code.",
        "description": "The Technical Design Document based on the PRD and prior research puts together a technical design document.",
        "previous": "prd",
    },
    "thinking": {
        "provider": "openai",
        "model": "o3",
        "temperature": 0.4,
        "system_prompt": "You are a helpful assistant for quick analysis.",
        "description": "Quick thinking and analysis mode for simple questions.",
    },
    "deep_research": {
        "provider": "openai",
        "model": "o3-deep-research",  # Explicit deep research model
        "providers": ["openai"],
        "parallel": True,
        "system_prompt": "Conduct comprehensive research with citations and multiple perspectives.\nOrganize findings clearly and highlight key insights.",
        "description": "Deep research mode using OpenAI for comprehensive analysis.",
        "previous": "exploration",
        "auto_input": True,
    },
    "comparison": {  # Add comparison mode with deep research
        "provider": "openai",
        "model": "o3-deep-research",
        "system_prompt": "Compare and contrast the given options, technologies, or approaches. Provide a detailed analysis of pros, cons, and recommendations.",
        "description": "Comparative analysis mode for evaluating multiple options.",
    },
}


def is_background_mode(mode_config: dict[str, Any]) -> bool:
    """Return True if a mode submits as a long-running background job.

    Precedence: explicit `async` key wins; otherwise derive from model name
    (any model containing "deep-research" is a background/long-running model).
    """
    if "async" in mode_config:
        return bool(mode_config["async"])
    model = mode_config.get("model") or ""
    return "deep-research" in model


class ConfigSchema:
    """Configuration schema and defaults"""

    @staticmethod
    def get_defaults() -> dict[str, Any]:
        """Return default configuration"""
        return {
            "version": CONFIG_VERSION,
            "general": {
                "default_project": "",  # Empty means ad-hoc mode
                "default_mode": "default",
            },
            "paths": {
                "base_output_dir": "./research-outputs",
                "checkpoint_dir": str(user_checkpoints_dir()),
            },
            "execution": {
                "poll_interval": 30,
                "max_wait": 30,
                "parallel_providers": True,
                "retry_attempts": 3,
                "max_transient_errors": 5,
                "auto_input": True,
            },
            "output": {
                "combine_reports": False,
                "format": "markdown",
                "include_metadata": True,
                "timestamp_format": "%Y-%m-%d_%H%M%S",
            },
            "providers": {
                "openai": {"api_key": "${OPENAI_API_KEY}"},
                "perplexity": {"api_key": "${PERPLEXITY_API_KEY}"},
            },
            "clarification": {
                "cli": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "temperature": 0.7,
                    "max_tokens": 500,
                    "system_prompt": """I don't want you to follow the above question and instructions; I want you to tell me the ways this is unclear, point out any ambiguities or anything you don't understand. Follow that by asking questions to help clarify the ambiguous points. Once there are no more unclear, ambiguous or not understood portions, help me draft a clear version of the question/instruction.""",
                    "retry_attempts": 3,
                    "retry_delay": 2.0,
                },
                "interactive": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "temperature": 0.7,
                    "max_tokens": 800,
                    "system_prompt": """I don't want you to follow the above question and instructions; I want you to tell me the ways this is unclear, point out any ambiguities or anything you don't understand. Follow that by asking questions to help clarify the ambiguous points. Once there are no more unclear, ambiguous or not understood portions, help me draft a clear version of the question/instruction.""",
                    "retry_attempts": 3,
                    "retry_delay": 2.0,
                    "input_height": 6,
                    "max_input_height": 15,
                },
            },
            "modes": {},  # Modes will be merged with built-in modes
        }


class ConfigManager:
    """Manages layered configuration with clear precedence hierarchy"""

    def __init__(self, config_path: Path | None = None):
        self.user_config_path = config_path or user_config_file()
        self.project_config_paths = ["./thoth.toml", "./.thoth/config.toml"]
        self.layers = {}
        self.data = {}

    def load_all_layers(self, cli_args: dict[str, Any] | None = None):
        """Load all configuration layers in precedence order"""
        # Layer 1: Internal defaults
        self.layers["defaults"] = ConfigSchema.get_defaults()

        # Layer 2: User config file
        if self.user_config_path.exists():
            self.layers["user"] = self._load_toml_file(self.user_config_path)
        else:
            self.layers["user"] = {}

        # Layer 3: Project config file (if exists)
        self.layers["project"] = self._load_project_config()

        # Layer 4: Environment variables
        self.layers["env"] = self._get_env_overrides()

        # Layer 5: CLI arguments
        self.layers["cli"] = cli_args or {}

        # Merge all layers
        self.data = self._merge_layers()
        self.data = self._substitute_env_vars(self.data)

        # Validate configuration
        self._validate_config()

    def _load_toml_file(self, path: Path) -> dict[str, Any]:
        """Load and parse a TOML configuration file"""
        try:
            with open(path, "rb") as f:
                config = tomllib.load(f)

            # Check version compatibility
            config_version = config.get("version", "0.0")
            if config_version != CONFIG_VERSION:
                _console.print(f"[yellow]Warning:[/yellow] Config version mismatch in {path}")

            # Expand paths and substitute env vars
            config = self._expand_paths(config)
            config = self._substitute_env_vars(config)

            return config
        except Exception as e:
            _console.print(f"[yellow]Warning:[/yellow] Failed to load {path}: {e}")
            return {}

    def _load_project_config(self) -> dict[str, Any]:
        """Load project-level configuration if it exists"""
        for config_path in self.project_config_paths:
            path = Path(config_path)
            if path.exists():
                return self._load_toml_file(path)
        return {}

    def _get_env_overrides(self) -> dict[str, Any]:
        """Get configuration overrides from environment variables"""
        overrides = {}

        # Map of env vars to config paths
        env_mappings = {
            "THOTH_DEFAULT_MODE": "general.default_mode",
            "THOTH_DEFAULT_PROJECT": "general.default_project",
            "THOTH_OUTPUT_DIR": "paths.base_output_dir",
            "THOTH_POLL_INTERVAL": "execution.poll_interval",
            "THOTH_MAX_WAIT": "execution.max_wait",
        }

        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert config path to nested dict
                keys = config_path.split(".")
                current = overrides
                for key in keys[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]

                # Try to convert to appropriate type
                try:
                    if value.lower() in ("true", "false"):
                        current[keys[-1]] = value.lower() == "true"
                    elif value.isdigit():
                        current[keys[-1]] = int(value)
                    else:
                        current[keys[-1]] = value
                except Exception:
                    current[keys[-1]] = value

        return overrides

    def _merge_layers(self) -> dict[str, Any]:
        """Merge all configuration layers with proper precedence"""
        result = {}

        # Merge in order of precedence
        for layer_name in ["defaults", "user", "project", "env", "cli"]:
            if layer_name in self.layers and self.layers[layer_name]:
                result = self._deep_merge(result, self.layers[layer_name])

        return result

    def _deep_merge(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Deep merge two dictionaries"""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _expand_paths(self, config: dict[str, Any]) -> dict[str, Any]:
        """Expand paths in configuration"""
        if "paths" in config:
            for key, value in config["paths"].items():
                path = Path(value).expanduser()
                if path.exists() and path.is_symlink():
                    path = path.resolve()
                config["paths"][key] = str(path)
        return config

    def _substitute_env_vars(self, config: dict[str, Any]) -> dict[str, Any]:
        """Replace ${VAR} with environment variable values"""

        def substitute(value):
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                var_name = value[2:-1]
                return os.getenv(var_name, value)
            elif isinstance(value, dict):
                return {k: substitute(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [substitute(v) for v in value]
            return value

        return substitute(config)

    def _validate_config(self):
        """Validate the merged configuration"""
        # Basic validation - can be extended
        required_keys = [
            "version",
            "general",
            "paths",
            "execution",
            "output",
            "providers",
        ]
        for key in required_keys:
            if key not in self.data:
                raise ThothError(
                    f"Missing required configuration key: {key}",
                    "Check your configuration file",
                )

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation"""
        keys = key.split(".")
        current = self.data

        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default

        return current

    def get_mode_config(self, mode: str) -> dict[str, Any]:
        """Get mode configuration, merging built-in with user config"""
        # Start with built-in mode if it exists
        mode_config = BUILTIN_MODES.get(mode, {}).copy()

        # Override with user config if present
        user_mode = self.data.get("modes", {}).get(mode, {})
        mode_config.update(user_mode)

        return mode_config

    def get_effective_config(self) -> dict[str, Any]:
        """Return the merged effective configuration"""
        return self.data


def get_config() -> ConfigManager:
    """Get a fully-loaded ConfigManager instance with custom path if provided"""
    manager = ConfigManager(_config_path) if _config_path else ConfigManager()
    manager.load_all_layers()
    return manager
