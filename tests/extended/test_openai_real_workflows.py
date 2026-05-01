"""Minimal live OpenAI workflow tests that mocks cannot prove."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tests.extended.conftest import (
    assert_no_secret_leaked,
    cancel_background_operation,
    load_checkpoint,
    payload,
    run_thoth,
    wait_for_provider_job_id,
)

pytestmark = pytest.mark.extended

BACKGROUND_STATUSES = {"queued", "running", "completed"}


def _assert_submit_envelope(
    result: subprocess.CompletedProcess[str],
    elapsed: float,
    env: dict[str, str],
    *,
    max_elapsed: float = 30.0,
) -> str:
    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.lstrip().startswith("{")
    assert result.stdout.rstrip().endswith("}")
    assert_no_secret_leaked(result, env)

    envelope = payload(result)
    assert envelope["status"] == "ok"
    data = envelope["data"]
    assert data["status"] == "submitted"
    assert data["mode"] == "quick_research"
    assert data["provider"] == "openai"
    assert elapsed < max_elapsed

    operation_id = data["operation_id"]
    assert isinstance(operation_id, str)
    assert operation_id.startswith("research-")
    return operation_id


def _submit_background_json(
    env: dict[str, str],
    *,
    explicit_async: bool,
    prompt: str,
    extra_args: list[str] | None = None,
) -> tuple[str, subprocess.CompletedProcess[str], float]:
    args = [
        "ask",
        prompt,
        "--mode",
        "quick_research",
        "--provider",
        "openai",
    ]
    if explicit_async:
        args.append("--async")
    args.append("--json")
    if extra_args:
        args.extend(extra_args)

    result, elapsed = run_thoth(args, env, timeout=90)
    operation_id = _assert_submit_envelope(result, elapsed, env)
    return operation_id, result, elapsed


def _write_resume_config(config_path: Path, output_root: Path) -> None:
    config_path.write_text(
        f"""version = "2.0"

[paths]
base_output_dir = "{output_root}"

[execution]
poll_interval = 5
max_wait = 10
""",
        encoding="utf-8",
    )


def test_ext_oai_imm_stream_tee_writes_stdout_and_file(
    live_cli_env: tuple[dict[str, str], Path],
    tmp_path: Path,
) -> None:
    """EXT-OAI-IMM-STREAM-TEE: live immediate stream tees to stdout and file."""
    env, _state_root = live_cli_env
    target = tmp_path / "openai-stream-tee.md"

    result, elapsed = run_thoth(
        [
            "ask",
            "Reply in one short sentence confirming that live streaming tee output works.",
            "--mode",
            "thinking",
            "--provider",
            "openai",
            "--out",
            f"-,{target}",
        ],
        env,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert elapsed < 120
    assert_no_secret_leaked(result, env)
    assert result.stdout.strip()
    assert target.read_text(encoding="utf-8") == result.stdout


def test_ext_oai_bg_json_auto_async_submits_and_can_cancel(
    live_cli_env: tuple[dict[str, str], Path],
) -> None:
    """EXT-OAI-BG-JSON-AUTO-ASYNC: background ask --json auto-submits async."""
    env, state_root = live_cli_env
    operation_id: str | None = None
    try:
        operation_id, _result, _elapsed = _submit_background_json(
            env,
            explicit_async=False,
            prompt="Start a concise live background JSON auto-async probe.",
        )
        checkpoint = load_checkpoint(state_root, operation_id)
        assert checkpoint["status"] == "running"
        assert checkpoint["providers"]["openai"]["status"] in BACKGROUND_STATUSES
        assert wait_for_provider_job_id(state_root, operation_id)
    finally:
        cancel_background_operation(operation_id, env, state_root)


def test_ext_oai_bg_json_explicit_async_submits_and_can_cancel(
    live_cli_env: tuple[dict[str, str], Path],
) -> None:
    """EXT-OAI-BG-JSON-EXPLICIT-ASYNC: explicit --async --json submit works."""
    env, state_root = live_cli_env
    operation_id: str | None = None
    try:
        operation_id, _result, _elapsed = _submit_background_json(
            env,
            explicit_async=True,
            prompt="Start a concise live background JSON explicit-async probe.",
        )
        checkpoint = load_checkpoint(state_root, operation_id)
        assert checkpoint["status"] == "running"
        assert checkpoint["providers"]["openai"]["status"] in BACKGROUND_STATUSES
        assert wait_for_provider_job_id(state_root, operation_id)
    finally:
        cancel_background_operation(operation_id, env, state_root)


def test_ext_oai_bg_cancel_cmd_json_cancels_live_background_job(
    live_cli_env: tuple[dict[str, str], Path],
) -> None:
    """EXT-OAI-BG-CANCEL-CMD: user-facing cancel JSON works for live OpenAI."""
    env, state_root = live_cli_env
    operation_id: str | None = None
    try:
        operation_id, _result, _elapsed = _submit_background_json(
            env,
            explicit_async=False,
            prompt="Start a concise live background job for cancel command coverage.",
        )
        assert wait_for_provider_job_id(state_root, operation_id)

        cancel_result, cancel_elapsed = run_thoth(["cancel", operation_id, "--json"], env)
        assert cancel_result.returncode == 0, cancel_result.stderr + cancel_result.stdout
        assert cancel_elapsed < 45
        assert_no_secret_leaked(cancel_result, env)

        envelope = payload(cancel_result)
        assert envelope["status"] == "ok"
        data: dict[str, Any] = envelope["data"]
        assert data["operation_id"] == operation_id
        assert data["status"] in {"ok", "already_terminal"}
        if data["status"] == "ok":
            assert data["providers"]["openai"]["status"] in {"cancelled", "completed"}
        else:
            assert data["previous"] in {"completed", "cancelled", "failed"}

        checkpoint = load_checkpoint(state_root, operation_id)
        assert checkpoint["status"] in {"cancelled", "completed", "failed"}
        assert checkpoint["providers"]["openai"]["status"] in {"cancelled", "completed"}
    finally:
        cancel_background_operation(operation_id, env, state_root)


@pytest.mark.extended_slow
def test_ext_oai_bg_async_blocking_resume_complete_lifecycle(
    live_cli_env: tuple[dict[str, str], Path],
    tmp_path: Path,
) -> None:
    """EXT-OAI-BG-ASYNC-BLOCKING-RESUME-COMPLETE: async submit then blocking resume."""
    if os.environ.get("THOTH_EXTENDED_SLOW") != "1":
        pytest.skip("set THOTH_EXTENDED_SLOW=1 to run the completion lifecycle test")

    env, state_root = live_cli_env
    project = "extended-slow"
    output_root = tmp_path / "outputs"
    config_path = tmp_path / "thoth.config.toml"
    _write_resume_config(config_path, output_root)

    operation_id: str | None = None
    try:
        operation_id, _result, _elapsed = _submit_background_json(
            env,
            explicit_async=True,
            prompt=(
                "Run a very brief live research check. Return a compact paragraph "
                "with one concrete observation."
            ),
            extra_args=["--config", str(config_path), "--project", project],
        )

        resume_result, _resume_elapsed = run_thoth(
            ["resume", operation_id, "--config", str(config_path), "--quiet"],
            env,
            timeout=900,
        )
        assert resume_result.returncode == 0, resume_result.stderr + resume_result.stdout
        assert_no_secret_leaked(resume_result, env)

        checkpoint = load_checkpoint(state_root, operation_id)
        assert checkpoint["status"] == "completed"
        assert checkpoint["providers"]["openai"]["status"] == "completed"

        output_path = Path(checkpoint["output_paths"]["openai"])
        assert output_path.exists()
        assert output_path.parent == output_root / project
        assert list((output_root / project).glob("*_quick_research_openai_*.md")) == [output_path]

        text = output_path.read_text(encoding="utf-8")
        assert text.strip()
        assert f"operation_id: {operation_id}" in text
        assert "provider: openai" in text
        assert "mode: quick_research" in text
        assert "No content in response" not in text
    finally:
        cancel_background_operation(operation_id, env, state_root)
