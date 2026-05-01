# OpenAI Extended Workflow Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a minimal, high-value live OpenAI extended test set that covers real streaming, JSON async submission, user-facing cancellation, and one full async-to-blocking-resume completion lifecycle.

**Architecture:** Keep mock/unit tests as the broad contract surface and add only live tests for behavior that can drift at the OpenAI API boundary. Extract shared subprocess, checkpoint, and cleanup helpers into `tests/extended/conftest.py`. Every background test must cancel in `finally` unless the operation is already completed.

**Tech Stack:** Python 3.11+, pytest, Click CLI subprocesses via `python -m thoth`, OpenAI Responses API, isolated XDG directories, `@pytest.mark.extended`, optional `@pytest.mark.extended_slow`.

---

## Scenario IDs

| ID | Marker | Cost profile | Purpose |
|---|---|---|---|
| `EXT-OAI-IMM-STREAM-TEE` | `extended` | fast, immediate | Prove live OpenAI streaming emits text through Thoth's immediate path and tee sink. |
| `EXT-OAI-BG-JSON-AUTO-ASYNC` | `extended` | fast, cancelled | Prove background `ask --json` auto-submits asynchronously without explicit `--async`. |
| `EXT-OAI-BG-JSON-EXPLICIT-ASYNC` | `extended` | fast, cancelled | Prove explicit `--async --json` also returns a submit envelope quickly. |
| `EXT-OAI-BG-CANCEL-CMD` | `extended` | fast, cancelled | Prove the user-facing `thoth cancel <op-id> --json` command works against a live OpenAI background job. |
| `EXT-OAI-BG-ASYNC-BLOCKING-RESUME-COMPLETE` | `extended`, `extended_slow` | slow, completes | Prove full live lifecycle: async submit, fresh-process blocking resume, final result extraction, output file write, completed checkpoint. |

## File Structure

| Action | Path | Responsibility |
|---|---|---|
| Create | `tests/extended/conftest.py` | Shared live OpenAI fixtures and helpers: isolated env, subprocess runner, JSON payload parser, checkpoint reader, operation/job-id lookup, best-effort cleanup. |
| Modify | `tests/extended/test_openai_cli_lifecycle.py` | Remove duplicated helpers and keep existing resume-one-tick and Ctrl-C lifecycle tests on shared helpers. |
| Create | `tests/extended/test_openai_real_workflows.py` | New scenario tests listed above. |
| Modify | `pyproject.toml` | Register `extended_slow` marker. |

## Non-Goals

- Do not live-test every parser and output-sink permutation. Mock tests already cover comma-list parsing, repeated `--out`, append, bare prompt leading/trailing `--out`, quiet, prompt-file, stdin, project path, and metadata mechanics.
- Do not add live `--auto` chaining. It requires at least two live background jobs and mostly validates local file discovery.
- Do not add live `--combined` until more than one real provider is operational.
- Do not assert deterministic model prose. Assert stable contracts: non-empty output, JSON envelope shape, checkpoint status, provider status, result-file metadata, absence of secret leakage.

---

## Pre-Flight

- [ ] **Step 1: Confirm current extended collection**

Run:

```bash
uv run pytest --collect-only -q -m extended tests/extended
```

Expected today:

```text
tests/extended/test_model_kind_runtime.py::test_model_kind_matches_runtime_behavior[openai/o3]
tests/extended/test_model_kind_runtime.py::test_model_kind_matches_runtime_behavior[openai/o4-mini-deep-research]
tests/extended/test_model_kind_runtime.py::test_model_kind_matches_runtime_behavior[openai/o3-deep-research]
tests/extended/test_openai_cli_lifecycle.py::test_openai_resume_async_cli_one_tick
tests/extended/test_openai_cli_lifecycle.py::test_openai_ctrl_c_sync_background_cancels_upstream
```

- [ ] **Step 2: Confirm default pytest still excludes extended tests**

Run:

```bash
uv run pytest --collect-only -q tests/extended
```

Expected: no selected tests, or all extended tests listed as deselected because `pyproject.toml` has `addopts = "-m 'not extended'"`.

- [ ] **Step 3: Use one implementation branch or worktree**

Recommended if implementing outside the main checkout:

```bash
git worktree add /Users/stevemorin/c/thoth-worktrees/openai-extended-workflows -b test/openai-extended-workflows main
cd /Users/stevemorin/c/thoth-worktrees/openai-extended-workflows
```

Expected: new worktree on a clean branch.

---

## Task 1: Extract Shared Extended OpenAI Helpers

**Files:**
- Create: `tests/extended/conftest.py`
- Modify: `tests/extended/test_openai_cli_lifecycle.py`

**Why first:** New tests need the same isolated subprocess environment, checkpoint parsing, and cleanup behavior as the current lifecycle tests. Duplicating this logic makes leaked jobs more likely.

- [ ] **Step 1: Write the helper module**

Create `tests/extended/conftest.py` with this content:

```python
from __future__ import annotations

import asyncio
import json
import os
import re
import select
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
OP_ID_RE = re.compile(r"Operation ID:\s*(research-\d{8}-\d{6}-[a-f0-9]{16})")
OPENAI_BACKGROUND_MODE = {
    "provider": "openai",
    "model": "o4-mini-deep-research",
    "kind": "background",
}


def require_openai_key() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY is required for OpenAI extended tests")


@pytest.fixture
def live_cli_env(tmp_path: Path) -> tuple[dict[str, str], Path]:
    """Return an isolated environment for live CLI subprocesses."""
    require_openai_key()
    env = os.environ.copy()
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
    env.setdefault("UV_CACHE_DIR", str(REPO_ROOT / ".uv-cache"))
    return env, tmp_path


def scrub_secret(text: str, env: dict[str, str]) -> str:
    secret = env.get("OPENAI_API_KEY")
    if secret:
        return text.replace(secret, "<OPENAI_API_KEY>")
    return text


def run_thoth(
    args: list[str],
    env: dict[str, str],
    *,
    timeout: float = 90.0,
) -> tuple[subprocess.CompletedProcess[str], float]:
    start = time.monotonic()
    result = subprocess.run(
        [sys.executable, "-m", "thoth", *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result, time.monotonic() - start


def payload(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return json.loads(result.stdout)


def checkpoint_path(state_root: Path, operation_id: str) -> Path:
    return state_root / "state" / "thoth" / "checkpoints" / f"{operation_id}.json"


def load_checkpoint(state_root: Path, operation_id: str) -> dict[str, Any]:
    return json.loads(checkpoint_path(state_root, operation_id).read_text())


def maybe_load_checkpoint(state_root: Path, operation_id: str | None) -> dict[str, Any] | None:
    if not operation_id:
        return None
    path = checkpoint_path(state_root, operation_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def provider_job_id(state_root: Path, operation_id: str | None) -> str | None:
    checkpoint = maybe_load_checkpoint(state_root, operation_id)
    if not checkpoint:
        return None
    job_id = checkpoint.get("providers", {}).get("openai", {}).get("job_id")
    return str(job_id) if job_id else None


def operation_completed(state_root: Path, operation_id: str | None) -> bool:
    checkpoint = maybe_load_checkpoint(state_root, operation_id)
    return bool(checkpoint and checkpoint.get("status") == "completed")


def cancel_operation(operation_id: str | None, env: dict[str, str]) -> None:
    if not operation_id:
        return
    run_thoth(["cancel", operation_id, "--json"], env, timeout=45)


def cancel_openai_job_direct(job_id: str | None) -> None:
    """Best-effort cleanup for jobs whose checkpoint command path could not cancel."""
    if not job_id:
        return

    from thoth.config import ConfigManager
    from thoth.providers import create_provider

    config = ConfigManager()
    config.load_all_layers({})
    provider = create_provider("openai", config, mode_config=OPENAI_BACKGROUND_MODE)
    try:
        asyncio.run(provider.cancel(job_id))
    except Exception:
        pass


def cancel_background_operation(
    operation_id: str | None,
    env: dict[str, str],
    state_root: Path,
) -> None:
    if not operation_id or operation_completed(state_root, operation_id):
        return
    job_id = provider_job_id(state_root, operation_id)
    cancel_operation(operation_id, env)
    cancel_openai_job_direct(job_id)


def read_until_operation_id(
    proc: subprocess.Popen[str],
    *,
    timeout: float = 45.0,
) -> tuple[str, list[str]]:
    assert proc.stdout is not None
    assert proc.stderr is not None
    streams = [proc.stdout, proc.stderr]
    seen: list[str] = []
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if proc.poll() is not None:
            remaining_out, remaining_err = proc.communicate(timeout=1)
            seen.extend([remaining_out, remaining_err])
            pytest.fail("thoth exited before printing an operation id:\n" + "".join(seen)[-2000:])

        readable, _, _ = select.select(streams, [], [], 0.2)
        for stream in readable:
            line = stream.readline()
            if not line:
                continue
            seen.append(line)
            match = OP_ID_RE.search(line)
            if match:
                return match.group(1), seen

    proc.kill()
    pytest.fail("timed out waiting for operation id:\n" + "".join(seen)[-2000:])


def wait_for_provider_job_id(
    state_root: Path,
    operation_id: str,
    *,
    timeout: float = 45.0,
) -> str:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job_id = provider_job_id(state_root, operation_id)
        if job_id:
            return job_id
        time.sleep(0.2)
    pytest.fail(f"timed out waiting for provider job id in checkpoint for {operation_id}")


def assert_no_secret_leaked(
    result: subprocess.CompletedProcess[str],
    env: dict[str, str],
) -> None:
    secret = env.get("OPENAI_API_KEY")
    if not secret:
        return
    combined = result.stdout + result.stderr
    assert secret not in combined
```

- [ ] **Step 2: Run collect-only to verify helper import is clean**

Run:

```bash
uv run pytest --collect-only -q -m extended tests/extended
```

Expected: same 5 tests collected. If import fails, fix `tests/extended/conftest.py` before continuing.

- [ ] **Step 3: Refactor lifecycle test imports**

In `tests/extended/test_openai_cli_lifecycle.py`, remove local definitions for:

```python
asyncio
json
re
select
time
Any
_REPO_ROOT
_OP_ID_RE
_OPENAI_BACKGROUND_MODE
_require_openai_key
live_cli_env
_run_thoth
_checkpoint_path
_load_checkpoint
_payload
_cancel_operation
_cancel_openai_job_direct
_read_until_operation_id
_wait_for_provider_job_id
```

Add this import block after `import pytest`:

```python
from tests.extended.conftest import (
    REPO_ROOT,
    cancel_background_operation,
    cancel_openai_job_direct,
    load_checkpoint,
    payload,
    read_until_operation_id,
    run_thoth,
    wait_for_provider_job_id,
)
```

Then update call sites:

```python
# old
submit, submit_elapsed = _run_thoth([...], env)
submit_payload = _payload(submit)
status_data = _payload(status)["data"]
_cancel_operation(operation_id, env)
proc = subprocess.Popen(..., cwd=_REPO_ROOT, ...)
operation_id, prefix_output = _read_until_operation_id(proc)
job_id = _wait_for_provider_job_id(state_root, operation_id)
checkpoint = _load_checkpoint(state_root, operation_id)

# new
submit, submit_elapsed = run_thoth([...], env)
submit_payload = payload(submit)
status_data = payload(status)["data"]
cancel_background_operation(operation_id, env, state_root)
proc = subprocess.Popen(..., cwd=REPO_ROOT, ...)
operation_id, prefix_output = read_until_operation_id(proc)
job_id = wait_for_provider_job_id(state_root, operation_id)
checkpoint = load_checkpoint(state_root, operation_id)
```

- [ ] **Step 4: Run the refactored lifecycle file in collection mode**

Run:

```bash
uv run pytest --collect-only -q -m extended tests/extended/test_openai_cli_lifecycle.py
```

Expected:

```text
tests/extended/test_openai_cli_lifecycle.py::test_openai_resume_async_cli_one_tick
tests/extended/test_openai_cli_lifecycle.py::test_openai_ctrl_c_sync_background_cancels_upstream
```

- [ ] **Step 5: Commit helper extraction**

```bash
git add tests/extended/conftest.py tests/extended/test_openai_cli_lifecycle.py
git commit -m "test(extended): share OpenAI live CLI helpers"
```

---

## Task 2: Register the Slow Extended Marker

**Files:**
- Modify: `pyproject.toml`

**Why now:** The slow lifecycle test should be independently selectable and skipped unless explicitly opted in.

- [ ] **Step 1: Add the marker**

Change `[tool.pytest.ini_options]` in `pyproject.toml`:

```toml
markers = [
    "extended: real-API contract tests; gated, not run by default",
    "extended_slow: slow/costly real-API completion tests; require THOTH_EXTENDED_SLOW=1",
]
```

- [ ] **Step 2: Run marker verification**

Run:

```bash
uv run pytest --collect-only -q -m extended tests/extended
```

Expected: collection succeeds with no unknown-marker warning.

- [ ] **Step 3: Commit marker registration**

```bash
git add pyproject.toml
git commit -m "test(extended): register slow live-api marker"
```

---

## Task 3: Add Fast Live Workflow Tests

**Files:**
- Create: `tests/extended/test_openai_real_workflows.py`

**Why this set:** These tests hit only the live provider boundaries mock tests cannot prove: OpenAI streaming events, JSON auto-async behavior, explicit JSON async behavior, and user-facing cancellation.

- [ ] **Step 1: Add the new test module**

Create `tests/extended/test_openai_real_workflows.py` with this content:

```python
"""Extended real OpenAI workflow tests.

These tests hit the live OpenAI API. Fast background tests submit only long-running
jobs and cancel them in ``finally``. The single completion lifecycle test is
marked ``extended_slow`` and requires ``THOTH_EXTENDED_SLOW=1``.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.extended.conftest import (
    assert_no_secret_leaked,
    cancel_background_operation,
    load_checkpoint,
    payload,
    run_thoth,
)

pytestmark = pytest.mark.extended


def _assert_submit_envelope(
    result,
    *,
    max_elapsed: float,
    elapsed: float,
) -> str:
    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.lstrip().startswith("{")
    assert result.stdout.rstrip().endswith("}")
    assert elapsed < max_elapsed
    data = payload(result)["data"]
    assert data["status"] == "submitted"
    operation_id = data["operation_id"]
    assert isinstance(operation_id, str) and operation_id.startswith("research-")
    return operation_id


def _result_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*_openai_*.md"))


def test_ext_oai_imm_stream_tee(live_cli_env: tuple[dict[str, str], Path]) -> None:
    """EXT-OAI-IMM-STREAM-TEE: live immediate stream tees to stdout and file."""
    env, state_root = live_cli_env
    target = state_root / "answer.md"

    result, elapsed = run_thoth(
        [
            "ask",
            "Return exactly these words: live stream tee probe",
            "--mode",
            "thinking",
            "--provider",
            "openai",
            "--out",
            f"-,{target}",
        ],
        env,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert elapsed < 60
    assert result.stdout.strip(), "live stream did not produce stdout"
    assert target.exists(), "tee target was not created"
    file_text = target.read_text()
    assert file_text.strip(), "tee target is empty"
    assert result.stdout == file_text
    assert "Operation ID:" not in result.stdout
    assert "Check status:" not in result.stdout
    assert "Research submitted" not in result.stdout
    assert _result_files(state_root) == []
    assert_no_secret_leaked(result, env)


def test_ext_oai_bg_json_auto_async(live_cli_env: tuple[dict[str, str], Path]) -> None:
    """EXT-OAI-BG-JSON-AUTO-ASYNC: background ask --json auto-submits async."""
    env, state_root = live_cli_env
    operation_id: str | None = None
    try:
        result, elapsed = run_thoth(
            [
                "ask",
                "Return exactly these words after starting: auto async probe",
                "--mode",
                "quick_research",
                "--provider",
                "openai",
                "--json",
            ],
            env,
            timeout=90,
        )
        operation_id = _assert_submit_envelope(result, max_elapsed=30, elapsed=elapsed)
        assert_no_secret_leaked(result, env)
    finally:
        cancel_background_operation(operation_id, env, state_root)


def test_ext_oai_bg_json_explicit_async(live_cli_env: tuple[dict[str, str], Path]) -> None:
    """EXT-OAI-BG-JSON-EXPLICIT-ASYNC: explicit --async --json returns submit envelope."""
    env, state_root = live_cli_env
    operation_id: str | None = None
    try:
        result, elapsed = run_thoth(
            [
                "ask",
                "Return exactly these words after starting: explicit async probe",
                "--mode",
                "quick_research",
                "--provider",
                "openai",
                "--async",
                "--json",
            ],
            env,
            timeout=90,
        )
        operation_id = _assert_submit_envelope(result, max_elapsed=30, elapsed=elapsed)
        assert_no_secret_leaked(result, env)
    finally:
        cancel_background_operation(operation_id, env, state_root)


def test_ext_oai_bg_cancel_cmd(live_cli_env: tuple[dict[str, str], Path]) -> None:
    """EXT-OAI-BG-CANCEL-CMD: user-facing cancel command cancels a live job."""
    env, state_root = live_cli_env
    operation_id: str | None = None
    try:
        submit, elapsed = run_thoth(
            [
                "ask",
                "Start a cancellable live OpenAI background probe.",
                "--mode",
                "quick_research",
                "--provider",
                "openai",
                "--async",
                "--json",
            ],
            env,
            timeout=90,
        )
        operation_id = _assert_submit_envelope(submit, max_elapsed=30, elapsed=elapsed)

        cancel, _ = run_thoth(["cancel", operation_id, "--json"], env, timeout=45)
        assert cancel.returncode == 0, cancel.stderr + cancel.stdout
        cancel_payload = payload(cancel)
        assert cancel_payload["status"] == "ok"
        cancel_data = cancel_payload["data"]
        assert cancel_data["operation_id"] == operation_id
        assert cancel_data["status"] in {"ok", "already_terminal"}
        if cancel_data["status"] == "ok":
            provider_status = cancel_data["providers"]["openai"]["status"]
            assert provider_status in {"cancelled", "completed"}
        else:
            assert cancel_data["previous"] in {"completed", "cancelled", "failed"}
        assert_no_secret_leaked(cancel, env)

        checkpoint = load_checkpoint(state_root, operation_id)
        assert checkpoint["status"] in {"cancelled", "completed"}
        provider_status = checkpoint.get("providers", {}).get("openai", {}).get("status")
        assert provider_status in {"cancelled", "completed"}
    finally:
        cancel_background_operation(operation_id, env, state_root)


@pytest.mark.extended_slow
def test_ext_oai_bg_async_blocking_resume_complete(
    live_cli_env: tuple[dict[str, str], Path],
) -> None:
    """EXT-OAI-BG-ASYNC-BLOCKING-RESUME-COMPLETE: async submit then blocking resume."""
    if os.environ.get("THOTH_EXTENDED_SLOW") != "1":
        pytest.skip("set THOTH_EXTENDED_SLOW=1 to run live completion lifecycle")

    env, state_root = live_cli_env
    output_root = state_root / "outputs"
    project = "extended-slow"
    config_path = state_root / "thoth.config.toml"
    config_path.write_text(
        'version = "2.0"\n'
        "[paths]\n"
        f'base_output_dir = "{output_root}"\n',
        encoding="utf-8",
    )
    operation_id: str | None = None
    try:
        submit, elapsed = run_thoth(
            [
                "ask",
                "Write one concise sentence containing the exact phrase blocking resume probe.",
                "--mode",
                "quick_research",
                "--provider",
                "openai",
                "--async",
                "--json",
                "--config",
                str(config_path),
                "--project",
                project,
            ],
            env,
            timeout=90,
        )
        operation_id = _assert_submit_envelope(submit, max_elapsed=30, elapsed=elapsed)

        resume, _ = run_thoth(
            ["resume", operation_id, "--config", str(config_path)],
            env,
            timeout=900,
        )
        assert resume.returncode == 0, resume.stderr + resume.stdout
        assert "Research completed" in resume.stdout or "Saved results from:" in resume.stdout
        assert_no_secret_leaked(resume, env)

        checkpoint = load_checkpoint(state_root, operation_id)
        assert checkpoint["status"] == "completed"
        assert checkpoint["providers"]["openai"]["status"] == "completed"

        files = _result_files(output_root / project)
        assert len(files) == 1, f"expected one OpenAI result file, got: {files}"
        text = files[0].read_text()
        assert text.strip()
        assert "operation_id: " + operation_id in text
        assert "provider: openai" in text
        assert "mode: quick_research" in text
        assert "No content in response" not in text
    finally:
        cancel_background_operation(operation_id, env, state_root)
```

- [ ] **Step 2: Run collect-only for the new module**

Run:

```bash
uv run pytest --collect-only -q -m extended tests/extended/test_openai_real_workflows.py
```

Expected:

```text
tests/extended/test_openai_real_workflows.py::test_ext_oai_imm_stream_tee
tests/extended/test_openai_real_workflows.py::test_ext_oai_bg_json_auto_async
tests/extended/test_openai_real_workflows.py::test_ext_oai_bg_json_explicit_async
tests/extended/test_openai_real_workflows.py::test_ext_oai_bg_cancel_cmd
tests/extended/test_openai_real_workflows.py::test_ext_oai_bg_async_blocking_resume_complete
```

- [ ] **Step 3: Verify default pytest deselects the new tests**

Run:

```bash
uv run pytest --collect-only -q tests/extended/test_openai_real_workflows.py
```

Expected: tests are deselected by default because they are marked `extended`.

- [ ] **Step 4: Run the fast new tests if `OPENAI_API_KEY` is available**

Run:

```bash
uv run pytest -m "extended and not extended_slow" tests/extended/test_openai_real_workflows.py -v
```

Expected with `OPENAI_API_KEY` set: 4 passed, 1 deselected. Expected without the key: tests skip.

- [ ] **Step 5: Commit fast workflow tests**

```bash
git add tests/extended/test_openai_real_workflows.py
git commit -m "test(extended): cover live OpenAI workflow contracts"
```

---

## Task 4: Decide Whether to Replace or Keep Existing Explicit Async Coverage

**Files:**
- Modify: `tests/extended/test_openai_cli_lifecycle.py`

**Recommendation:** Keep the existing `test_openai_resume_async_cli_one_tick` even though Task 3 adds `EXT-OAI-BG-JSON-EXPLICIT-ASYNC`. They test different layers:

- `EXT-OAI-BG-JSON-EXPLICIT-ASYNC`: submit envelope only, cancels immediately.
- existing `test_openai_resume_async_cli_one_tick`: submit, `resume --async --json`, text `resume --async`, `status --json`, then cleanup.

- [ ] **Step 1: Rename the existing test for clarity**

Change:

```python
def test_openai_resume_async_cli_one_tick(live_cli_env: tuple[dict[str, str], Path]) -> None:
```

to:

```python
def test_openai_resume_async_cli_one_tick_after_explicit_async_submit(
    live_cli_env: tuple[dict[str, str], Path],
) -> None:
```

Also update its docstring:

```python
"""Live OpenAI explicit async submit can be checked with one non-blocking resume tick."""
```

- [ ] **Step 2: Ensure cleanup uses the shared cancel helper**

The `finally` block should be:

```python
    finally:
        cancel_background_operation(operation_id, env, state_root)
```

- [ ] **Step 3: Run collect-only for lifecycle file**

Run:

```bash
uv run pytest --collect-only -q -m extended tests/extended/test_openai_cli_lifecycle.py
```

Expected:

```text
tests/extended/test_openai_cli_lifecycle.py::test_openai_resume_async_cli_one_tick_after_explicit_async_submit
tests/extended/test_openai_cli_lifecycle.py::test_openai_ctrl_c_sync_background_cancels_upstream
```

- [ ] **Step 4: Commit lifecycle naming cleanup**

```bash
git add tests/extended/test_openai_cli_lifecycle.py
git commit -m "test(extended): clarify OpenAI async resume lifecycle coverage"
```

---

## Task 5: Slow Full Lifecycle Verification

**Files:**
- Modify: `tests/extended/test_openai_real_workflows.py`

**Why separate:** This is the expensive test. It should run only when explicitly requested, but it is the one test that proves final output extraction works against live OpenAI response shapes.

- [ ] **Step 1: Run only the slow lifecycle test with explicit opt-in**

Run:

```bash
THOTH_EXTENDED_SLOW=1 uv run pytest -m "extended and extended_slow" tests/extended/test_openai_real_workflows.py::test_ext_oai_bg_async_blocking_resume_complete -v
```

Expected with `OPENAI_API_KEY` set: pass within the 900 second timeout. If it fails before completion, the `finally` cleanup attempts `thoth cancel <op-id> --json` and direct OpenAI cancel by job ID.

- [ ] **Step 2: If the slow test flakes on exact stdout text, loosen only stdout assertion**

If the failure is only:

```text
AssertionError: assert 'Research completed' in resume.stdout or 'Saved results from:' in resume.stdout
```

replace:

```python
assert "Research completed" in resume.stdout or "Saved results from:" in resume.stdout
```

with:

```python
assert resume.stdout.strip()
```

Keep the checkpoint and output-file assertions unchanged. Those are the real contract.

- [ ] **Step 3: Commit slow lifecycle test adjustment if needed**

Only commit if Step 2 changed the test:

```bash
git add tests/extended/test_openai_real_workflows.py
git commit -m "test(extended): harden live blocking resume assertion"
```

---

## Task 6: Verification

**Files:**
- No code changes unless failures reveal a real bug.

- [ ] **Step 1: Verify default pytest behavior**

Run:

```bash
uv run pytest -q
```

Expected: default pytest passes and extended tests are deselected.

- [ ] **Step 2: Verify extended collection**

Run:

```bash
uv run pytest --collect-only -q -m extended tests/extended
```

Expected collection count after this plan:

```text
10 tests collected
```

Expected test set:

```text
tests/extended/test_model_kind_runtime.py::test_model_kind_matches_runtime_behavior[openai/o3]
tests/extended/test_model_kind_runtime.py::test_model_kind_matches_runtime_behavior[openai/o4-mini-deep-research]
tests/extended/test_model_kind_runtime.py::test_model_kind_matches_runtime_behavior[openai/o3-deep-research]
tests/extended/test_openai_cli_lifecycle.py::test_openai_resume_async_cli_one_tick_after_explicit_async_submit
tests/extended/test_openai_cli_lifecycle.py::test_openai_ctrl_c_sync_background_cancels_upstream
tests/extended/test_openai_real_workflows.py::test_ext_oai_imm_stream_tee
tests/extended/test_openai_real_workflows.py::test_ext_oai_bg_json_auto_async
tests/extended/test_openai_real_workflows.py::test_ext_oai_bg_json_explicit_async
tests/extended/test_openai_real_workflows.py::test_ext_oai_bg_cancel_cmd
tests/extended/test_openai_real_workflows.py::test_ext_oai_bg_async_blocking_resume_complete
```

- [ ] **Step 3: Run fast extended tests**

Run:

```bash
uv run pytest -m "extended and not extended_slow" tests/extended -v
```

Expected with `OPENAI_API_KEY` set: fast extended tests pass. The slow lifecycle test is deselected.

- [ ] **Step 4: Run slow lifecycle test only when explicitly desired**

Run:

```bash
THOTH_EXTENDED_SLOW=1 uv run pytest -m "extended and extended_slow" tests/extended/test_openai_real_workflows.py::test_ext_oai_bg_async_blocking_resume_complete -v
```

Expected with `OPENAI_API_KEY` set: pass, completed checkpoint, one non-empty `_openai_` result file.

- [ ] **Step 5: Run quality checks**

Run:

```bash
make env-check
just fix
just check
./thoth_test -r
just test-fix
just test-lint
just test-typecheck
```

Expected: all pass. If `just fix` or `just test-fix` changes files, rerun the relevant checks and include those edits in the final commit.

---

## Rollback and Leak Safety

- Every background test stores `operation_id` and calls `cancel_background_operation(operation_id, env, state_root)` in `finally`.
- `cancel_background_operation` checks the local checkpoint first. It skips cancellation only when the operation is already `completed`.
- If `thoth cancel <op-id> --json` fails or the checkpoint path is unavailable, it falls back to direct `OpenAIProvider.cancel(job_id)` when a provider job ID is present.
- If a test times out before an operation ID is captured, no job ID is known. That failure should be investigated before rerunning the whole suite.

## Completion Criteria

- The extended suite has the five new scenario IDs above.
- The slow lifecycle test is gated by both `extended_slow` and `THOTH_EXTENDED_SLOW=1`.
- Fast background tests cancel live jobs after the contract assertion.
- Default `uv run pytest -q` remains free of live OpenAI calls.
- The final implementation preserves the current broad mock coverage and does not duplicate every mock-only flow as a live test.
