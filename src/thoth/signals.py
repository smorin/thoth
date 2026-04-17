"""Cooperative SIGINT handling and global cancellation state.

Module-level state is the source of truth during a CLI run:
  _interrupt_event             — set on first Ctrl-C; polled by the async loop
  _last_interrupt_at           — monotonic time of most recent Ctrl-C
  _current_checkpoint_manager  — set by run loop so the signal handler can checkpoint
  _current_operation           — set by run loop so the signal handler can checkpoint
  _INTERRUPT_FORCE_EXIT_WINDOW_S — two consecutive Ctrl-C within this window force-exit

Tests that need to preset or inspect this state should target this module
(`thoth.signals`) directly rather than the re-export shim in `thoth.__main__`,
because writing to the shim only rebinds the shim's name — handle_sigint reads
from its own module's globals.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from dataclasses import asdict
from typing import TYPE_CHECKING, Any

from rich.console import Console

if TYPE_CHECKING:
    from thoth.checkpoint import CheckpointManager
    from thoth.models import OperationStatus


_console = Console()

_current_checkpoint_manager: CheckpointManager | None = None
_current_operation: OperationStatus | None = None

_interrupt_event: threading.Event = threading.Event()
_last_interrupt_at: float | None = None
_INTERRUPT_FORCE_EXIT_WINDOW_S = 2.0


def _raise_if_interrupted() -> None:
    """Raise KeyboardInterrupt if a SIGINT has been received."""
    if _interrupt_event.is_set():
        raise KeyboardInterrupt


def handle_sigint(signum: int, frame: Any) -> None:
    """Handle Ctrl-C cooperatively.

    First press: set the cancellation flag, write a synchronous checkpoint, and
    return. The async poll loop picks up the flag at its next await boundary
    and raises KeyboardInterrupt so in-flight aiofiles writes unwind cleanly.

    Second press within _INTERRUPT_FORCE_EXIT_WINDOW_S: force-exit immediately.
    """
    global _last_interrupt_at

    now = time.monotonic()
    if (
        _interrupt_event.is_set()
        and _last_interrupt_at is not None
        and now - _last_interrupt_at < _INTERRUPT_FORCE_EXIT_WINDOW_S
    ):
        _console.print("\n[red]Force exit.[/red]")
        sys.exit(1)

    _last_interrupt_at = now
    _interrupt_event.set()

    _console.print("\n[yellow]Interrupt received. Saving checkpoint...[/yellow]")

    if _current_checkpoint_manager and _current_operation:
        if _current_operation.status not in ("cancelled", "failed", "completed"):
            _current_operation.transition_to("cancelled")

        try:
            checkpoint_dir = _current_checkpoint_manager.checkpoint_dir
            checkpoint_file = checkpoint_dir / f"{_current_operation.id}.json"
            temp_file = checkpoint_file.with_suffix(".tmp")

            data = asdict(_current_operation)
            data["created_at"] = _current_operation.created_at.isoformat()
            data["updated_at"] = _current_operation.updated_at.isoformat()
            data["output_paths"] = {k: str(v) for k, v in _current_operation.output_paths.items()}
            data["input_files"] = [str(p) for p in _current_operation.input_files]

            with open(temp_file, "w") as f:
                f.write(json.dumps(data, indent=2))
            temp_file.replace(checkpoint_file)

            _console.print(
                f"[green]✓[/green] Checkpoint saved. Resume with: thoth --resume {_current_operation.id}"
            )
        except Exception as e:
            _console.print(f"[red]Error saving checkpoint:[/red] {e}")

    _console.print("[dim]Finishing current write; press Ctrl-C again to force exit.[/dim]")
