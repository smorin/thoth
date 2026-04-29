"""Interactive-mode slash command + op-id wiring — migrated from thoth_test P07-M3-01/02.

Uses `monkeypatch.setattr` on the `thoth.__main__` shim; `_ShimModule.__setattr__`
propagates rebinds to `thoth.interactive`, so the fakes are visible at call
sites inside `enter_interactive_mode` / `InteractiveSession`.
"""

from __future__ import annotations

import asyncio
import builtins
from typing import Any, cast

import pytest

import thoth.__main__ as thoth_main


def test_basic_interactive_mode_stores_last_operation_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """P07-M3-01: basic interactive mode stores the last operation ID after submission."""
    observed: dict[str, Any] = {}
    original_registry = thoth_main.SlashCommandRegistry

    class RecordingRegistry(original_registry):
        last_created: RecordingRegistry | None = None

        def __init__(self, console: Any) -> None:
            super().__init__(console)
            RecordingRegistry.last_created = self

    async def fake_run_research(**kwargs: Any) -> str:
        observed["kwargs"] = kwargs
        return "research-20260416-010101-abcdef1234567890"

    prompts = iter(["interactive stored op id"])

    def fake_input(prompt: object = "") -> str:
        try:
            return next(prompts)
        except StopIteration as exc:
            raise EOFError("no more inputs") from exc

    monkeypatch.setattr(thoth_main, "PROMPT_TOOLKIT_AVAILABLE", False)
    monkeypatch.setattr(thoth_main, "run_research", cast(Any, fake_run_research))
    monkeypatch.setattr(thoth_main, "SlashCommandRegistry", cast(Any, RecordingRegistry))
    monkeypatch.setattr(builtins, "input", cast(Any, fake_input))

    asyncio.run(
        thoth_main.enter_interactive_mode(
            initial_settings=thoth_main.InteractiveInitialSettings(provider="mock"),
            project=None,
            output_dir=None,
            config_path=None,
            verbose=False,
            quiet=True,
            no_metadata=False,
            timeout=None,
        )
    )

    registry = RecordingRegistry.last_created
    assert registry is not None, "interactive mode did not create a slash registry"
    assert registry.last_operation_id == "research-20260416-010101-abcdef1234567890", (
        f"expected stored operation id, got: {registry.last_operation_id!r}"
    )
    assert observed["kwargs"]["prompt"] == "interactive stored op id"


def test_basic_interactive_mode_threads_profile_to_run_research(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BUG-02: --profile passed to enter_interactive_mode reaches both
    get_config (so profile-aware overlays are applied during interactive
    setup) and run_research (so the profile is honored on each prompt)."""
    observed: dict[str, Any] = {}
    get_config_calls: list[str | None] = []

    async def fake_run_research(**kwargs: Any) -> str:
        observed["kwargs"] = kwargs
        return "research-20260416-020202-fedcba9876543210"

    def fake_get_config(profile: str | None = None) -> Any:
        get_config_calls.append(profile)
        # Return a minimal stand-in with the attribute access the basic-input
        # branch makes: config.data["general"].get("default_mode", ...).
        from thoth.config import ConfigManager

        cm = ConfigManager.__new__(ConfigManager)
        cm.data = {"general": {"default_mode": "default"}}
        return cm

    prompts = iter(["profile reaches run_research"])

    def fake_input(prompt: object = "") -> str:
        try:
            return next(prompts)
        except StopIteration as exc:
            raise EOFError("no more inputs") from exc

    import thoth.interactive as _interactive

    monkeypatch.setattr(thoth_main, "PROMPT_TOOLKIT_AVAILABLE", False)
    monkeypatch.setattr(thoth_main, "run_research", cast(Any, fake_run_research))
    monkeypatch.setattr(_interactive, "get_config", cast(Any, fake_get_config))
    monkeypatch.setattr(builtins, "input", cast(Any, fake_input))

    asyncio.run(
        thoth_main.enter_interactive_mode(
            initial_settings=thoth_main.InteractiveInitialSettings(provider="mock"),
            project=None,
            output_dir=None,
            config_path=None,
            verbose=False,
            quiet=True,
            no_metadata=False,
            timeout=None,
            profile="fast",
        )
    )

    assert get_config_calls == ["fast"], (
        f"expected get_config called once with profile='fast', got: {get_config_calls!r}"
    )
    assert observed["kwargs"].get("profile") == "fast", (
        f"expected profile='fast' to reach run_research, got: {observed['kwargs'].get('profile')!r}"
    )


def test_slash_status_delegates_to_show_status(monkeypatch: pytest.MonkeyPatch) -> None:
    """P07-M3-02: prompt-toolkit /status delegates to show_status for the last operation."""
    if not getattr(thoth_main, "PROMPT_TOOLKIT_AVAILABLE", False):
        pytest.skip("prompt_toolkit not available in this environment")

    captured: dict[str, Any] = {}

    async def fake_show_status(operation_id: str) -> None:
        captured["operation_id"] = operation_id

    monkeypatch.setattr(thoth_main, "run_in_terminal", cast(Any, lambda fn: fn()))
    monkeypatch.setattr(thoth_main, "show_status", cast(Any, fake_show_status))

    session = thoth_main.InteractiveSession(
        thoth_main.console,
        thoth_main.get_config(),
        thoth_main.InteractiveInitialSettings(provider="mock"),
    )
    session.slash_registry.last_operation_id = "research-20260416-020202-fedcba9876543210"
    session._handle_slash_command("/status")

    assert captured.get("operation_id") == "research-20260416-020202-fedcba9876543210", (
        f"/status did not delegate to show_status: {captured}"
    )
