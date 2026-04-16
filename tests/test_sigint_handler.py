"""Tests for cooperative SIGINT handling and atomic result writes."""

from __future__ import annotations

import asyncio
import json
import signal
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from thoth import __main__ as thoth_main
from thoth.__main__ import (
    CheckpointManager,
    OperationStatus,
    OutputManager,
    handle_sigint,
)


def _make_operation(tmp_path: Path) -> OperationStatus:
    return OperationStatus(
        id="research-20260416-000000-0000000000000000",
        prompt="test prompt",
        mode="default",
        status="running",
        created_at=datetime(2026, 4, 16, 0, 0, 0),
        updated_at=datetime(2026, 4, 16, 0, 0, 0),
    )


def _make_stub_config(tmp_path: Path) -> SimpleNamespace:
    """Minimal Config shape for OutputManager."""
    return SimpleNamespace(
        data={
            "paths": {"base_output_dir": str(tmp_path)},
            "output": {
                "format": "markdown",
                "timestamp_format": "%Y%m%d-%H%M%S",
                "include_metadata": False,
            },
        }
    )


def _make_stub_checkpoint_manager(tmp_path: Path) -> SimpleNamespace:
    """Minimal CheckpointManager shape for handle_sigint."""
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    return SimpleNamespace(checkpoint_dir=checkpoint_dir)


@pytest.fixture(autouse=True)
def _reset_interrupt_globals():
    """Ensure each test starts with cleared interrupt state."""
    thoth_main._interrupt_event.clear()
    thoth_main._last_interrupt_at = None
    thoth_main._current_checkpoint_manager = None
    thoth_main._current_operation = None
    yield
    thoth_main._interrupt_event.clear()
    thoth_main._last_interrupt_at = None
    thoth_main._current_checkpoint_manager = None
    thoth_main._current_operation = None


class TestSaveResultAtomic:
    """OutputManager.save_result must write atomically."""

    def test_save_result_completes_atomically(self, tmp_path: Path) -> None:
        config = _make_stub_config(tmp_path)
        manager = OutputManager(config, no_metadata=True)
        operation = _make_operation(tmp_path)
        final_path = asyncio.run(
            manager.save_result(
                operation,
                provider="openai",
                content="hello world",
                output_dir=str(tmp_path),
            )
        )
        assert final_path.exists()
        assert final_path.read_text() == "hello world"
        siblings = list(tmp_path.glob("*.tmp"))
        assert siblings == []

    def test_save_result_write_failure_leaves_no_final_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config = _make_stub_config(tmp_path)
        manager = OutputManager(config, no_metadata=True)
        operation = _make_operation(tmp_path)

        class _FailingFile:
            def __init__(self, target: Path) -> None:
                self.target = target

            async def __aenter__(self):
                # Simulate aiofiles opening the tmp file and writing partial bytes.
                self.target.write_text("partial")
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def write(self, data: str) -> None:
                raise RuntimeError("simulated interrupt")

        def failing_open(path, *args, **kwargs):
            return _FailingFile(Path(path))

        monkeypatch.setattr(thoth_main.aiofiles, "open", failing_open)

        with pytest.raises(RuntimeError, match="simulated interrupt"):
            asyncio.run(
                manager.save_result(
                    operation,
                    provider="openai",
                    content="complete content",
                    output_dir=str(tmp_path),
                )
            )

        md_files = list(tmp_path.glob("*.md"))
        assert md_files == [], f"final .md should not exist, found {md_files}"
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == [], f"tmp leftover should be cleaned up, found {tmp_files}"


class TestInterruptFlag:
    """The cooperative interrupt flag raises KeyboardInterrupt when set."""

    def test_raise_if_interrupted_raises_when_flag_set(self) -> None:
        thoth_main._interrupt_event.set()
        with pytest.raises(KeyboardInterrupt):
            thoth_main._raise_if_interrupted()

    def test_raise_if_interrupted_no_raise_when_clear(self) -> None:
        assert not thoth_main._interrupt_event.is_set()
        thoth_main._raise_if_interrupted()


class TestHandleSigint:
    """handle_sigint: cooperative on first press, force-exit on quick second press."""

    def test_first_press_sets_flag_and_returns(self, tmp_path: Path) -> None:
        thoth_main._current_checkpoint_manager = _make_stub_checkpoint_manager(tmp_path)
        thoth_main._current_operation = _make_operation(tmp_path)

        handle_sigint(signal.SIGINT, None)

        assert thoth_main._interrupt_event.is_set()
        assert thoth_main._last_interrupt_at is not None

    def test_first_press_writes_checkpoint(self, tmp_path: Path) -> None:
        cm = _make_stub_checkpoint_manager(tmp_path)
        op = _make_operation(tmp_path)
        thoth_main._current_checkpoint_manager = cm
        thoth_main._current_operation = op

        handle_sigint(signal.SIGINT, None)

        checkpoint_file = cm.checkpoint_dir / f"{op.id}.json"
        assert checkpoint_file.exists()
        data = json.loads(checkpoint_file.read_text())
        assert data["status"] == "cancelled"

    def test_second_press_within_window_force_exits(self, tmp_path: Path) -> None:
        thoth_main._current_checkpoint_manager = _make_stub_checkpoint_manager(tmp_path)
        thoth_main._current_operation = _make_operation(tmp_path)

        handle_sigint(signal.SIGINT, None)

        with pytest.raises(SystemExit) as exc_info:
            handle_sigint(signal.SIGINT, None)
        assert exc_info.value.code == 1

    def test_press_after_window_is_cooperative_again(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        thoth_main._current_checkpoint_manager = _make_stub_checkpoint_manager(tmp_path)
        thoth_main._current_operation = _make_operation(tmp_path)

        clock = {"t": 1000.0}

        def fake_monotonic() -> float:
            return clock["t"]

        monkeypatch.setattr(thoth_main.time, "monotonic", fake_monotonic)

        handle_sigint(signal.SIGINT, None)
        first_ts = thoth_main._last_interrupt_at

        clock["t"] += 5.0  # outside the 2s second-press window

        handle_sigint(signal.SIGINT, None)

        assert thoth_main._interrupt_event.is_set()
        assert thoth_main._last_interrupt_at is not None
        assert thoth_main._last_interrupt_at > first_ts

    def test_first_press_with_no_active_operation_is_noop(self) -> None:
        thoth_main._current_checkpoint_manager = None
        thoth_main._current_operation = None

        handle_sigint(signal.SIGINT, None)

        assert thoth_main._interrupt_event.is_set()


class TestCheckpointManagerStillWorks:
    """Regression: real CheckpointManager.save is unchanged."""

    def test_checkpoint_save_round_trip(self, tmp_path: Path) -> None:
        config = SimpleNamespace(data={"paths": {"checkpoint_dir": str(tmp_path / "ckpt")}})
        cm = CheckpointManager(config)
        op = _make_operation(tmp_path)
        asyncio.run(cm.save(op))
        loaded = asyncio.run(cm.load(op.id))
        assert loaded is not None
        assert loaded.id == op.id
        assert loaded.status == op.status
