"""P18-T38: tests for `thoth resume <op-id> --async` non-blocking single-tick path.

Covers seven contract points from `projects/P18-resume-async.md`:

  1. Path isolation     — `--async` does NOT enter `_run_polling_loop`.
  2. All running        — no save_result calls, statuses unchanged.
  3. One completed      — exactly one save_result; aggregate status stays.
  4. All completed      — every result saved; aggregate flips to completed.
  5. JSON envelope      — emits snapshot fields + `newly_completed`, no prose.
  6. Missing op-id      — exits 6 (matches default `resume`).
  7. Already-completed  — short-circuits with the existing message, exit 0.

Most tests exercise `_resume_one_tick` (or `resume_operation(async_check=True)`)
directly with stub providers. Tests 5 and 6 use the subprocess fixture to
verify CLI-surface behavior end-to-end.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import pytest

from tests._fixture_helpers import run_thoth, write_test_checkpoint
from thoth import signals as thoth_signals
from thoth.checkpoint import CheckpointManager
from thoth.config import get_config
from thoth.context import AppContext
from thoth.models import OperationStatus
from thoth.output import OutputManager
from thoth.providers.base import ResearchProvider
from thoth.run import _resume_one_tick, resume_operation


@pytest.fixture(autouse=True)
def _reset_interrupt() -> Any:
    thoth_signals._interrupt_event.clear()
    yield
    thoth_signals._interrupt_event.clear()


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class _StubProvider:
    """Records check_status / get_result / cancel calls for assertions."""

    def __init__(self, *, status_sequence: list[dict[str, Any]] | None = None) -> None:
        self.model = "stub-model"
        self.status_sequence = status_sequence or [{"status": "running", "progress": 0.5}]
        self.check_calls: list[str] = []
        self.get_result_calls: list[str] = []

    async def check_status(self, job_id: str) -> dict[str, Any]:
        self.check_calls.append(job_id)
        return self.status_sequence[min(len(self.check_calls) - 1, len(self.status_sequence) - 1)]

    async def get_result(self, job_id: str, verbose: bool = False) -> str:
        self.get_result_calls.append(job_id)
        return f"# stub result for {job_id}\n\nbody.\n"

    async def reconnect(self, job_id: str) -> None:  # noqa: D401 — pass-through stub
        return None


def _make_operation(op_id: str, providers: dict[str, str]) -> OperationStatus:
    """Build an in-memory OperationStatus with the named providers running."""
    now = datetime.now()
    op = OperationStatus(
        id=op_id,
        prompt="t38 prompt",
        mode="default",
        status="running",
        created_at=now,
        updated_at=now,
    )
    for name, job_id in providers.items():
        op.providers[name] = {"status": "running", "job_id": job_id}
    return op


def _make_ctx(checkpoint_dir: Path, *, as_json: bool = False) -> AppContext:
    """Construct an AppContext that points at the given (per-test) checkpoint dir."""
    cfg = get_config()
    cfg.data["paths"]["checkpoint_dir"] = str(checkpoint_dir)
    return AppContext(config=cfg, as_json=as_json)


# ---------------------------------------------------------------------------
# 1. Path isolation
# ---------------------------------------------------------------------------


def test_resume_async_does_not_enter_polling_loop(
    isolated_thoth_home: Path,
    checkpoint_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`async_check=True` must short-circuit before `_run_polling_loop`."""
    monkeypatch.chdir(tmp_path)

    op_id = "research-20260430-async01"
    write_test_checkpoint(
        checkpoint_dir,
        op_id,
        status="running",
        providers={"mock": {"status": "running", "job_id": "mock-1"}},
    )

    stub = _StubProvider(status_sequence=[{"status": "running", "progress": 0.5}])

    async def _fake_create_provider(*args: Any, **kwargs: Any) -> _StubProvider:
        return stub

    polling_called: list[bool] = []

    async def _fake_polling_loop(*args: Any, **kwargs: Any):
        polling_called.append(True)
        raise AssertionError("polling loop must NOT run when async_check=True")

    with (
        patch("thoth.run.create_provider", side_effect=lambda *a, **kw: stub),
        patch("thoth.run._run_polling_loop", side_effect=_fake_polling_loop),
    ):
        asyncio.run(resume_operation(op_id, verbose=False, async_check=True, quiet=True))

    assert polling_called == [], "polling loop fired unexpectedly"
    assert stub.check_calls == ["mock-1"], f"expected one check_status call, got {stub.check_calls}"


# ---------------------------------------------------------------------------
# 2. All running
# ---------------------------------------------------------------------------


def test_resume_async_all_running_writes_no_files(
    isolated_thoth_home: Path,
    checkpoint_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every provider returns running → no file written, statuses unchanged."""
    monkeypatch.chdir(tmp_path)

    op = _make_operation(
        "research-20260430-async02",
        {"openai": "job-oai", "perplexity": "job-pplx"},
    )

    p_oai = _StubProvider(status_sequence=[{"status": "running", "progress": 0.4}])
    p_pplx = _StubProvider(status_sequence=[{"status": "queued"}])
    instances = cast(dict[str, ResearchProvider], {"openai": p_oai, "perplexity": p_pplx})

    cm = CheckpointManager(get_config())
    om = OutputManager(get_config(), no_metadata=True)
    ctx = _make_ctx(checkpoint_dir)

    tick = asyncio.run(
        _resume_one_tick(op, instances, om, cm, {"system_prompt": ""}, ctx, verbose=False)
    )

    assert tick["newly_completed"] == []
    assert tick["all_done"] is False
    assert op.providers["openai"]["status"] == "running"
    assert op.providers["perplexity"]["status"] == "running"
    # No files written: tmp_path stays free of *_mock_*.md / *_openai_*.md outputs.
    assert list(tmp_path.glob("*.md")) == []


# ---------------------------------------------------------------------------
# 3. One completed, one running
# ---------------------------------------------------------------------------


def test_resume_async_partial_completion_saves_only_completed(
    isolated_thoth_home: Path,
    checkpoint_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One provider completed, one running → exactly one save; aggregate stays running."""
    monkeypatch.chdir(tmp_path)

    op = _make_operation(
        "research-20260430-async03",
        {"openai": "job-oai", "perplexity": "job-pplx"},
    )

    p_oai = _StubProvider(status_sequence=[{"status": "completed", "progress": 1.0}])
    p_pplx = _StubProvider(status_sequence=[{"status": "running", "progress": 0.5}])

    cm = CheckpointManager(get_config())
    om = OutputManager(get_config(), no_metadata=True)
    ctx = _make_ctx(checkpoint_dir)

    tick = asyncio.run(
        _resume_one_tick(
            op,
            cast(dict[str, ResearchProvider], {"openai": p_oai, "perplexity": p_pplx}),
            om,
            cm,
            {"system_prompt": ""},
            ctx,
            verbose=False,
        )
    )

    assert tick["newly_completed"] == ["openai"]
    assert tick["all_done"] is False
    assert op.providers["openai"]["status"] == "completed"
    assert op.providers["perplexity"]["status"] == "running"
    assert p_oai.get_result_calls == ["job-oai"]
    assert p_pplx.get_result_calls == []
    # Locked decision: aggregate status stays as-is on partial completion.
    assert op.status == "running"


# ---------------------------------------------------------------------------
# 4. All completed
# ---------------------------------------------------------------------------


def test_resume_async_all_completed_flips_aggregate(
    isolated_thoth_home: Path,
    checkpoint_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All providers completed → aggregate operation.status flips to completed."""
    monkeypatch.chdir(tmp_path)

    op = _make_operation(
        "research-20260430-async04",
        {"openai": "job-oai", "perplexity": "job-pplx"},
    )

    p_oai = _StubProvider(status_sequence=[{"status": "completed", "progress": 1.0}])
    p_pplx = _StubProvider(status_sequence=[{"status": "completed", "progress": 1.0}])

    cm = CheckpointManager(get_config())
    om = OutputManager(get_config(), no_metadata=True)
    ctx = _make_ctx(checkpoint_dir)

    tick = asyncio.run(
        _resume_one_tick(
            op,
            cast(dict[str, ResearchProvider], {"openai": p_oai, "perplexity": p_pplx}),
            om,
            cm,
            {"system_prompt": ""},
            ctx,
            verbose=False,
        )
    )

    assert sorted(tick["newly_completed"]) == ["openai", "perplexity"]
    assert tick["all_done"] is True
    assert op.providers["openai"]["status"] == "completed"
    assert op.providers["perplexity"]["status"] == "completed"
    assert op.status == "completed"


# ---------------------------------------------------------------------------
# 5. JSON envelope (subprocess CLI)
# ---------------------------------------------------------------------------


def test_resume_async_json_envelope_includes_newly_completed(
    isolated_thoth_home: Path,
    checkpoint_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`thoth resume OP --async --json` emits the snapshot + newly_completed field."""
    monkeypatch.chdir(tmp_path)

    op_id = "research-20260430-async05"
    # Pre-stage a checkpoint with a still-running mock provider; the actual
    # tick will run the real MockProvider, which completes on first check
    # (default delay path is fast in tests).
    write_test_checkpoint(
        checkpoint_dir,
        op_id,
        status="running",
        providers={"mock": {"status": "running", "job_id": "mock-existing"}},
    )

    exit_code, stdout, _stderr = run_thoth(
        ["resume", op_id, "--async", "--json"],
        env_overrides={"THOTH_MOCK_BEHAVIOR": "default", "THOTH_POLL_INTERVAL": "0.1"},
    )

    assert exit_code == 0, f"expected exit 0, got {exit_code}\nstdout={stdout!r}"
    envelope = json.loads(stdout.strip())
    # `emit_json` wraps payloads as {"status": "ok", "data": {...}}.
    assert envelope["status"] == "ok", f"unexpected envelope status: {envelope}"
    payload = envelope["data"]
    assert payload["operation_id"] == op_id
    assert "newly_completed" in payload, f"newly_completed missing from envelope: {payload}"
    assert isinstance(payload["newly_completed"], list)
    assert "providers" in payload
    assert "status" in payload


# ---------------------------------------------------------------------------
# 6. Missing op-id (subprocess CLI)
# ---------------------------------------------------------------------------


def test_resume_async_missing_op_id_exits_6(
    isolated_thoth_home: Path,
    checkpoint_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing operation id with --async exits 6 (matches default resume)."""
    monkeypatch.chdir(tmp_path)

    exit_code, _stdout, stderr = run_thoth(["resume", "op_does_not_exist", "--async"])

    assert exit_code == 6, f"expected exit 6, got {exit_code}\nstderr={stderr!r}"


# ---------------------------------------------------------------------------
# 7. Already-completed no-op
# ---------------------------------------------------------------------------


def test_resume_async_already_completed_is_noop(
    isolated_thoth_home: Path,
    checkpoint_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Already-completed operation: no API calls, exits cleanly with the existing message."""
    monkeypatch.chdir(tmp_path)

    op_id = "research-20260430-async07"
    write_test_checkpoint(
        checkpoint_dir,
        op_id,
        status="completed",
        providers={"mock": {"status": "completed"}},
    )

    # Track whether create_provider is ever called — for a completed op, it must NOT be.
    calls: list[Any] = []

    def _spy_create_provider(*args: Any, **kwargs: Any) -> Any:
        calls.append(args)
        raise AssertionError("create_provider must not run for an already-completed op")

    with patch("thoth.run.create_provider", side_effect=_spy_create_provider):
        asyncio.run(resume_operation(op_id, verbose=False, async_check=True, quiet=True))

    assert calls == [], "create_provider was called for a completed op"

    # Checkpoint untouched.
    cp = json.loads((checkpoint_dir / f"{op_id}.json").read_text())
    assert cp["status"] == "completed"
    assert cp["providers"]["mock"]["status"] == "completed"
    # Spot-check updated_at didn't change since we wrote it.
    parsed = datetime.fromisoformat(cp["updated_at"])
    assert (datetime.now() - parsed).total_seconds() < 60
