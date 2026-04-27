"""Runtime dependency container (`AppContext`).

Replaces the module-level singletons (`console`, `_current_*`, `_interrupt_event`)
with an explicit dataclass that gets constructed once in `cli.main()` and threaded
through the research-execution call chain. Tests construct their own `AppContext`
with stub fields instead of monkeypatching module globals.

Thread-safety: an `AppContext` is constructed once per CLI invocation; no
concurrent mutation is expected except the `interrupt_event` field, which is a
`threading.Event` and is safe to `set()`/`clear()` from a signal handler.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from thoth.checkpoint import CheckpointManager
    from thoth.config import ConfigManager
    from thoth.models import OperationStatus
    from thoth.output import OutputManager


@dataclass
class AppContext:
    """Runtime dependencies passed explicitly instead of via module globals.

    - `config`: the loaded ConfigManager. Required.
    - `console`: Rich console for all user-facing output.
    - `checkpoint_manager` / `output_manager`: set once a research operation is
      created. `None` before then.
    - `interrupt_event`: shared `threading.Event` the SIGINT handler sets.
    - `current_operation`: the in-flight `OperationStatus`, if any.
    - `verbose`: propagates the CLI `--verbose` flag.
    """

    config: ConfigManager
    console: Console = field(default_factory=Console)
    checkpoint_manager: CheckpointManager | None = None
    output_manager: OutputManager | None = None
    interrupt_event: threading.Event = field(default_factory=threading.Event)
    current_operation: OperationStatus | None = None
    verbose: bool = False
    quiet: bool = False
    no_metadata: bool = False
    timeout_override: float | None = None
    cli_api_keys: dict[str, str | None] = field(default_factory=dict)


__all__ = ["AppContext"]
