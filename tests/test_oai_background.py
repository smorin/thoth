"""OpenAI background-job status & polling-loop tests.

Migrated from `thoth_test` fixture tests OAI-BG-01…14.

- 01…08: `OpenAIProvider.check_status()` on various response shapes.
- 09…14: `_execute_research()` polling loop against provider-state-machine variants.
"""

from __future__ import annotations

import asyncio
import types
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import pytest

from tests._fixture_helpers import (
    make_mock_openai_client,
    make_mock_openai_response,
)
from thoth.__main__ import OperationStatus, _execute_research
from thoth.providers.openai import OpenAIProvider


@pytest.fixture(autouse=True)
def _isolate_config(isolated_thoth_home: Path) -> Path:
    return isolated_thoth_home


# ----- check_status() variants (OAI-BG-01…08) -----------------------------


def test_queued_status_is_not_completed() -> None:
    """OAI-BG-01: queued status must not be treated as completed."""
    provider = OpenAIProvider(api_key="dummy")
    provider.jobs["job-1"] = {"background": True, "response": None}
    provider.client = cast(Any, make_mock_openai_client(make_mock_openai_response("queued")))
    result = asyncio.run(provider.check_status("job-1"))
    assert result["status"] != "completed", f"queued was treated as completed: {result}"
    assert result["status"] == "queued", f"expected queued, got: {result}"


def test_failed_status_propagates_error() -> None:
    """OAI-BG-02: failed status must propagate the error message as permanent_error."""
    provider = OpenAIProvider(api_key="dummy")
    provider.jobs["job-1"] = {"background": True, "response": None}
    provider.client = cast(
        Any,
        make_mock_openai_client(make_mock_openai_response("failed", error="API quota exceeded")),
    )
    result = asyncio.run(provider.check_status("job-1"))
    assert result["status"] == "permanent_error", f"expected permanent_error, got: {result}"
    assert "quota" in result.get("error", ""), f"error not propagated: {result}"


def test_incomplete_status_maps_to_permanent_error() -> None:
    """OAI-BG-03: incomplete status must map to permanent_error with 'incomplete' in the error."""
    provider = OpenAIProvider(api_key="dummy")
    provider.jobs["job-1"] = {"background": True, "response": None}
    provider.client = cast(Any, make_mock_openai_client(make_mock_openai_response("incomplete")))
    result = asyncio.run(provider.check_status("job-1"))
    assert result["status"] == "permanent_error", f"expected permanent_error, got: {result}"
    assert "incomplete" in result.get("error", "").lower(), f"'incomplete' not in error: {result}"


def test_cancelled_status_maps_to_cancelled() -> None:
    """OAI-BG-04: cancelled status must map to cancelled."""
    provider = OpenAIProvider(api_key="dummy")
    provider.jobs["job-1"] = {"background": True, "response": None}
    provider.client = cast(Any, make_mock_openai_client(make_mock_openai_response("cancelled")))
    result = asyncio.run(provider.check_status("job-1"))
    assert result["status"] == "cancelled", f"expected cancelled, got: {result}"


def test_no_status_attr_is_not_completed() -> None:
    """OAI-BG-05: a response with no status attribute must not be treated as completed."""
    provider = OpenAIProvider(api_key="dummy")
    provider.jobs["job-1"] = {"background": True, "response": None}
    provider.client = cast(Any, make_mock_openai_client(types.SimpleNamespace()))
    result = asyncio.run(provider.check_status("job-1"))
    assert result["status"] != "completed", (
        f"no-status-attr response was treated as completed: {result}"
    )
    assert result["status"] in ("error", "failed", "permanent_error", "transient_error"), (
        f"expected error/failed/permanent_error/transient_error, got: {result}"
    )


def test_network_error_with_stale_inprogress_cache_is_not_completed() -> None:
    """OAI-BG-06: network error with stale cached (in_progress) response must not be completed."""
    provider = OpenAIProvider(api_key="dummy")
    stale = make_mock_openai_response("in_progress")
    provider.jobs["job-1"] = {"background": True, "response": stale}

    async def raise_error(*args: object, **kwargs: object) -> object:
        raise Exception("network error")

    provider.client = cast(
        Any, types.SimpleNamespace(responses=types.SimpleNamespace(retrieve=raise_error))
    )
    result = asyncio.run(provider.check_status("job-1"))
    assert result["status"] != "completed", (
        f"stale cached response was treated as completed: {result}"
    )
    assert result["status"] in ("error", "failed", "permanent_error", "transient_error"), (
        f"expected error/failed/permanent_error/transient_error, got: {result}"
    )


def test_network_error_with_completed_cache_still_returns_completed() -> None:
    """OAI-BG-07: exception with a genuinely completed cached response must still return completed."""
    provider = OpenAIProvider(api_key="dummy")
    good_cache = make_mock_openai_response("completed")
    provider.jobs["job-1"] = {"background": True, "response": good_cache}

    async def raise_error(*args: object, **kwargs: object) -> object:
        raise Exception("network error")

    provider.client = cast(
        Any, types.SimpleNamespace(responses=types.SimpleNamespace(retrieve=raise_error))
    )
    result = asyncio.run(provider.check_status("job-1"))
    assert result["status"] == "completed", (
        f"completed cache should survive network error: {result}"
    )


def test_in_progress_maps_to_running() -> None:
    """OAI-BG-08: in_progress still maps to running (regression guard)."""
    provider = OpenAIProvider(api_key="dummy")
    provider.jobs["job-1"] = {"background": True, "response": None}
    provider.client = cast(Any, make_mock_openai_client(make_mock_openai_response("in_progress")))
    result = asyncio.run(provider.check_status("job-1"))
    assert result["status"] == "running", f"expected running, got: {result}"


# ----- polling-loop variants (OAI-BG-09…14) -------------------------------


def _polling_stubs() -> tuple[
    types.SimpleNamespace, types.SimpleNamespace, types.SimpleNamespace, dict[str, str]
]:
    """Return (config_stub, checkpoint_stub, output_stub, mode_config) for polling tests."""
    from pathlib import Path

    async def _noop_save(op: object) -> None:
        pass

    async def _stub_save_result(
        op: object, provider: str, content: str, output_dir: object, **kw: object
    ) -> Path:
        return Path("/tmp/mock_result.md")

    config_stub = types.SimpleNamespace(data={"execution": {"poll_interval": 0.01, "max_wait": 1}})
    checkpoint_stub = types.SimpleNamespace(save=_noop_save)
    output_stub = types.SimpleNamespace(save_result=_stub_save_result)
    mode_config: dict[str, str] = {"system_prompt": ""}
    return config_stub, checkpoint_stub, output_stub, mode_config


def _make_op(op_id: str) -> OperationStatus:
    return OperationStatus(
        id=op_id,
        prompt="test",
        mode="default",
        status="queued",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def _run_research(provider: object, operation: OperationStatus) -> None:
    config_stub, checkpoint_stub, output_stub, mode_config = _polling_stubs()
    asyncio.run(
        _execute_research(
            operation=operation,
            checkpoint_manager=cast(Any, checkpoint_stub),
            output_manager=cast(Any, output_stub),
            config=cast(Any, config_stub),
            mode_config=mode_config,
            providers={"mock": cast(Any, provider)},
            quiet=True,
            verbose=False,
            output_dir=None,
            combined=False,
            project=None,
            mode="default",
            prompt="test",
        )
    )


def test_queued_does_not_exit_polling_loop() -> None:
    """OAI-BG-09: queued status does not exit prematurely — result must be retrieved."""

    class _Prov:
        model = "mock"
        _calls = 0

        async def submit(
            self, prompt: str, mode: str, system_prompt: str, verbose: bool = False
        ) -> str:
            return "job-1"

        async def check_status(self, job_id: str) -> dict[str, Any]:
            self._calls += 1
            if self._calls <= 1:
                return {"status": "queued", "progress": 0.0}
            return {"status": "completed", "progress": 1.0}

        async def get_result(self, job_id: str, verbose: bool = False) -> str:
            return "mock result content"

    op = _make_op("test-bg-09")
    _run_research(_Prov(), op)
    assert len(op.output_paths) > 0, (
        f"queued caused premature loop exit — result never retrieved: {op.output_paths}"
    )


def test_failed_provider_fails_operation() -> None:
    """OAI-BG-10: failed provider status transitions operation to failed."""

    class _Prov:
        model = "mock"
        _calls = 0

        async def submit(
            self, prompt: str, mode: str, system_prompt: str, verbose: bool = False
        ) -> str:
            return "job-1"

        async def check_status(self, job_id: str) -> dict[str, Any]:
            self._calls += 1
            if self._calls == 1:
                return {"status": "running", "progress": 0.3}
            return {"status": "failed", "error": "API quota exceeded"}

        async def get_result(self, job_id: str, verbose: bool = False) -> str:
            return ""

    op = _make_op("test-bg-10")
    _run_research(_Prov(), op)
    assert op.status == "failed", (
        f"failed provider should set operation to failed, got: {op.status}"
    )
    assert "quota" in (op.providers["mock"].get("error") or "").lower(), (
        f"provider error message should be propagated, got: {op.providers}"
    )
    assert "quota" in (op.error or "").lower(), (
        f"operation error should include provider error detail, got: {op.error}"
    )


def test_cancelled_provider_fails_operation() -> None:
    """OAI-BG-11: cancelled provider status transitions operation to failed."""

    class _Prov:
        model = "mock"

        async def submit(
            self, prompt: str, mode: str, system_prompt: str, verbose: bool = False
        ) -> str:
            return "job-1"

        async def check_status(self, job_id: str) -> dict[str, Any]:
            return {"status": "cancelled", "error": "Response was cancelled"}

        async def get_result(self, job_id: str, verbose: bool = False) -> str:
            return ""

    op = _make_op("test-bg-11")
    _run_research(_Prov(), op)
    assert op.status == "failed", (
        f"cancelled provider should set operation to failed, got: {op.status}"
    )
    assert op.providers["mock"]["status"] == "failed", (
        f"provider status should be normalized to failed, got: {op.providers}"
    )
    assert op.providers["mock"].get("failure_type") == "permanent", (
        f"cancelled jobs cannot be resumed via the original job id, "
        f"so failure_type must be permanent: {op.providers}"
    )
    assert "cancel" in (op.providers["mock"].get("error") or "").lower(), (
        f"cancelled error detail should be propagated, got: {op.providers}"
    )


def test_error_provider_fails_operation() -> None:
    """OAI-BG-12: error provider status transitions operation to failed."""

    class _Prov:
        model = "mock"

        async def submit(
            self, prompt: str, mode: str, system_prompt: str, verbose: bool = False
        ) -> str:
            return "job-1"

        async def check_status(self, job_id: str) -> dict[str, Any]:
            return {"status": "error", "error": "network error"}

        async def get_result(self, job_id: str, verbose: bool = False) -> str:
            return ""

    op = _make_op("test-bg-12")
    _run_research(_Prov(), op)
    assert op.status == "failed", f"error provider should set operation to failed, got: {op.status}"
    assert op.providers["mock"]["status"] == "failed", (
        f"error provider should be normalized to failed, got: {op.providers}"
    )
    assert op.providers["mock"].get("failure_type") == "recoverable", (
        f"'error' provider status should route to recoverable, got: {op.providers}"
    )


def test_not_found_provider_fails_with_error_details() -> None:
    """OAI-BG-13: not_found provider status normalizes to error and fails the operation."""

    class _Prov:
        model = "mock"

        async def submit(
            self, prompt: str, mode: str, system_prompt: str, verbose: bool = False
        ) -> str:
            return "job-1"

        async def check_status(self, job_id: str) -> dict[str, Any]:
            return {"status": "not_found", "error": "Job not found"}

        async def get_result(self, job_id: str, verbose: bool = False) -> str:
            return ""

    op = _make_op("test-bg-13")
    _run_research(_Prov(), op)
    assert op.status == "failed", f"not_found provider should fail the operation, got: {op.status}"
    assert op.providers["mock"]["status"] == "failed", (
        f"not_found should normalize to failed, got: {op.providers}"
    )
    assert "not found" in (op.error or "").lower(), (
        f"expected not_found details in error, got: {op.error}"
    )


def test_unknown_provider_status_fails_with_error_message() -> None:
    """OAI-BG-14: unknown provider status normalizes to error with raw state in the message."""

    class _Prov:
        model = "mock"

        async def submit(
            self, prompt: str, mode: str, system_prompt: str, verbose: bool = False
        ) -> str:
            return "job-1"

        async def check_status(self, job_id: str) -> dict[str, Any]:
            return {"status": "mystery_state", "error": "unexpected provider state"}

        async def get_result(self, job_id: str, verbose: bool = False) -> str:
            return ""

    op = _make_op("test-bg-14")
    _run_research(_Prov(), op)
    assert op.status == "failed", (
        f"unknown provider status should fail the operation, got: {op.status}"
    )
    assert op.providers["mock"]["status"] == "failed", (
        f"unknown status should normalize to failed, got: {op.providers}"
    )
    assert op.providers["mock"].get("error"), (
        f"unknown status should record an error message, got: {op.providers}"
    )
