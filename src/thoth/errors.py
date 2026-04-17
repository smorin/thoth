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
        super().__init__(
            f"{provider} API key not found",
            f"Set {provider.upper()}_API_KEY or run 'thoth init'",
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
