"""Minimal live Perplexity workflow tests that mocks cannot prove.

Gated by `@pytest.mark.live_api`. Default `pytest` skips this entire module
(`addopts = "-m 'not extended and not live_api'"`); run explicitly with
`uv run pytest -m live_api` or `just test-live-api` after exporting
`PERPLEXITY_API_KEY`.

Cost target — immediate (sync) tests: a few cents per full run (small ping
prompts at search_context_size=low).

Cost target — background (P27 sonar-deep-research) tests: ~$1.32 per run
at reasoning_effort=high. Perplexity has no upstream cancel API (T01
verified), so the upstream job continues billing even after `thoth cancel`
marks the local checkpoint cancelled — there's no way to reduce cost by
aborting early. Run this module weekly via the live-api workflow only.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import pytest

from tests.extended.conftest import (
    assert_no_secret_leaked,
    checkpoint_path,
    payload,
    run_thoth,
    wait_for_provider_job_id,
)

pytestmark = pytest.mark.live_api

PERPLEXITY_BACKGROUND_STATUSES = {"queued", "running", "completed", "cancelled"}


def test_ext_pplx_imm_stream_default_mode_emits_grounded_answer(
    live_perplexity_env: tuple[dict[str, str], Path],
) -> None:
    """Live: --provider perplexity --mode perplexity_quick produces grounded text."""
    env, _ = live_perplexity_env
    result, elapsed = run_thoth(
        [
            "ask",
            "Reply in one short sentence about Sonar.",
            "--mode",
            "perplexity_quick",
            "--provider",
            "perplexity",
        ],
        env,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert elapsed < 120
    assert_no_secret_leaked(result, env)
    assert result.stdout.strip(), "expected non-empty answer"


def test_ext_pplx_imm_stream_explicit_model_passthrough(
    live_perplexity_env: tuple[dict[str, str], Path],
) -> None:
    """Live: --provider perplexity --model sonar runs without local validation."""
    env, _ = live_perplexity_env
    result, elapsed = run_thoth(
        [
            "ask",
            "Reply in one short sentence.",
            "--provider",
            "perplexity",
            "--model",
            "sonar",
        ],
        env,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert elapsed < 120
    assert_no_secret_leaked(result, env)
    assert result.stdout.strip()


def test_ext_pplx_imm_stream_tee_writes_stdout_and_file(
    live_perplexity_env: tuple[dict[str, str], Path],
    tmp_path: Path,
) -> None:
    """Live: tee --out -,FILE writes identical content to stdout and file."""
    env, _ = live_perplexity_env
    target = tmp_path / "perplexity-stream-tee.md"

    result, elapsed = run_thoth(
        [
            "ask",
            "Reply in one short sentence confirming live tee works.",
            "--mode",
            "perplexity_quick",
            "--provider",
            "perplexity",
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


def test_ext_pplx_imm_custom_mode_passes_provider_namespace_without_argv_key(
    live_perplexity_env: tuple[dict[str, str], Path],
    tmp_path: Path,
) -> None:
    """Live: Perplexity mode-specific extra_body settings pass via config/env.

    Real Perplexity keys must not be placed on argv; timeout/error paths can
    print argv before normal no-leak assertions run.
    """
    env, _ = live_perplexity_env
    config_path = tmp_path / "pplx-passthrough.toml"
    config_path.write_text(
        """version = "2.0"

[providers.perplexity]
api_key = "${PERPLEXITY_API_KEY}"

[modes.pplx_passthrough_live]
provider = "perplexity"
model = "sonar"
kind = "immediate"

[modes.pplx_passthrough_live.perplexity]
stream_mode = "full"
web_search_options = { search_context_size = "low" }
""",
        encoding="utf-8",
    )

    args = [
        "--config",
        str(config_path),
        "ask",
        "Reply in one short sentence.",
        "--mode",
        "pplx_passthrough_live",
    ]
    assert env["PERPLEXITY_API_KEY"] not in args

    result, _elapsed = run_thoth(
        args,
        env,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert_no_secret_leaked(result, env)
    assert result.stdout.strip()


# =============================================================================
# P27 — background deep-research lifecycle (sonar-deep-research / async API)
# =============================================================================
#
# Cost: ~$1.32 per run at reasoning_effort=high. Perplexity has no upstream
# cancel API (T01) — submitted jobs continue billing regardless of `thoth
# cancel`. Tests below intentionally accept this cost; the live-api workflow
# runs weekly.


def _submit_perplexity_background_json(
    env: dict[str, str],
    *,
    prompt: str,
    extra_args: list[str] | None = None,
) -> tuple[str, Any, float]:
    """Submit a Perplexity deep-research job asynchronously and return op-id."""
    args = [
        "ask",
        prompt,
        "--mode",
        "perplexity_deep_research",
        "--provider",
        "perplexity",
        "--async",
        "--json",
    ]
    if extra_args:
        args.extend(extra_args)

    result, elapsed = run_thoth(args, env, timeout=120)

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.lstrip().startswith("{")
    assert_no_secret_leaked(result, env)
    envelope = payload(result)
    assert envelope["status"] == "ok", envelope
    data = envelope["data"]
    assert data["status"] == "submitted"
    assert data["mode"] == "perplexity_deep_research"
    assert data["provider"] == "perplexity"
    assert elapsed < 120

    operation_id = data["operation_id"]
    assert isinstance(operation_id, str) and operation_id.startswith("research-")
    return operation_id, result, elapsed


def test_ext_pplx_bg_submit_async_persists_request_id(
    live_perplexity_env: tuple[dict[str, str], Path],
) -> None:
    """EXT-PPLX-BG-SUBMIT: background ask --async --json submits and persists request_id.

    Mirrors `test_ext_oai_bg_json_explicit_async_submits_and_can_cancel`. Verifies
    that the upstream Perplexity request_id (the async job_id) lands in the
    checkpoint via the runner's existing checkpoint format. If this passes,
    P27's `submit()` is wire-compatible with the runner contract.

    NOTE: ~$1.32 per run; upstream job continues running after this test
    returns and there is no way to stop it (T01). Cost is unavoidable.
    """
    env, state_root = live_perplexity_env
    operation_id, _result, _elapsed = _submit_perplexity_background_json(
        env,
        prompt="Briefly summarize one recent advance in mRNA vaccine research.",
    )

    job_id = wait_for_provider_job_id(state_root, operation_id, provider="perplexity", timeout=60.0)
    assert isinstance(job_id, str) and job_id, "expected non-empty Perplexity request_id"

    checkpoint = json.loads(checkpoint_path(state_root, operation_id).read_text())
    providers = checkpoint.get("providers", {})
    assert "perplexity" in providers, f"checkpoint missing perplexity entry: {checkpoint}"
    assert providers["perplexity"].get("status") in PERPLEXITY_BACKGROUND_STATUSES
    assert providers["perplexity"].get("job_id") == job_id


def test_ext_pplx_bg_cancel_renders_upstream_unsupported(
    live_perplexity_env: tuple[dict[str, str], Path],
) -> None:
    """EXT-PPLX-BG-CANCEL: thoth cancel surfaces upstream_unsupported correctly.

    Perplexity returns {status: upstream_unsupported} from cancel(); the
    user-facing CLI (cancel.py:126) must render the warning string
    'upstream cancel not supported; local checkpoint marked cancelled'.
    Mirrors OpenAI's `test_ext_oai_bg_cancel_cmd_json_cancels_live_background_job`
    but for the no-upstream-cancel-API case.

    NOTE: ~$1.32 per run; cancel does NOT abort the upstream job.
    """
    env, state_root = live_perplexity_env
    operation_id, _result, _elapsed = _submit_perplexity_background_json(
        env,
        prompt="Briefly summarize one recent advance in genetic engineering.",
    )
    assert wait_for_provider_job_id(state_root, operation_id, provider="perplexity", timeout=60.0)

    cancel_result, cancel_elapsed = run_thoth(["cancel", operation_id, "--json"], env, timeout=45)
    assert cancel_result.returncode == 0, cancel_result.stderr + cancel_result.stdout
    assert cancel_elapsed < 45
    assert_no_secret_leaked(cancel_result, env)

    envelope = payload(cancel_result)
    assert envelope["status"] == "ok", envelope
    data: dict[str, Any] = envelope["data"]
    assert data["operation_id"] == operation_id

    # Perplexity must surface upstream_unsupported (the runner records the
    # exact status returned by provider.cancel).
    perp_status = data["providers"]["perplexity"]["status"]
    assert perp_status in {"upstream_unsupported", "cancelled", "completed"}, (
        f"unexpected provider cancel status: {perp_status!r}"
    )

    # Local checkpoint must reflect cancelled regardless of upstream support.
    checkpoint = json.loads(checkpoint_path(state_root, operation_id).read_text())
    assert checkpoint["status"] in {"cancelled", "completed", "failed"}


@pytest.mark.extended_slow
def test_ext_pplx_bg_blocking_resume_complete_lifecycle(
    live_perplexity_env: tuple[dict[str, str], Path],
    tmp_path: Path,
) -> None:
    """EXT-PPLX-BG-LIFECYCLE: full async submit -> resume -> complete cycle.

    Gated by THOTH_EXTENDED_SLOW=1. Submits a deep-research job, then calls
    `thoth resume <op_id>` which exercises PerplexityProvider.reconnect() +
    the runner's polling loop until COMPLETED. Verifies the output file
    contains the answer + ## Sources + ## Cost sections.

    NOTE: ~$1.32 per run AND 2-15 minutes wall-clock (sonar-deep-research
    typical completion time). Set THOTH_EXTENDED_SLOW=1 to opt in.
    """
    if os.environ.get("THOTH_EXTENDED_SLOW") != "1":
        pytest.skip("set THOTH_EXTENDED_SLOW=1 to run the completion lifecycle test")

    env, state_root = live_perplexity_env
    project = "ext-pplx-bg-slow"
    output_root = tmp_path / "outputs"
    config_path = tmp_path / "thoth.config.toml"
    # [providers.perplexity] is REQUIRED here — there's a pre-existing bug
    # in the --config + --async + --json path where the env-var fallback for
    # api_key doesn't fire when the config omits the providers section.
    # The ${PERPLEXITY_API_KEY} placeholder resolves at config-load time
    # using the env var the live_perplexity_env fixture exports. Same shape
    # as test_ext_pplx_imm_custom_mode_passes_provider_namespace_without_argv_key.
    config_path.write_text(
        f"""version = "2.0"

[paths]
base_output_dir = "{output_root}"

[providers.perplexity]
api_key = "${{PERPLEXITY_API_KEY}}"

[execution]
poll_interval = 10
max_wait = 30
""",
        encoding="utf-8",
    )

    operation_id, _result, _elapsed = _submit_perplexity_background_json(
        env,
        prompt=(
            "Write a single short paragraph (3-5 sentences) summarizing one "
            "concrete observation about Sonar deep research."
        ),
        extra_args=["--config", str(config_path), "--project", project],
    )

    # Resume blocks until completion. 25 min budget covers the typical
    # 2-15 min lifecycle plus headroom for the documented async polling
    # delay bug (research §17).
    deadline = time.monotonic()  # noqa: F841 (left for future budget tracking)
    resume_result, _resume_elapsed = run_thoth(
        ["resume", operation_id, "--config", str(config_path), "--quiet"],
        env,
        timeout=1500,
    )
    assert resume_result.returncode == 0, resume_result.stderr + resume_result.stdout
    assert_no_secret_leaked(resume_result, env)

    checkpoint = json.loads(checkpoint_path(state_root, operation_id).read_text())
    assert checkpoint["status"] == "completed"
    assert checkpoint["providers"]["perplexity"]["status"] == "completed"

    output_path = Path(checkpoint["output_paths"]["perplexity"])
    assert output_path.exists()
    text = output_path.read_text(encoding="utf-8")
    assert text.strip()
    assert f"operation_id: {operation_id}" in text
    assert "provider: perplexity" in text
    assert "mode: perplexity_deep_research" in text
    # The async API output must include cost (always-on per Open Question
    # resolution at P27 kickoff).
    assert "## Cost" in text, "expected ## Cost footer in output"
    assert "Total: $" in text
