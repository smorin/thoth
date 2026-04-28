"""P18 Phase C: progress display suppression for immediate-kind runs.

Today (pre-P18) `should_show_spinner` returns False for non-deep-research
models, but the unified `_poll_display` falls through to a `rich.Progress`
bar for those cases. After P18, immediate-kind runs see NEITHER spinner NOR
Progress bar.

See spec §5.7 + Phase C in the plan.
"""

from __future__ import annotations

import io

from thoth.progress import should_show_spinner


class _FakeTTY(io.StringIO):
    def isatty(self) -> bool:
        return True


def test_should_show_spinner_false_for_immediate_mode_cfg() -> None:
    """Immediate mode_cfg suppresses spinner regardless of model substring."""
    tty = _FakeTTY()
    immediate_cfg = {"model": "o3-deep-research", "kind": "immediate"}
    # Even with a deep-research model, declared immediate kind wins → no spinner
    assert (
        should_show_spinner(
            model=immediate_cfg["model"],
            async_mode=False,
            verbose=False,
            stream=tty,
            mode_cfg=immediate_cfg,
        )
        is False
    )


def test_should_show_spinner_true_for_background_mode_cfg_in_tty() -> None:
    """Background kind + TTY + sync + non-verbose → spinner engages (existing behavior)."""
    tty = _FakeTTY()
    background_cfg = {"model": "o3-deep-research", "kind": "background"}
    assert (
        should_show_spinner(
            model=background_cfg["model"],
            async_mode=False,
            verbose=False,
            stream=tty,
            mode_cfg=background_cfg,
        )
        is True
    )


def test_should_show_spinner_legacy_callers_unchanged() -> None:
    """Callers without mode_cfg keep the pre-P18 model-only gate."""
    tty = _FakeTTY()
    # No mode_cfg passed; falls back to is_background_model substring
    assert (
        should_show_spinner(
            model="o3-deep-research",
            async_mode=False,
            verbose=False,
            stream=tty,
        )
        is True
    )
    assert (
        should_show_spinner(
            model="o3",
            async_mode=False,
            verbose=False,
            stream=tty,
        )
        is False
    )


def test_should_show_spinner_async_overrides_immediate_or_background() -> None:
    """`--async` always wins — user wants to background and exit, not watch."""
    tty = _FakeTTY()
    cfg = {"model": "o3-deep-research", "kind": "background"}
    assert (
        should_show_spinner(
            model=cfg["model"],
            async_mode=True,
            verbose=False,
            stream=tty,
            mode_cfg=cfg,
        )
        is False
    )


def test_should_show_spinner_verbose_overrides() -> None:
    tty = _FakeTTY()
    cfg = {"model": "o3-deep-research", "kind": "background"}
    assert (
        should_show_spinner(
            model=cfg["model"],
            async_mode=False,
            verbose=True,
            stream=tty,
            mode_cfg=cfg,
        )
        is False
    )


def test_should_show_spinner_non_tty_returns_false() -> None:
    pipe = io.StringIO()  # no isatty() → False
    cfg = {"model": "o3-deep-research", "kind": "background"}
    assert (
        should_show_spinner(
            model=cfg["model"],
            async_mode=False,
            verbose=False,
            stream=pipe,
            mode_cfg=cfg,
        )
        is False
    )
