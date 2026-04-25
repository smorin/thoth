"""Progress spinner integration for sync background-mode operations."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from contextlib import contextmanager
from typing import IO

from thoth.config import is_background_model


def should_show_spinner(
    *,
    model: str | None,
    async_mode: bool,
    verbose: bool,
    stream: IO[str] | None = None,
) -> bool:
    """Decide whether to engage the progress spinner.

    Engages only when ALL hold:
      - the resolved model is a background (deep-research) model
      - --async is NOT set (sync caller is the one waiting)
      - --verbose is NOT set (verbose keeps raw-log UX)
      - the output stream is a TTY (avoid clobbering pipes/CI)
    """
    if async_mode or verbose:
        return False
    if not is_background_model(model):
        return False
    s = stream if stream is not None else sys.stdout
    return bool(getattr(s, "isatty", lambda: False)())


@contextmanager
def run_with_spinner(label: str, expected_minutes: int = 20) -> Iterator[None]:
    """Display a ThothSpinner while the wrapped block runs.

    Caller pre-decides via should_show_spinner(); this context manager assumes
    the gate already returned True.
    """
    from rich.console import Console
    from rich.live import Live
    from thothspinner import ThothSpinner

    console = Console()
    spinner = ThothSpinner()
    if hasattr(spinner, "set_message"):
        spinner.set_message(
            text=f"{label} · ~{expected_minutes} min expected · Ctrl-C to background"
        )
    with Live(spinner, console=console, refresh_per_second=10):
        spinner.start()
        try:
            yield
            if hasattr(spinner, "success"):
                spinner.success(f"{label} complete")
        except BaseException:
            if hasattr(spinner, "error"):
                spinner.error(f"{label} interrupted")
            raise
