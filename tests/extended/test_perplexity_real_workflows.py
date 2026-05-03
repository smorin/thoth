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
