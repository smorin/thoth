"""Shared helpers for thoth provider implementations.

Functions here are used by multiple provider modules
(openai.py, perplexity.py, gemini.py). Keeping them in one
place makes cross-provider behavior easier to audit and avoids
copy-paste drift.
"""

from __future__ import annotations

from thoth.errors import ThothError


def _invalid_key_thotherror(provider: str, settings_url: str) -> ThothError:
    """Friendly ThothError for an upstream-rejected API key.

    Distinct from APIKeyError (which signals 'no key found'); this one
    signals 'a key was supplied but the upstream rejected it'. Different
    user actions (rotate vs. set), different exit_code semantics
    (exit_code=2 for invalid-vs-missing distinction).

    Called by every immediate-call provider's error mapper to keep the
    wording byte-identical across provider error-mapping paths.
    """
    return ThothError(
        f"{provider} API key is invalid",
        f"Your {provider.title()} API key was rejected by the API. "
        f"Check your key at {settings_url}",
        exit_code=2,
    )
