"""Tests for `thoth.context.AppContext`.

These pin the dataclass's public surface so Phase 5 DI wiring (threading
`ctx: AppContext` through `run_research` et al.) has a stable contract.
"""

from __future__ import annotations

import threading

from rich.console import Console

from thoth.config import ConfigManager
from thoth.context import AppContext


def _stub_config() -> ConfigManager:
    """Return a ConfigManager with defaults loaded — good enough for tests."""
    cm = ConfigManager()
    cm.load_all_layers({})
    return cm


def test_app_context_requires_config() -> None:
    """`config` is the only required field."""
    ctx = AppContext(config=_stub_config())
    assert ctx.config is not None


def test_app_context_defaults_sane() -> None:
    """All optional fields have safe defaults."""
    ctx = AppContext(config=_stub_config())

    assert isinstance(ctx.console, Console)
    assert ctx.checkpoint_manager is None
    assert ctx.output_manager is None
    assert isinstance(ctx.interrupt_event, threading.Event)
    assert ctx.interrupt_event.is_set() is False
    assert ctx.current_operation is None
    assert ctx.verbose is False


def test_app_context_verbose_propagates() -> None:
    """`verbose=True` round-trips through the dataclass."""
    ctx = AppContext(config=_stub_config(), verbose=True)
    assert ctx.verbose is True


def test_app_context_console_injectable() -> None:
    """A test can pass its own Console."""
    my_console = Console(record=True)
    ctx = AppContext(config=_stub_config(), console=my_console)
    assert ctx.console is my_console


def test_app_context_interrupt_event_independent() -> None:
    """Each AppContext gets its own Event by default — no shared state."""
    a = AppContext(config=_stub_config())
    b = AppContext(config=_stub_config())

    a.interrupt_event.set()

    assert a.interrupt_event.is_set() is True
    assert b.interrupt_event.is_set() is False
