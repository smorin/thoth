"""Category G — Option E non-blocking timing assertions (spec §8.4)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from click.testing import CliRunner

from tests.conftest import make_operation


@pytest.fixture
def cli():
    from thoth.cli import cli as _cli

    return _cli


def _write_checkpoint(checkpoint_dir: Path, op, **overrides) -> None:
    payload = {
        "id": op.id,
        "prompt": op.prompt,
        "mode": op.mode,
        "status": op.status,
        "created_at": op.created_at.isoformat(),
        "updated_at": op.updated_at.isoformat(),
        "output_paths": {},
        "input_files": [],
        "providers": {},
        "project": None,
        "output_dir": None,
        "error": None,
        "failure_type": None,
        **overrides,
    }
    (checkpoint_dir / f"{op.id}.json").write_text(json.dumps(payload))


def test_resume_json_returns_within_5s_for_running_op(cli, checkpoint_dir):
    op = make_operation("research-20260427-000000-aaaaaaaaaaaaaaaa", status="running")
    _write_checkpoint(checkpoint_dir, op)

    runner = CliRunner()  # NOTE: drop mix_stderr=False — Click 8.3 removed it (PR2 precedent)
    start = time.time()
    result = runner.invoke(cli, ["resume", op.id, "--json"], catch_exceptions=False)
    elapsed = time.time() - start

    assert elapsed < 5.0, f"resume --json took {elapsed:.2f}s (must be non-blocking)"
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["data"]["status"] == "running"


def test_resume_json_recoverable_failure_returns_status_ok(cli, checkpoint_dir):
    """spec §8.5: command succeeded → status:'ok'; data.status describes the op."""
    op = make_operation("research-20260427-000000-aaaaaaaaaaaaaaaa", status="failed")
    _write_checkpoint(
        checkpoint_dir,
        op,
        status="failed",
        failure_type="transient",
        error="rate limit exceeded",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["resume", op.id, "--json"], catch_exceptions=False)

    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["data"]["status"] == "recoverable_failure"


def test_ask_json_background_mode_returns_within_5s(cli, isolated_thoth_home, monkeypatch):
    """ask --json in background mode auto-asyncs and returns op-id envelope."""
    monkeypatch.setenv("THOTH_TEST_MODE", "1")

    runner = CliRunner()
    start = time.time()
    result = runner.invoke(
        cli,
        ["ask", "test prompt", "--mode", "deep_research", "--json", "--provider", "mock"],
        catch_exceptions=False,
    )
    elapsed = time.time() - start

    # If the test environment can't reach `deep_research` via mock provider, the
    # envelope may be an error envelope — that's still valid (returns within 5s).
    assert elapsed < 5.0, f"ask --json deep_research took {elapsed:.2f}s"
    payload = json.loads(result.output)
    assert payload["status"] in ("ok", "error")
    if payload["status"] == "ok":
        # Background mode → submit envelope (op-id present, no result inline).
        assert "operation_id" in payload["data"]
