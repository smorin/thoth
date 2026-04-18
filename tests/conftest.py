"""Shared fixtures and VCR configuration for the pytest suite."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
import vcr

from thoth.config import ConfigManager
from thoth.models import OperationStatus
from thoth.paths import user_checkpoints_dir

CASSETTE_DIR = Path(__file__).resolve().parent.parent / "thoth_test_cassettes"

# Shared VCR instance:
# - record_mode="none": never make real HTTP requests
# - match_on=["uri", "method"]: ignore body differences between SDK-generated
#   requests (structured input_messages) and cassette bodies (plain strings)
thoth_vcr = vcr.VCR(
    record_mode="none",
    match_on=["uri", "method"],
)


@pytest.fixture
def isolated_thoth_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Per-test XDG_* roots so config/state/cache never hit the real user dir."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    return tmp_path


@pytest.fixture
def checkpoint_dir(isolated_thoth_home: Path) -> Path:
    """Thoth's checkpoint directory under the isolated test state dir."""
    path = user_checkpoints_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture
def stub_config() -> ConfigManager:
    """ConfigManager with defaults loaded — matches the _stub_config() helper
    duplicated across test_app_context.py / test_provider_registry.py /
    test_api_key_resolver.py.
    """
    cm = ConfigManager()
    cm.load_all_layers({})
    return cm


@pytest.fixture
def mock_operation() -> OperationStatus:
    """An OperationStatus with pinned id/timestamps for deterministic assertions."""
    now = datetime(2026, 4, 16, 0, 0, 0)
    return OperationStatus(
        id="research-20260416-000000-0000000000000000",
        prompt="test prompt",
        mode="default",
        status="queued",
        created_at=now,
        updated_at=now,
    )


def make_operation(op_id: str, **overrides: Any) -> OperationStatus:
    """Factory for one-off OperationStatus values inside a test."""
    now = datetime(2026, 4, 16, 0, 0, 0)
    defaults: dict[str, Any] = {
        "id": op_id,
        "prompt": "test prompt",
        "mode": "default",
        "status": "queued",
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return OperationStatus(**defaults)
