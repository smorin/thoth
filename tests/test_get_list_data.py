"""Category F — get_list_data unit tests."""

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
    # NOTE: NO "output_dir" key per OperationStatus field set
    (checkpoint_dir / f"{op.id}.json").write_text(json.dumps(payload))


def test_get_list_data_returns_dict_with_operations_list(checkpoint_dir):
    from thoth.commands import get_list_data

    op1 = make_operation("research-20260427-000000-aaaaaaaaaaaaaaaa", status="running")
    op2 = make_operation("research-20260427-000001-bbbbbbbbbbbbbbbb", status="completed")
    for op in (op1, op2):
        _write_checkpoint(checkpoint_dir, op)

    data = asyncio.run(get_list_data(show_all=True))
    assert isinstance(data, dict)
    assert "operations" in data
    assert isinstance(data["operations"], list)
    assert len(data["operations"]) == 2


def test_get_list_data_signature_excludes_as_json(isolated_thoth_home):
    from thoth.commands import get_list_data

    assert "as_json" not in inspect.signature(get_list_data).parameters


def test_get_list_data_filters_by_show_all_false(checkpoint_dir):
    from thoth.commands import get_list_data

    op_running = make_operation("research-20260427-000000-aaaaaaaaaaaaaaaa", status="running")
    _write_checkpoint(checkpoint_dir, op_running)

    data = asyncio.run(get_list_data(show_all=False))
    assert any(o["operation_id"] == op_running.id for o in data["operations"])
