"""P18 Phase C: immediate-mode UX deltas.

Confirms the user-visible Phase C value:

  * `_poll_display(mode_cfg=immediate)` yields None (neither spinner nor
    Progress bar engages)
  * `_execute_research` does NOT print the trailing "Operation ID" + status
    hints for immediate-kind operations
  * `_execute_research` does NOT print the "Resume with: thoth resume" hint
    on a recoverable failure for immediate-kind operations

The full path split (skipping the polling loop entirely for immediate runs)
arrives in Phase E alongside `provider.stream()`. Phase C ships the UX gates.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest
from rich.console import Console

from tests._fixture_helpers import run_thoth
from tests.conftest import make_operation
from thoth.context import AppContext
from thoth.run import _execute_immediate, _poll_display


def test_poll_display_yields_none_for_immediate_kind() -> None:
    """Declared `kind=immediate` → no progress UI at all."""
    immediate_cfg = {"model": "o3", "kind": "immediate"}
    with _poll_display(
        quiet=False,
        mode_model="o3",
        verbose=False,
        rich_console=Console(),
        mode_cfg=immediate_cfg,
    ) as display:
        assert display is None


def test_poll_display_yields_progress_for_background_no_tty() -> None:
    """Background-kind in non-TTY (test stream) → Progress bar (legacy fallback)."""
    background_cfg = {"model": "o3-deep-research", "kind": "background"}
    # We can't easily simulate a TTY in tests; the spinner path requires it.
    # Without TTY, _poll_display engages the Progress bar branch — verify it's
    # not None, which is the salient difference from the immediate path.
    with _poll_display(
        quiet=False,
        mode_model="o3-deep-research",
        verbose=False,
        rich_console=Console(),
        mode_cfg=background_cfg,
    ) as display:
        assert display is not None  # Progress object


def test_poll_display_legacy_no_mode_cfg_unchanged() -> None:
    """Pre-P18 callers without mode_cfg: behavior unchanged."""
    with _poll_display(
        quiet=False,
        mode_model="o3-deep-research",
        verbose=False,
        rich_console=Console(),
    ) as display:
        # Without mode_cfg, the model substring rule fires; non-TTY stream
        # falls through to Progress bar (existing behavior).
        assert display is not None


def test_poll_display_legacy_no_mode_cfg_immediate_model() -> None:
    """Pre-P18 caller with immediate-y model: still gets Progress (legacy)."""
    with _poll_display(
        quiet=False,
        mode_model="o3",
        verbose=False,
        rich_console=Console(),
    ) as display:
        # Without mode_cfg the function defaults to model-only check; o3 is
        # not a deep-research model → Progress bar fires (the pre-P18 path).
        assert display is not None


def test_should_show_spinner_used_by_poll_display_for_background_with_mode_cfg() -> None:
    """When mode_cfg=background, the spinner gate is consulted."""
    background_cfg = {"model": "o3-deep-research", "kind": "background"}
    with patch("thoth.run.should_show_spinner", return_value=False) as mock_gate:
        with _poll_display(
            quiet=False,
            mode_model="o3-deep-research",
            verbose=False,
            rich_console=Console(),
            mode_cfg=background_cfg,
        ):
            pass
    # Verify the gate was called — Phase C wired mode_cfg into the call.
    assert mock_gate.called
    call_kwargs = mock_gate.call_args.kwargs
    assert call_kwargs.get("mode_cfg") == background_cfg


def test_should_show_spinner_short_circuits_for_immediate() -> None:
    """For immediate kind, _poll_display short-circuits without consulting the spinner gate."""
    immediate_cfg = {"model": "o3", "kind": "immediate"}
    with patch("thoth.run.should_show_spinner", return_value=False) as mock_gate:
        with _poll_display(
            quiet=False,
            mode_model="o3",
            verbose=False,
            rich_console=Console(),
            mode_cfg=immediate_cfg,
        ) as display:
            assert display is None
    # The spinner gate should NOT have been called for immediate runs — the
    # short-circuit happens above it.
    assert not mock_gate.called


def test_immediate_stream_failure_does_not_double_fail_operation(
    isolated_thoth_home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stream failure already marked failed must not be failed a second time."""
    monkeypatch.chdir(tmp_path)

    exit_code, stdout, stderr = run_thoth(
        ["permanent stream fail", "--provider", "mock"],
        env_overrides={"THOTH_MOCK_BEHAVIOR": "permanent"},
    )
    combined = stdout + stderr

    assert exit_code == 1, combined
    assert "Mock permanent failure" in combined
    assert "Invalid state transition" not in combined


def test_immediate_falls_back_to_submit_get_result_when_stream_not_implemented(
    stub_config,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class CheckpointStub:
        def __init__(self) -> None:
            self.saved_statuses: list[str] = []

        async def save(self, operation) -> None:
            self.saved_statuses.append(operation.status)

    class OutputStub:
        async def save_result(self, *args, **kwargs):
            raise AssertionError("project-less immediate fallback must not save result files")

    class FallbackProvider:
        model = "fallback-model"

        def __init__(self) -> None:
            self.submitted: tuple[str, str, str | None] | None = None

        async def stream(self, prompt, mode, system_prompt=None, verbose=False):
            if False:
                yield None
            raise NotImplementedError("stream unavailable")

        async def submit(self, prompt, mode, system_prompt=None, verbose=False):
            self.submitted = (prompt, mode, system_prompt)
            return "job-1"

        async def get_result(self, job_id, verbose=False):
            assert job_id == "job-1"
            return "fallback content"

    checkpoint = CheckpointStub()
    provider = FallbackProvider()
    operation = make_operation("research-fallback")

    # ty doesn't honor structural typing for stub doubles; the runtime contract
    # is duck-typed and explicit `cast` would just hide the same delta. Suppress
    # arg-type for the call itself.
    asyncio.run(
        _execute_immediate(
            operation=operation,
            checkpoint_manager=checkpoint,  # ty: ignore[invalid-argument-type]
            output_manager=OutputStub(),  # ty: ignore[invalid-argument-type]
            config=stub_config,
            mode_config={"system_prompt": "system text"},
            providers={"mock": provider},
            quiet=False,
            verbose=False,
            output_dir=None,
            project=None,
            mode="default",
            prompt="fallback prompt",
            out_specs=(),
            append=False,
            ctx=AppContext(config=stub_config),
        )
    )

    assert capsys.readouterr().out == "fallback content"
    assert provider.submitted == ("fallback prompt", "default", "system text")
    assert operation.status == "completed"
    assert operation.providers["mock"]["job_id"] == "job-1"
    assert operation.output_paths == {}
    assert checkpoint.saved_statuses == ["running", "completed"]
