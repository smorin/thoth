"""Custom exception classes for Thoth.

Each exception carries a structured `message` + `suggestion` + `exit_code`
so `handle_error` can render a consistent CLI error banner. Exit codes:

  1  - generic ThothError / KeyboardInterrupt fallback
  2  - APIKeyError (missing/invalid API key)
  3  - ProviderError (upstream provider failure)
  8  - DiskSpaceError
  9  - APIQuotaError
  127 - uncaught unexpected exception (handled in handle_error)
"""

from __future__ import annotations

import os
from pathlib import Path


def format_config_context(config_path: Path | str, env_vars: list[str] | None = None) -> str:
    """Return a multi-line "Resolved from:" block for error bodies.

    Shows the config file path + whether it exists, and optional env vars
    + whether each is set. Used by APIKeyError so users can see what the
    tool consulted when resolving credentials.
    """
    p = Path(config_path)
    lines = [f"  Config file: {p}  ({'exists' if p.exists() else 'does not exist'})"]
    if env_vars:
        parts = [f"{name} ({'set' if os.environ.get(name) else 'unset'})" for name in env_vars]
        lines.append(f"  Env checked: {', '.join(parts)}")
    return "\n".join(lines)


class ThothError(Exception):
    """Base exception for Thoth errors"""

    def __init__(self, message: str, suggestion: str | None = None, exit_code: int = 1):
        self.message = message
        self.suggestion = suggestion
        self.exit_code = exit_code
        super().__init__(message)


class APIKeyError(ThothError):
    """Missing or invalid API key"""

    def __init__(self, provider: str):
        from thoth.paths import user_config_file  # local import to avoid cycles

        env_var = f"{provider.upper()}_API_KEY"
        cfg_path = user_config_file()
        suggestion = f"Set {env_var} (or edit {cfg_path})\n" + format_config_context(
            cfg_path, env_vars=[env_var]
        )
        super().__init__(
            f"{provider} API key not found",
            suggestion,
            exit_code=2,
        )


class ProviderError(ThothError):
    """Provider-specific error with raw error support"""

    def __init__(self, provider: str, message: str, raw_error: str | None = None):
        self.provider = provider
        self.raw_error = raw_error
        super().__init__(
            f"{provider} error: {message}",
            "Check API status or try again later",
            exit_code=3,
        )


class DiskSpaceError(ThothError):
    """Insufficient disk space"""

    def __init__(self, message: str):
        super().__init__(message, "Free up disk space and try again", exit_code=8)


class APIQuotaError(ThothError):
    """API quota exceeded"""

    def __init__(self, provider: str):
        super().__init__(
            f"{provider} API quota exceeded",
            "Wait for quota reset or upgrade your plan",
            exit_code=9,
        )


class ModeKindMismatchError(ThothError):
    """A mode's declared `kind` is incompatible with its model's required kind.

    Raised by `OpenAIProvider._validate_kind_for_model` BEFORE any HTTP call,
    so the user sees a config-edit suggestion instead of a confusing API
    error mid-run. See spec §5.6 + §4 Q1.

    Attributes (for programmatic access):
      * mode_name      — the mode whose `kind` is wrong
      * model          — the model the mode is configured to use
      * declared_kind  — what the mode says (e.g., "immediate")
      * required_kind  — what the model actually requires (e.g., "background")
    """

    def __init__(
        self,
        mode_name: str,
        model: str,
        declared_kind: str,
        required_kind: str,
    ):
        self.mode_name = mode_name
        self.model = model
        self.declared_kind = declared_kind
        self.required_kind = required_kind
        super().__init__(
            (
                f"Mode '{mode_name}' is declared as kind='{declared_kind}', "
                f"but model '{model}' requires kind='{required_kind}'."
            ),
            (
                f"Update [modes.{mode_name}] in your config: set "  # nosec B608 — TOML config-edit suggestion, not SQL
                f"kind = '{required_kind}', or pick a model compatible with "
                f"'{declared_kind}' execution. Run `thoth modes list` to see "
                f"current kinds."
            ),
            exit_code=1,
        )
