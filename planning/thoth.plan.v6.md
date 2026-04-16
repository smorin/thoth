# P05: VCR Cassette Replay Tests — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add pytest-based VCR cassette replay tests that exercise `OpenAIProvider.submit()`, `check_status()`, and `get_result()` against recorded API traffic, wired into `just all`.

**Architecture:** Separate `tests/` directory with pytest + vcrpy replaying cassettes from `thoth_test_cassettes/`. VCR configured with `record_mode="none"` (never hits live API) and `match_on=["uri", "method"]` (cassette request bodies differ from SDK-generated bodies). A new `test-vcr` justfile recipe runs the pytest suite and is added to the `all` recipe.

**Tech Stack:** pytest, vcrpy (>=8.1.1), existing OpenAI cassettes in `thoth_test_cassettes/openai/happy-path.yaml`

---

## File Structure

| Action | Path | Responsibility |
|--------|------|---------------|
| Create | `tests/test_vcr_openai.py` | VCR replay tests for OpenAIProvider |
| Create | `tests/conftest.py` | Shared VCR configuration + cassette directory constant |
| Modify | `pyproject.toml:54-59` | Add pytest and vcrpy to dev dependencies |
| Modify | `justfile:37` | Add `test-vcr` to `all` recipe |
| Modify | `justfile:102-117` | Add `test-vcr` recipe in Testing section |
| Modify | `PROJECTS.md` | Add P05 project tracking |

## Critical Design Note: VCR Request Matching

The cassette records the raw API request body as a plain string (`"input": "What are the three..."`), but `OpenAIProvider.submit()` sends structured input messages (`"input": [{"role": "user", ...}]`). VCR's default body matching would fail. We use `match_on=["uri", "method"]` to match only on URL and HTTP method, ignoring body differences. This is safe because the cassette has exactly one POST URI and replays GETs in recorded order.

## Cassette Structure Reference

The `happy-path.yaml` cassette contains 57 interactions:
- **Interaction 0:** `POST /v1/responses` → `status: "queued"`, `id: "resp_0c13a25ee1a48f780069df079e0a58819cbde29d8a2906c590"`
- **Interactions 1–55:** `GET /v1/responses/{id}` → `status: "in_progress"`
- **Interaction 56:** `GET /v1/responses/{id}` → `status: "completed"`, full output with text + annotations

Each `@vcr.use_cassette` decorated test replays from interaction 0.

---

### Task 1: Add pytest and vcrpy dev dependencies

**Files:**
- Modify: `pyproject.toml:54-59`

- [ ] **Step 1: Add dependencies**

In `pyproject.toml`, add `pytest` and `vcrpy` to the dev dependency group:

```toml
[dependency-groups]
dev = [
    "ruff>=0.9",
    "ty>=0.0.1a14",
    "pexpect>=4.8",
    "pytest>=8.0",
    "vcrpy>=8.1.1",
]
```

- [ ] **Step 2: Lock dependencies**

Run: `uv lock`
Expected: `uv.lock` updates with pytest and vcrpy resolved.

- [ ] **Step 3: Sync environment**

Run: `uv sync`
Expected: pytest and vcrpy installed into the project venv.

- [ ] **Step 4: Verify pytest is available**

Run: `uv run pytest --version`
Expected: prints pytest version (8.x+).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "feat(test): add pytest and vcrpy dev dependencies for VCR cassette tests"
```

---

### Task 2: Create shared VCR test configuration

**Files:**
- Create: `tests/conftest.py`

- [ ] **Step 1: Create tests/conftest.py**

```python
"""Shared VCR configuration for cassette replay tests."""

from __future__ import annotations

from pathlib import Path

import vcr

CASSETTE_DIR = Path(__file__).resolve().parent.parent / "thoth_test_cassettes"

# Shared VCR instance:
# - record_mode="none": never make real HTTP requests
# - match_on=["uri", "method"]: ignore body differences between SDK-generated
#   requests (structured input_messages) and cassette bodies (plain strings)
thoth_vcr = vcr.VCR(
    record_mode="none",
    match_on=["uri", "method"],
)
```

- [ ] **Step 2: Verify the import works**

Run: `uv run python -c "from tests.conftest import thoth_vcr, CASSETTE_DIR; print(CASSETTE_DIR)"`
Expected: prints the absolute path to `thoth_test_cassettes/`.

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "feat(test): add shared VCR configuration in tests/conftest.py"
```

---

### Task 3: Write failing VCR replay tests for OpenAIProvider

**Files:**
- Create: `tests/test_vcr_openai.py`

- [ ] **Step 1: Write test file with all test cases**

Create `tests/test_vcr_openai.py`:

```python
"""VCR cassette replay tests for OpenAI provider."""

from __future__ import annotations

import asyncio
from pathlib import Path

from tests.conftest import CASSETTE_DIR, thoth_vcr

OPENAI_CASSETTE = str(CASSETTE_DIR / "openai" / "happy-path.yaml")

# The prompt recorded in the cassette — must match for submit() to work,
# though VCR matching ignores bodies (match_on=["uri", "method"]).
CASSETTE_PROMPT = (
    "What are the three most significant recent breakthroughs"
    " in solid-state battery technology? Provide specific company"
    " names, dates, and technical details with citations."
)

# The response ID baked into the cassette.
CASSETTE_RESPONSE_ID = "resp_0c13a25ee1a48f780069df079e0a58819cbde29d8a2906c590"


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


def _make_provider():
    """Create an OpenAIProvider configured for deep-research cassette replay."""
    from thoth.__main__ import OpenAIProvider

    return OpenAIProvider(
        api_key="sk-replay-dummy",
        config={"model": "o4-mini-deep-research", "background": True},
    )


class TestOpenAISubmit:
    """Replay the happy-path cassette through OpenAIProvider.submit()."""

    @thoth_vcr.use_cassette(OPENAI_CASSETTE)
    def test_submit_returns_response_id(self):
        """submit() should return a response ID starting with 'resp_'."""
        provider = _make_provider()
        job_id = _run(provider.submit(prompt=CASSETTE_PROMPT, mode="deep-research"))
        assert job_id.startswith("resp_"), f"unexpected job_id: {job_id}"

    @thoth_vcr.use_cassette(OPENAI_CASSETTE)
    def test_submit_returns_expected_id(self):
        """submit() should return the exact ID from the cassette."""
        provider = _make_provider()
        job_id = _run(provider.submit(prompt=CASSETTE_PROMPT, mode="deep-research"))
        assert job_id == CASSETTE_RESPONSE_ID

    @thoth_vcr.use_cassette(OPENAI_CASSETTE)
    def test_submit_stores_job_info(self):
        """submit() should populate self.jobs with the job ID."""
        provider = _make_provider()
        job_id = _run(provider.submit(prompt=CASSETTE_PROMPT, mode="deep-research"))
        assert job_id in provider.jobs
        assert provider.jobs[job_id]["background"] is True


class TestOpenAIPolling:
    """Replay the full polling sequence to completion."""

    @thoth_vcr.use_cassette(OPENAI_CASSETTE)
    def test_first_status_is_in_progress_or_queued(self):
        """First check_status() after submit should be queued or in_progress."""
        provider = _make_provider()
        job_id = _run(provider.submit(prompt=CASSETTE_PROMPT, mode="deep-research"))
        status = _run(provider.check_status(job_id))
        assert status["status"] in ("queued", "running"), f"unexpected: {status}"

    @thoth_vcr.use_cassette(OPENAI_CASSETTE)
    def test_poll_to_completed(self):
        """Polling check_status() through the cassette should reach 'completed'."""
        provider = _make_provider()
        job_id = _run(provider.submit(prompt=CASSETTE_PROMPT, mode="deep-research"))

        final_status = None
        for _ in range(60):
            info = _run(provider.check_status(job_id))
            if info["status"] == "completed":
                final_status = info
                break
        assert final_status is not None, "never reached 'completed'"
        assert final_status["status"] == "completed"
        assert final_status["progress"] == 1.0


class TestOpenAIResult:
    """Verify get_result() returns substantial research output."""

    @thoth_vcr.use_cassette(OPENAI_CASSETTE)
    def test_get_result_returns_text(self):
        """After polling to completed, get_result() should return research text."""
        provider = _make_provider()
        job_id = _run(provider.submit(prompt=CASSETTE_PROMPT, mode="deep-research"))

        # Poll through all in_progress interactions to reach completed
        for _ in range(60):
            info = _run(provider.check_status(job_id))
            if info["status"] == "completed":
                break

        # get_result() will try another retrieve call; VCR raises CannotSendRequest
        # since the cassette is exhausted, but get_result() catches the exception
        # and falls back to the cached response from the last check_status() call.
        result = _run(provider.get_result(job_id))
        assert len(result) > 100, f"expected substantial output, got {len(result)} chars"

    @thoth_vcr.use_cassette(OPENAI_CASSETTE)
    def test_get_result_contains_research_content(self):
        """Result text should contain domain-relevant content from the cassette."""
        provider = _make_provider()
        job_id = _run(provider.submit(prompt=CASSETTE_PROMPT, mode="deep-research"))

        for _ in range(60):
            info = _run(provider.check_status(job_id))
            if info["status"] == "completed":
                break

        result = _run(provider.get_result(job_id))
        # The cassette output discusses solid-state batteries
        assert "solid" in result.lower() or "battery" in result.lower(), (
            "expected research content about batteries"
        )
```

- [ ] **Step 2: Run tests to verify they fail (no implementation issue — tests should pass with existing code)**

Run: `uv run pytest tests/test_vcr_openai.py -v`
Expected: Tests either pass (proving the VCR integration works) or fail with a specific VCR/httpx interception issue that needs debugging.

- [ ] **Step 3: Debug any VCR/httpx interception issues**

If tests fail due to VCR not intercepting `AsyncOpenAI`'s httpx calls, the most likely fix is to ensure vcrpy >= 8.1.1 (which has native httpx support). Check the error message and adjust.

Common issues:
- `CannotSendRequest` on the first POST → VCR isn't intercepting; check vcrpy version
- `ConnectionError` → VCR is intercepting but cassette format doesn't match; check `match_on`

- [ ] **Step 4: Commit**

```bash
git add tests/test_vcr_openai.py
git commit -m "feat(test): add VCR cassette replay tests for OpenAIProvider"
```

---

### Task 4: Add test-vcr justfile recipe and wire into all

**Files:**
- Modify: `justfile:37` (the `all` recipe)
- Modify: `justfile:102-117` (Testing section)

- [ ] **Step 1: Add test-vcr recipe to Testing section**

Add after the `update-snapshots` recipe (after line 117 in justfile):

```just
# Run VCR cassette replay tests
[group: 'testing']
test-vcr:
    uv run pytest tests/test_vcr_openai.py -v
```

- [ ] **Step 2: Add test-vcr to the all recipe**

Change line 37 from:

```just
all: format lint typecheck security test
```

to:

```just
all: format lint typecheck security test test-vcr
```

- [ ] **Step 3: Verify test-vcr runs standalone**

Run: `just test-vcr`
Expected: pytest runs 8 tests from `test_vcr_openai.py`, all pass.

- [ ] **Step 4: Verify just all includes test-vcr**

Run: `just all`
Expected: format, lint, typecheck, security, test, and test-vcr all run. No failures.

- [ ] **Step 5: Commit**

```bash
git add justfile
git commit -m "feat(test): add test-vcr justfile recipe and wire into just all"
```

---

### Task 5: Update PROJECTS.md with P05

**Files:**
- Modify: `PROJECTS.md`

- [ ] **Step 1: Add P05 project block at the top of PROJECTS.md**

Prepend the following to `PROJECTS.md` (before the existing P03 block):

```markdown
## [ ] Project P05: VCR Cassette Replay Tests (v2.6.0)
**Goal**: Add pytest-based VCR cassette replay tests that exercise OpenAIProvider against recorded API traffic, using Option B (separate pytest test file) from thoth_vcr.md.

**Out of Scope**
- Gemini/Perplexity cassettes (blocked on deepresearch_replay P03/P04)
- Integration into thoth_test runner (Option A rejected)

### Tests & Tasks
- [ ] [P05-T01] Add pytest and vcrpy to dev dependencies
- [ ] [P05-T02] Create tests/conftest.py with shared VCR configuration
- [ ] [P05-TS01] VCR-OAI-SUBMIT: submit() returns response ID from cassette
- [ ] [P05-TS02] VCR-OAI-SUBMIT: submit() returns exact cassette ID
- [ ] [P05-TS03] VCR-OAI-SUBMIT: submit() stores job info with background=True
- [ ] [P05-TS04] VCR-OAI-POLL: first check_status() returns queued/in_progress
- [ ] [P05-TS05] VCR-OAI-POLL: polling reaches completed status
- [ ] [P05-TS06] VCR-OAI-RESULT: get_result() returns substantial text
- [ ] [P05-TS07] VCR-OAI-RESULT: get_result() contains domain-relevant content
- [ ] [P05-T03] Add test-vcr justfile recipe and wire into just all
- [ ] [P05-T04] Update PROJECTS.md

### Automated Verification
- `make check` passes
- `just test-vcr` → 8/8 pass
- `just all` completes without errors

### Regression Test Status
- [ ] All existing thoth_test tests still pass
- [ ] VCR tests run in `record_mode="none"` — no live API calls

---

```

- [ ] **Step 2: Commit**

```bash
git add PROJECTS.md
git commit -m "docs: add P05 VCR Cassette Replay Tests to PROJECTS.md"
```

---

### Task 6: Final verification

- [ ] **Step 1: Run make check**

Run: `make check`
Expected: Environment dependencies verified.

- [ ] **Step 2: Run the full quality suite**

Run: `just all`
Expected: format, lint, typecheck, security, test, and test-vcr all pass.

- [ ] **Step 3: Run make test-check on thoth_test**

Run: `make test-check`
Expected: No lint/typecheck errors in thoth_test.

- [ ] **Step 4: Verify no regressions in existing tests**

Run: `./thoth_test -r --provider mock --skip-interactive`
Expected: All existing tests pass, no regressions.

- [ ] **Step 5: Mark P05 tasks as complete in PROJECTS.md**

Update each `[ ]` to `[x]` for completed tasks/tests in the P05 block.

- [ ] **Step 6: Final commit**

```bash
git add PROJECTS.md
git commit -m "docs: mark P05 VCR Cassette Replay Tests complete"
```
