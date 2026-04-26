"""Progress spinner integration for sync background-mode operations."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from contextlib import contextmanager
from typing import IO, TYPE_CHECKING

from thoth.config import is_background_model

if TYPE_CHECKING:
    from rich.console import Console


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
def run_with_spinner(
    label: str,
    expected_minutes: int = 20,
    *,
    console: Console | None = None,
) -> Iterator[None]:
    """Display a ThothSpinner while the wrapped block runs.

    Caller pre-decides via should_show_spinner(); this context manager assumes
    the gate already returned True. Pass an existing Rich ``console`` so the
    spinner doesn't open a second Console (which would race with any active
    rich.Live elsewhere). With no console, a fresh one is created.

    Configuration choices (deliberate for thoth's deep_research UX):
      * spinner_style="npm_dots" — familiar from npm/Claude Code
      * message_shimmer=True — anti-frustration on 20-min waits
      * timer_format="auto" — elapsed-time counter is the most useful signal
      * hint_text="Ctrl-C to background" — accurate to thoth's SIGINT semantics
      * progress component hidden — provider returns ~0% during deep_research
    """
    from rich.console import Console
    from rich.live import Live
    from thothspinner import ThothSpinner

    rich_console = console if console is not None else Console()
    spinner = ThothSpinner(
        spinner_style="npm_dots",
        message_shimmer=True,
        timer_format="auto",
        hint_text="Ctrl-C to background",
    )
    progress_component = (
        spinner.get_component("progress") if hasattr(spinner, "get_component") else None
    )
    if progress_component is not None and hasattr(progress_component, "visible"):
        progress_component.visible = False
    if hasattr(spinner, "set_message"):
        spinner.set_message(text=f"{label} · ~{expected_minutes} min expected")
    with Live(spinner, console=rich_console, refresh_per_second=10):
        spinner.start()
        try:
            yield
            if hasattr(spinner, "success"):
                spinner.success(f"{label} complete")
        except BaseException:
            if hasattr(spinner, "error"):
                spinner.error(f"{label} interrupted")
            raise
