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


def test_modes_set_via_subprocess_human(isolated_thoth_home: Path) -> None:  # TS02g (human path)
    rc, _, _ = run_thoth(["modes", "add", "brief", "--model", "gpt-4o-mini"])
    assert rc == 0
    rc, _, _ = run_thoth(["modes", "set", "brief", "temperature", "0.2"])
    assert rc == 0
    cfg = Path(isolated_thoth_home) / "config" / "thoth" / "thoth.config.toml"
    assert "temperature = 0.2" in cfg.read_text()


def test_modes_set_json_via_subprocess(isolated_thoth_home: Path) -> None:  # TS02g (JSON path)
    rc, _, _ = run_thoth(["modes", "add", "brief", "--model", "gpt-4o-mini"])
    assert rc == 0
    rc, stdout, _ = run_thoth(["modes", "set", "brief", "temperature", "0.2", "--json"])
    assert rc == 0
    payload = json.loads(stdout)
    assert payload["status"] == "ok"
    data = payload["data"]
    assert data["schema_version"] == "1"
    assert data["op"] == "set"
    assert data["mode"] == "brief"
    assert data["key"] == "temperature"
    assert data["value"] == 0.2
    assert data["wrote"] is True
    assert data["target"]["tier"] == "modes"


def test_modes_set_json_masks_secret_value(
    isolated_thoth_home: Path,
) -> None:  # TS02g (secret masking)
    """Secret-like keys (matching `_is_secret_key`) have their value masked
    in the JSON receipt, but written verbatim to TOML. The matched suffix
    is `api_key`."""
    rc, _, _ = run_thoth(["modes", "add", "brief", "--model", "gpt-4o-mini"])
    assert rc == 0
    rc, stdout, _ = run_thoth(
        ["modes", "set", "brief", "api_key", "sk-supersecret123", "--string", "--json"]
    )
    assert rc == 0
    payload = json.loads(stdout)
    data = payload["data"]
    # Receipt value is masked: format is ****<last4>
    assert data["value"] != "sk-supersecret123"
    assert data["value"].startswith("****")
    assert data["value"].endswith("t123")
    # File still has the real value (TOML round-trip preserves it)
    cfg = Path(isolated_thoth_home) / "config" / "thoth" / "thoth.config.toml"
    assert "sk-supersecret123" in cfg.read_text()


def test_modes_unset_json_via_subprocess(isolated_thoth_home: Path) -> None:  # TS03g
    """JSON envelope shape for `unset`."""
    rc, _, _ = run_thoth(["modes", "add", "brief", "--model", "gpt-4o-mini"])
    assert rc == 0
    rc, _, _ = run_thoth(["modes", "set", "brief", "temperature", "0.2"])
    assert rc == 0
    rc, stdout, _ = run_thoth(["modes", "unset", "brief", "temperature", "--json"])
    assert rc == 0
    payload = json.loads(stdout)
    assert payload["status"] == "ok"
    data = payload["data"]
    assert data["schema_version"] == "1"
    assert data["op"] == "unset"
    assert data["mode"] == "brief"
    assert data["key"] == "temperature"
    assert data["removed"] is True
    assert data["table_pruned"] is False
    assert data["target"]["tier"] == "modes"
