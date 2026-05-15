"""Shared helpers for doxa_research provider implementations.

Functions here are used by multiple provider modules
(openai.py, perplexity.py, gemini.py). Keeping them in one
place makes cross-provider behavior easier to audit and avoids
copy-paste drift.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterable
from typing import Any

from rich.console import Console

from doxa_research.errors import DoxaError
from doxa_research.providers.base import Citation
from doxa_research.utils import md_link_title, md_link_url

_UNSUPPORTED_PARAM_RE = re.compile(r"'(\w+)'")
_DEBUG_INFO_LIMIT = 1000


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


def _invalid_key_doxaerror(display_name: str, settings_url: str) -> DoxaError:
    """Friendly DoxaError for an upstream-rejected API key.

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
    return DoxaError(
        f"{display_name} API key is invalid",
        f"Your {display_name} API key was rejected by the API. Check your key at {settings_url}",
        exit_code=2,
    )


def render_sources_block(citations: Iterable[Citation]) -> str:
    """Render a deduped Markdown sources block from normalized citations.

    Deduplication is URL-first and stable: the first title observed for a URL
    is the one rendered. Provider modules remain responsible for extracting
    provider-specific response shapes into `Citation` objects.
    """
    seen_urls: set[str] = set()
    source_lines: list[str] = []
    for citation in citations:
        url = str(citation.url or "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        title = str(citation.title or url)
        source_lines.append(f"- [{md_link_title(title)}]({md_link_url(url)})")
    if not source_lines:
        return ""
    return "## Sources\n\n" + "\n".join(source_lines)


def debug_print_empty_response(response: Any, provider_label: str) -> None:
    """Emit a consistent verbose empty-response debug line to stderr."""
    err_console = Console(file=sys.stderr)
    try:
        if hasattr(response, "model_dump_json"):
            debug_info = str(response.model_dump_json())
        elif hasattr(response, "__dict__"):
            debug_info = str(
                {k: str(v)[:100] for k, v in response.__dict__.items() if not k.startswith("_")}
            )
        else:
            debug_info = repr(response)
    except Exception:
        debug_info = f"<{type(response).__name__}>"

    if len(debug_info) > _DEBUG_INFO_LIMIT:
        debug_info = debug_info[:_DEBUG_INFO_LIMIT] + "... [truncated]"

    err_console.print(
        f"[dim]Debug: {provider_label} response had no content. Structure: {debug_info}[/dim]"
    )
