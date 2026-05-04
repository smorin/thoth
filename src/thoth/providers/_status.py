"""Shared status-enum translation for background-lifecycle providers.

Both `OpenAIProvider.check_status` and `PerplexityProvider._poll_async_job`
translate a provider-specific status literal (e.g. `"completed"`,
`"COMPLETED"`, `"in_progress"`) into Thoth's internal status dict
(`{"status": "completed", "progress": 1.0}` etc.). The dispatch shape
is identical across providers; only the table differs.

This helper is the pure-data part of that translation. It does NOT
touch self.jobs caching, exception handling, or any provider-specific
I/O — callers wrap their own error and cache logic around it.

Per the P27 factor-dedup spec; declared in its own module rather than
appended to `base.py` so the ABC doesn't grow lifecycle-specific helpers.
"""

from __future__ import annotations

from typing import Any


def _translate_provider_status(
    provider_status: str,
    status_table: dict[str, dict[str, Any]],
    *,
    unknown_template: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Translate a provider-specific status literal to Thoth's status dict.

    `status_table` maps the provider's own status enum (e.g.,
    `"COMPLETED"`, `"in_progress"`) to a Thoth status template such as
    `{"status": "completed", "progress": 1.0}`. The helper returns a
    fresh dict copy on every call so callers may mutate the result
    (e.g., to add a runtime `progress` from response.metadata or an
    `error` field from the upstream payload) without poisoning the
    table.

    Unknown statuses fall through to `unknown_template` if supplied, or
    to a default `permanent_error` carrying the unrecognized literal.
    Custom unknown_template may use `{status}` in the `error` field as
    a substitution token.
    """
    template = status_table.get(provider_status)
    if template is not None:
        return dict(template)
    if unknown_template is not None:
        result = dict(unknown_template)
        if "error" in result and isinstance(result["error"], str):
            result["error"] = result["error"].format(status=provider_status)
        return result
    return {
        "status": "permanent_error",
        "error": f"Unexpected provider status: {provider_status!r}",
    }
