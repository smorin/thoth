"""Polling-interval scheduler tests — migrated from thoth_test BUG-03-01/02.

These tests exercise the jitter/poll-interval math inside
`thoth.run._execute_research` by stubbing `thoth.run.asyncio` (for
`get_running_loop`/`sleep`) and `thoth.run.random` (for `uniform`) via
`monkeypatch.setattr`, which is reversible and xdist-safe.
"""

from __future__ import annotations

import asyncio
import types
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import pytest

from tests._fixture_helpers import FakeLoop, MockSeqProvider
from thoth.__main__ import OperationStatus, _execute_research


async def _noop_save(op: object) -> None:
    return None


async def _stub_save_result(
    op: object, provider: str, content: str, output_dir: object, **kw: object
) -> Path:
    return Path("/tmp/mock_result.md")


def _build_asyncio_stub(fake_loop: FakeLoop) -> types.SimpleNamespace:
    async def fake_sleep(seconds: float) -> None:
        fake_loop.advance(seconds)

    return types.SimpleNamespace(get_running_loop=lambda: fake_loop, sleep=fake_sleep)


def _run_execute(provider: MockSeqProvider, poll_interval: float, op_id: str) -> None:
    config_stub = types.SimpleNamespace(
        data={"execution": {"poll_interval": poll_interval, "max_wait": 1}}
    )
    checkpoint_stub = types.SimpleNamespace(save=_noop_save)
    output_stub = types.SimpleNamespace(save_result=_stub_save_result)
    operation = OperationStatus(
        id=op_id,
        prompt="test",
        mode="default",
        status="queued",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    asyncio.run(
        _execute_research(
            operation=operation,
            checkpoint_manager=cast(Any, checkpoint_stub),
            output_manager=cast(Any, output_stub),
            config=cast(Any, config_stub),
            mode_config={"system_prompt": ""},
            providers={"mock": provider},
            quiet=True,
            verbose=False,
            output_dir=None,
            combined=False,
            project=None,
            mode="default",
            prompt="test",
        )
    )


def test_negative_jitter_does_not_truncate_two_second_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BUG-03-01: Negative jitter must not truncate a 2s interval down to a 1s poll."""
    fake_loop = FakeLoop()
    provider = MockSeqProvider(fake_loop)
    monkeypatch.setattr("thoth.run.asyncio", _build_asyncio_stub(fake_loop))
    monkeypatch.setattr(
        "thoth.run.random",
        types.SimpleNamespace(uniform=lambda _a, _b: -0.10),
    )

    _run_execute(provider, poll_interval=2.0, op_id="bug03-01")

    assert provider.poll_times == [0.0, 1.8], (
        f"expected polls at t=0.0s and t=1.8s with -10% jitter on a 2.0s base interval, "
        f"got: {provider.poll_times}"
    )


def test_sub_second_poll_interval_is_honored(monkeypatch: pytest.MonkeyPatch) -> None:
    """BUG-03-02: Sub-second poll intervals must be honored instead of rounding up to 1s."""
    fake_loop = FakeLoop()
    provider = MockSeqProvider(fake_loop)
    monkeypatch.setattr("thoth.run.asyncio", _build_asyncio_stub(fake_loop))
    monkeypatch.setattr(
        "thoth.run.random",
        types.SimpleNamespace(uniform=lambda _a, _b: 0.0),
    )

    _run_execute(provider, poll_interval=0.25, op_id="bug03-02")

    assert provider.poll_times == [0.0, 0.25], (
        "expected a 0.25s poll interval to be honored exactly in the scheduler, "
        f"got: {provider.poll_times}"
    )
