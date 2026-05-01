"""Subprocess-level CLI integration tests for thoth modes mutations (P12)."""

from __future__ import annotations

from tests._fixture_helpers import run_thoth


def test_all_six_modes_leaves_registered_at_module_load() -> None:
    """Smoke test: each of the six leaves responds to --help."""
    for op in ("add", "set", "unset", "remove", "rename", "copy"):
        rc, stdout, _stderr = run_thoth(["modes", op, "--help"])
        assert rc == 0, f"`thoth modes {op} --help` failed"
        # Click prints the leaf's usage; minimum sanity check.
        assert op in stdout.lower()
