"""Subprocess-level CLI integration tests for thoth modes mutations (P12)."""

from __future__ import annotations

import json
from pathlib import Path

from tests._fixture_helpers import run_thoth


def test_all_six_modes_leaves_registered_at_module_load() -> None:
    """Smoke test: each of the six leaves responds to --help."""
    for op in ("add", "set", "unset", "remove", "rename", "copy"):
        rc, stdout, _stderr = run_thoth(["modes", op, "--help"])
        assert rc == 0, f"`thoth modes {op} --help` failed"
        # Click prints the leaf's usage; minimum sanity check.
        assert op in stdout.lower()


def test_modes_add_via_subprocess(isolated_thoth_home: Path) -> None:
    rc, _stdout, _stderr = run_thoth(["modes", "add", "brief", "--model", "gpt-4o-mini"])
    assert rc == 0
    cfg = Path(isolated_thoth_home) / "config" / "thoth" / "thoth.config.toml"
    assert "[modes.brief]" in cfg.read_text()


def test_modes_add_json_via_subprocess(isolated_thoth_home: Path) -> None:
    rc, stdout, _stderr = run_thoth(["modes", "add", "brief", "--model", "gpt-4o-mini", "--json"])
    assert rc == 0
    payload = json.loads(stdout)
    assert payload["status"] == "ok"
    data = payload["data"]
    assert data["schema_version"] == "1"
    assert data["op"] == "add"
    assert data["mode"] == "brief"
    assert data["created"] is True
    assert data["target"]["tier"] == "modes"
    assert "file" in data["target"]
