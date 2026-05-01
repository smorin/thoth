"""P20: Live-API workflow regression suite.

Slim scope (TS03-TS08): real-API CLI behaviors that mocks cannot
catch — streaming, file output, append, no-metadata, secret
masking, and mismatch defense. Sibling to the `extended` marker
suite (`test_model_kind_runtime.py`, `test_openai_real_workflows.py`)
but distinct in cadence and purpose: this suite watches user-visible
CLI workflow drift, not model-kind contracts.

Gated by `@pytest.mark.live_api`; default `pytest` skips this
module via `addopts = "-m 'not extended and not live_api'"`. Run
explicitly with `just test-live-api` or weekly via
`.github/workflows/live-api.yml` (Saturday 7pm PDT).

Cost target: <$0.20 per full run (short prompts, single-shot
immediate streams, one no-HTTP test).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from tests.extended.conftest import (
    assert_metadata_absent,
    assert_no_secret_leaked,
    assert_nonempty_file,
    run_thoth,
)

pytestmark = pytest.mark.live_api


def test_immediate_streaming_smoke(
    live_cli_env: tuple[dict[str, str], Path],
) -> None:
    """P20-TS03: immediate `thoth ask` streams to stdout, no result file, no bg hints."""
    env, tmp_path = live_cli_env
    result, elapsed = run_thoth(
        [
            "ask",
            "Reply with the word ok.",
            "--mode",
            "thinking",
            "--provider",
            "openai",
        ],
        env,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert elapsed < 120
    assert_no_secret_leaked(result, env)
    assert result.stdout.strip(), "expected streamed output to stdout"

    # Immediate path skips background plumbing entirely.
    assert "Operation ID:" not in result.stdout
    assert "Resume with:" not in result.stdout

    # No project / no --out → no result file written under tmp_path.
    result_files = list(tmp_path.rglob("*.md"))
    assert not result_files, f"expected no result files, found {result_files}"


def test_immediate_out_file_writes_and_silences_stdout(
    live_cli_env: tuple[dict[str, str], Path],
    tmp_path,
) -> None:
    """P20-TS04: `--out FILE` writes non-empty file; stdout suppressed."""
    env, _state_root = live_cli_env
    target = tmp_path / "answer.md"
    result, _elapsed = run_thoth(
        [
            "ask",
            "Reply with the word ok.",
            "--mode",
            "thinking",
            "--provider",
            "openai",
            "--out",
            str(target),
        ],
        env,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert_no_secret_leaked(result, env)
    assert_nonempty_file(target)
    # Streamed answer goes to file, not stdout, when --out is the only sink.
    assert not result.stdout.strip(), (
        f"expected empty stdout when streaming to file; got: {result.stdout!r}"
    )


def test_append_grows_file_and_preserves_prefix(
    live_cli_env: tuple[dict[str, str], Path],
    tmp_path,
) -> None:
    """P20-TS05: `--append` grows the file; first run's prefix is preserved."""
    env, _state_root = live_cli_env
    target = tmp_path / "appended.md"
    cmd = [
        "ask",
        "Reply with one short word.",
        "--mode",
        "thinking",
        "--provider",
        "openai",
        "--out",
        str(target),
        "--append",
    ]

    r1, _ = run_thoth(cmd, env, timeout=120)
    assert r1.returncode == 0, r1.stderr + r1.stdout
    assert_no_secret_leaked(r1, env)
    assert_nonempty_file(target)
    size_after_first = target.stat().st_size
    prefix_after_first = target.read_bytes()

    r2, _ = run_thoth(cmd, env, timeout=120)
    assert r2.returncode == 0, r2.stderr + r2.stdout
    assert_no_secret_leaked(r2, env)
    size_after_second = target.stat().st_size
    assert size_after_second > size_after_first, "expected --append to grow the file"
    assert target.read_bytes().startswith(prefix_after_first), (
        "first run's content was lost — --append truncated instead of appending"
    )


def test_no_metadata_immediate_smoke(
    live_cli_env: tuple[dict[str, str], Path],
    tmp_path,
) -> None:
    """P20-TS06: `--no-metadata` is innocuous on the immediate `--out` path.

    Note: in immediate mode without `--project`, `OutputManager` is not
    invoked, so YAML metadata never appears in `--out` files regardless of
    this flag. This test asserts the flag doesn't break the path and locks
    in metadata-free output as a regression guard.
    """
    env, _state_root = live_cli_env
    target = tmp_path / "no-metadata.md"
    result, _ = run_thoth(
        [
            "ask",
            "Reply with one short word.",
            "--mode",
            "thinking",
            "--provider",
            "openai",
            "--out",
            str(target),
            "--no-metadata",
        ],
        env,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert_no_secret_leaked(result, env)
    assert_nonempty_file(target)
    assert_metadata_absent(target)


def test_cli_api_key_does_not_leak(
    live_cli_env: tuple[dict[str, str], Path],
) -> None:
    """P20-TS07: `--api-key-openai` works without env var and key not echoed."""
    env, _state_root = live_cli_env
    secret = env["OPENAI_API_KEY"]
    env_no_key = env.copy()
    env_no_key.pop("OPENAI_API_KEY", None)

    result, _ = run_thoth(
        [
            "ask",
            "Reply with the word ok.",
            "--mode",
            "thinking",
            "--provider",
            "openai",
            "--api-key-openai",
            secret,
        ],
        env_no_key,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip(), "expected streamed output to stdout"
    # `assert_no_secret_leaked` reads the secret from `env`; here we passed
    # `env_no_key` which has it stripped, so check explicitly.
    assert secret not in result.stdout, "API key leaked to stdout"
    assert secret not in result.stderr, "API key leaked to stderr"


def test_mismatch_defense_no_http(monkeypatch: pytest.MonkeyPatch) -> None:
    """P20-TS08: immediate-declared deep-research model raises pre-HTTP.

    Constructs a real `OpenAIProvider` with a deliberately mismatched
    `mode_config` (`kind="immediate"` but a background-only model) and asserts
    `submit()` raises `ModeKindMismatchError` synchronously. No HTTP call.

    Uses a fake API key for provider construction; the mismatch check
    fires before the key is ever sent to OpenAI.
    """
    from thoth.config import ConfigManager
    from thoth.errors import ModeKindMismatchError
    from thoth.models import KNOWN_MODELS
    from thoth.providers import create_provider

    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-mismatch-defense-key")

    bg_model = next(m.id for m in KNOWN_MODELS if m.provider == "openai" and m.kind == "background")
    cm = ConfigManager()
    cm.load_all_layers({})
    mode_config = {"provider": "openai", "model": bg_model, "kind": "immediate"}
    provider = create_provider("openai", cm, mode_config=mode_config)

    with pytest.raises(ModeKindMismatchError):
        asyncio.run(provider.submit("ping", mode="_mismatch_check_"))
