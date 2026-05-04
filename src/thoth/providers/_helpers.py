"""Shared helpers for thoth provider implementations.

Functions here are used by multiple provider modules
(openai.py, perplexity.py, gemini.py). Keeping them in one
place makes cross-provider behavior easier to audit and avoids
copy-paste drift.
"""

from __future__ import annotations

import re

from thoth.errors import ThothError

_UNSUPPORTED_PARAM_RE = re.compile(r"'(\w+)'")


def _extract_unsupported_param(message: str) -> str | None:
    """Extract the offending parameter name from an "unsupported parameter X" error.

    Used by provider error mappers when an OpenAI SDK BadRequestError surfaces
    a message of the form "Unsupported parameter 'X' ...". Returns None when
    the message doesn't match the unsupported-parameter shape.

    Both OpenAI and Perplexity use the OpenAI SDK exception body, which is
    why they share this extractor. Gemini uses google-genai's ClientError
    body shape and may need its own extractor.
    """
    if "unsupported parameter" not in message.lower():
        return None
    match = _UNSUPPORTED_PARAM_RE.search(message)
    return match.group(1) if match else None


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
