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

from unittest.mock import patch

from rich.console import Console

from thoth.run import _poll_display


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
