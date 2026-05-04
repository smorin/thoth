"""Tests for _translate_provider_status — the shared status-enum dispatcher.

Used by both OpenAIProvider.check_status and PerplexityProvider._poll_async_job
to translate provider-specific status literals to Thoth's internal status
dict ({status, progress, error?}). Pure data transform; no I/O, no caching.
"""

from __future__ import annotations

from typing import Any

from thoth.providers._status import _translate_provider_status


def test_table_lookup_returns_template_copy() -> None:
    """A known status returns a COPY of the template (caller may mutate freely)."""
    table = {"COMPLETED": {"status": "completed", "progress": 1.0}}
    result = _translate_provider_status("COMPLETED", table)
    assert result == {"status": "completed", "progress": 1.0}
    # Mutating the result must NOT mutate the table entry — caller fills in
    # dynamic fields (error, runtime progress) without poisoning the table.
    result["error"] = "extra"
    assert "error" not in table["COMPLETED"]


def test_unknown_status_returns_default_permanent_error() -> None:
    """An unrecognized status falls through to permanent_error with the literal in the message."""
    table = {"COMPLETED": {"status": "completed", "progress": 1.0}}
    result = _translate_provider_status("WAT", table)
    assert result == {
        "status": "permanent_error",
        "error": "Unexpected provider status: 'WAT'",
    }


def test_empty_status_string_falls_through_to_permanent_error() -> None:
    """An empty string status (defaulted from a missing key) is treated as unknown."""
    table = {"COMPLETED": {"status": "completed", "progress": 1.0}}
    result = _translate_provider_status("", table)
    assert result["status"] == "permanent_error"
    assert "''" in result["error"]


def test_explicit_unknown_template_overrides_default() -> None:
    """Caller may supply a custom unknown_template (e.g., to embed the status differently)."""
    table = {"COMPLETED": {"status": "completed", "progress": 1.0}}
    custom = {"status": "permanent_error", "error": "got status={status}"}
    result = _translate_provider_status("WAT", table, unknown_template=custom)
    assert result == {"status": "permanent_error", "error": "got status=WAT"}


def test_table_with_partial_template_returns_partial_dict() -> None:
    """Templates may omit progress (e.g., for failed states); the helper preserves shape."""
    table: dict[str, dict[str, Any]] = {
        "FAILED": {"status": "permanent_error"},
    }
    result = _translate_provider_status("FAILED", table)
    assert result == {"status": "permanent_error"}
    # Caller fills in `error` after the lookup.
