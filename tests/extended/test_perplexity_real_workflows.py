"""Minimal live Perplexity workflow tests that mocks cannot prove.

Gated by `@pytest.mark.live_api`. Default `pytest` skips this entire module
(`addopts = "-m 'not extended and not live_api'"`); run explicitly with
`uv run pytest -m live_api` or `just test-live-api` after exporting
`PERPLEXITY_API_KEY`.

Cost target: a few cents per full run (small ping prompts at search_context_size=low).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.extended.conftest import (
    assert_no_secret_leaked,
    run_thoth,
)

pytestmark = pytest.mark.live_api


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


def test_ext_pplx_imm_cli_api_key_flag_works_without_env(
    tmp_path: Path,
) -> None:
    """Live: --api-key-perplexity sk-... works without PERPLEXITY_API_KEY in env;
    the key never appears in stdout/stderr/logs."""
    import os

    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        pytest.skip("PERPLEXITY_API_KEY is required for this test")

    env = {k: v for k, v in os.environ.items() if k != "PERPLEXITY_API_KEY"}
    env.update(
        {
            "HOME": str(tmp_path / "home"),
            "XDG_CONFIG_HOME": str(tmp_path / "config"),
            "XDG_STATE_HOME": str(tmp_path / "state"),
            "XDG_CACHE_HOME": str(tmp_path / "cache"),
            "PYTHONUNBUFFERED": "1",
            "COLUMNS": "200",
        }
    )

    result, _elapsed = run_thoth(
        [
            "ask",
            "Reply in one short sentence.",
            "--mode",
            "perplexity_quick",
            "--provider",
            "perplexity",
            "--api-key-perplexity",
            api_key,
        ],
        env,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert api_key not in result.stdout
    assert api_key not in result.stderr
