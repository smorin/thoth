"""Category F — get_status_data unit tests (spec §6.6 pattern reference)."""

from __future__ import annotations

import asyncio
import inspect
import json
from pathlib import Path

from tests.conftest import make_operation


def _write_checkpoint(checkpoint_dir: Path, op) -> None:
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
        "error": None,
        "failure_type": None,
    }
    (checkpoint_dir / f"{op.id}.json").write_text(json.dumps(payload))


def test_get_status_data_returns_none_for_missing_operation(isolated_thoth_home, checkpoint_dir):
    from thoth.commands import get_status_data

    result = asyncio.run(get_status_data("not-a-real-op"))
    assert result is None


def test_get_status_data_returns_dict_for_existing_operation(checkpoint_dir):
    from thoth.commands import get_status_data

    op = make_operation("research-20260427-000000-aaaaaaaaaaaaaaaa", status="running")
    _write_checkpoint(checkpoint_dir, op)

    data = asyncio.run(get_status_data(op.id))
    assert isinstance(data, dict)
    assert data["operation_id"] == op.id
    assert data["status"] == "running"
    assert data["mode"] == "default"
    assert data["prompt"] == "test prompt"


def test_get_status_data_signature_excludes_as_json(isolated_thoth_home):
    """spec §7.2 critical invariant — `as_json` MUST NOT appear here."""
    from thoth.commands import get_status_data

    params = inspect.signature(get_status_data).parameters
    assert "as_json" not in params
