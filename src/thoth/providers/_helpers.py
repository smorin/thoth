"""Shared helpers for thoth provider implementations.

Functions here are used by multiple provider modules
(openai.py, perplexity.py, gemini.py). Keeping them in one
place makes cross-provider behavior easier to audit and avoids
copy-paste drift.
"""

from __future__ import annotations

from thoth.errors import ThothError


def _invalid_key_thotherror(display_name: str, settings_url: str) -> ThothError:
    """Friendly ThothError for an upstream-rejected API key.

    Distinct from APIKeyError (which signals 'no key found'); this one
    signals 'a key was supplied but the upstream rejected it'. Different
    user actions (rotate vs. set), different exit_code semantics
    (exit_code=2 for invalid-vs-missing distinction).

    Called by every immediate-call provider's error mapper to keep the
    wording byte-identical across provider error-mapping paths.

    `display_name` is the brand-correct, user-facing name (e.g. "OpenAI",
    "Perplexity") and is used verbatim in both message and suggestion;
    callers must capitalize correctly rather than passing a lookup-key.
    """
    return ThothError(
        f"{display_name} API key is invalid",
        f"Your {display_name} API key was rejected by the API. Check your key at {settings_url}",
        exit_code=2,
    )
