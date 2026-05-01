# P20: Live-API Workflow Regression Suite — Implementation Plan (TDD)

**References**
- **Trunk:** [../PROJECTS.md](../PROJECTS.md) (P20 row, status legend, conventions)
- **Sibling cron:** [../.github/workflows/extended.yml](../.github/workflows/extended.yml) (model-kind drift watch, nightly)
- **Foundation test:** `tests/extended/test_model_kind_runtime.py` (existing live-API drift watch — pattern to mirror)
- **Mock counterparts:** `tests/test_output_sinks.py`, `tests/test_p16_pr2_ask.py`, `tests/test_cli_regressions.py`
- **Marker config:** `pyproject.toml` (`[tool.pytest.ini_options].markers`, `addopts`)
- **Lifecycle precedent:** `tests/extended/test_openai_cli_lifecycle.py` (P18-T38 — resume/cancel real-API patterns)

---

## Source of truth

The P20 row in `PROJECTS.md` is the contract. If this plan and the trunk disagree, the trunk wins.

## Outcome

A new `live_api` pytest marker, gating 8 real-API tests in a new `tests/extended/test_live_api_workflows.py`. Tests are deselected by default (PR CI and `git commit` unaffected). Run weekly via `.github/workflows/live-api.yml` (cron `0 2 * * 0` = Saturday 7pm PDT / Sunday 02:00 UTC). Cost target: <$0.20/run. Failures informational (`continue-on-error: true`).

## Phase ordering

The phases are ordered so each commit ships a self-consistent slice:

1. **Phase A — marker + workflow plumbing** (T01–T03). No test logic. Lands the `live_api` marker, the GitHub workflow file, and docs. After this phase, `pytest -m live_api` runs cleanly with 0 collected tests.
2. **Phase B — fixtures** (TS01–TS02). Land the shared fixture and assertion helpers. Mock-only meta-tests verify the helpers themselves.
3. **Phase C — immediate-path tests** (TS03–TS06). The largest tranche. Each test is independent; can be split across commits if reviews want it.
4. **Phase D — security + mismatch** (TS07–TS08). Smallest, most distinct tranche.

Each commit goes through the full pre-commit gate (lefthook). The last commit triggers `gh workflow run "Live-API Workflow Tests (weekly)"` to confirm the cron path works.

## Phase A — marker + workflow plumbing

### P20-T01: Register `live_api` marker

**File:** `pyproject.toml`

Add the marker entry alongside the existing `extended` entry, and extend `addopts`:

```toml
[tool.pytest.ini_options]
markers = [
    "extended: real-API contract tests; gated, not run by default",
    "live_api: real-API workflow regression tests; gated, weekly cron",
]
addopts = "-m 'not extended and not live_api'"
```

**File:** `justfile`

Add a recipe peer to `test-extended`:

```
# Run live-API workflow tests. Gated by `pytest -m live_api`;
# requires OPENAI_API_KEY. Runs weekly via .github/workflows/live-api.yml.
test-live-api:
    uv run pytest -m live_api -v
```

**Verify:**
- `uv run pytest -q` continues to deselect both markers (run count unchanged from pre-P20 baseline).
- `uv run pytest -m live_api --collect-only` succeeds (0 collected, pre-tests).

### P20-T02: GitHub Actions weekly workflow

**File:** `.github/workflows/live-api.yml`

```yaml
---
# P20: weekly real-API workflow regression tests.
#
# Runs `pytest -m live_api` against live OpenAI to detect drift
# in user-visible CLI behaviors (streaming, file output, append,
# no-metadata, secret masking, mismatch defense). Sibling to
# extended.yml (model-kind contracts, nightly).

name: Live-API Workflow Tests (weekly)

"on":
  schedule:
    - cron: "0 2 * * 0"   # Sunday 02:00 UTC = Saturday 7pm PDT
  workflow_dispatch:

permissions:
  contents: read

jobs:
  live_api:
    name: pytest -m live_api
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6.0.2
      - uses: astral-sh/setup-uv@v8.0.0
        with:
          python-version: "3.11"
          enable-cache: true
      - name: Run live-API workflow tests
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: uv run pytest -m live_api -v
        continue-on-error: true
```

**Setup checklist (one-time after merge):**
1. `OPENAI_API_KEY` repo secret is already present (used by `extended.yml`); no new secret required.
2. Manually trigger the workflow once via `gh workflow run "Live-API Workflow Tests (weekly)"` (or the Actions tab "Run workflow" button) to confirm the cron path works before relying on it.
3. Watch the badge weekly. `continue-on-error: true` keeps a red live-API run from blocking other CI.

### P20-T03: Documentation

**File:** `CLAUDE.md`

In the "Code Quality Assurance Workflow" section, add a bullet noting the new marker and weekly cadence. Keep it short — one paragraph or list item.

**File:** `README.md`

If a "Testing" or "Test categories" section exists, append the `live_api` marker row. Otherwise no-op (do not invent a section).

**Verify:**
- `grep -n live_api CLAUDE.md` returns at least one line.
- `grep -n live_api README.md || echo "no testing section, skipped"` — either match or documented skip.

---

## Phase B — fixtures

### P20-TS01: `live_cli_env` fixture

**File:** `tests/extended/conftest.py` (extend the existing file used by `test_openai_cli_lifecycle.py`).

Fixture contract:

```python
@pytest.fixture
def live_cli_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> LiveCliEnv:
    """Real-API test fixture. Skips if OPENAI_API_KEY missing."""
    if "OPENAI_API_KEY" not in os.environ:
        pytest.skip("OPENAI_API_KEY not set — skipping live_api test")
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(home / ".local" / "state"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(home / ".cache"))
    return LiveCliEnv(tmp_path=tmp_path, run=_run_thoth_factory(...))
```

The returned `LiveCliEnv` exposes:
- `tmp_path: Path` — the test's tmp dir (output goes here by default).
- `run(args: list[str], timeout: int = 60, env_overrides: dict[str, str] | None = None) -> CompletedProcess[str]` — runs `python -m thoth <args>` via subprocess; on non-zero exit, scrubs the API key from stdout/stderr before re-raising.

**Test:** `tests/extended/test_live_cli_env_fixture.py` (or add to existing `conftest.py` companion test file). Mock-only (no `live_api` marker — runs in default suite). Asserts:
- Skip when `OPENAI_API_KEY` deleted (use `monkeypatch.delenv`).
- `HOME` is the tmp dir, not the real home, when fixture is active.
- Secret scrub: feed stdout/stderr containing the secret to the scrubber, assert it's masked.

### P20-TS02: assertion helpers

**File:** `tests/extended/_assertions.py`

```python
def assert_nonempty_file(path: Path) -> None:
    assert path.exists(), f"expected file at {path}, none found"
    assert path.stat().st_size > 0, f"file at {path} is empty"

def assert_metadata_present(
    path: Path, *, prompt_fragment: str, mode: str, provider: str
) -> None:
    text = path.read_text()
    assert text.startswith("---\n"), "expected YAML front-matter at file start"
    assert f"mode: {mode}" in text
    assert f"provider: {provider}" in text
    assert prompt_fragment in text

def assert_metadata_absent(path: Path) -> None:
    text = path.read_text()
    assert not text.startswith("---\n"), "did not expect YAML front-matter"
    assert "operation_id:" not in text
    assert "### Prompt" not in text

def assert_secret_not_leaked(stdout: str, stderr: str, *, secret: str) -> None:
    assert secret not in stdout, "secret leaked to stdout"
    assert secret not in stderr, "secret leaked to stderr"
```

**Test:** `tests/extended/test_assertion_helpers.py`. Mock-only. Tiny round-trip tests with synthetic file contents.

---

## Phase C — immediate-path tests

All under `@pytest.mark.live_api`. All take `live_cli_env`.

### P20-TS03: streaming smoke

**Goal:** prove `provider.stream()` still works and immediate path doesn't go through background plumbing.

```python
@pytest.mark.live_api
def test_immediate_streaming_smoke(live_cli_env):
    result = live_cli_env.run([
        "ask", "live api streaming smoke",
        "--mode", "thinking", "--provider", "openai",
    ])
    assert result.returncode == 0
    assert result.stdout.strip(), "expected streamed output to stdout"
    # No default result file
    output_files = list(live_cli_env.tmp_path.rglob("*.md"))
    assert not output_files, f"expected no result files, found {output_files}"
    # No background hints in immediate path
    assert "Operation ID:" not in result.stdout
    assert "Resume with:" not in result.stdout
```

### P20-TS04: `--out FILE`

```python
@pytest.mark.live_api
def test_immediate_out_writes_file(live_cli_env):
    out = live_cli_env.tmp_path / "answer.md"
    result = live_cli_env.run([
        "ask", "live api file",
        "--mode", "thinking", "--provider", "openai",
        "--out", str(out),
    ])
    assert result.returncode == 0
    assert_nonempty_file(out)
    # stdout should be empty (or only contain progress UI; assert no answer text)
    # The exact contract is: streamed answer goes to file when --out is given.
```

### P20-TS05: `--append`

```python
@pytest.mark.live_api
def test_immediate_append_grows_file(live_cli_env):
    out = live_cli_env.tmp_path / "answer.md"
    cmd = ["ask", "live api append round one",
           "--mode", "thinking", "--provider", "openai",
           "--out", str(out), "--append"]
    r1 = live_cli_env.run(cmd)
    assert r1.returncode == 0
    size_after_first = out.stat().st_size
    prefix_after_first = out.read_bytes()[:50]

    r2 = live_cli_env.run(cmd[:1] + ["live api append round two"] + cmd[2:])
    assert r2.returncode == 0
    size_after_second = out.stat().st_size
    assert size_after_second > size_after_first
    # First run's content is still at the start
    assert out.read_bytes().startswith(prefix_after_first)
```

### P20-TS06: `--no-metadata`

```python
@pytest.mark.live_api
def test_immediate_no_metadata(live_cli_env):
    out = live_cli_env.tmp_path / "answer.md"
    result = live_cli_env.run([
        "ask", "live api no metadata",
        "--mode", "thinking", "--provider", "openai",
        "--out", str(out), "--no-metadata",
    ])
    assert result.returncode == 0
    assert_nonempty_file(out)
    assert_metadata_absent(out)
```

---

## Phase D — security + mismatch

### P20-TS07: CLI API key + secret leak

```python
@pytest.mark.live_api
def test_cli_api_key_no_leak(live_cli_env, monkeypatch):
    secret = os.environ["OPENAI_API_KEY"]
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = live_cli_env.run(
        ["ask", "live api cli key",
         "--mode", "thinking", "--provider", "openai",
         "--api-key-openai", secret],
        env_overrides={"OPENAI_API_KEY": ""},
    )
    assert result.returncode == 0
    assert result.stdout.strip()
    assert_secret_not_leaked(result.stdout, result.stderr, secret=secret)
```

### P20-TS08: mismatch defense (no HTTP)

This test does NOT need `live_api` because it makes no network call — but place it under the marker anyway since it lives in the same file and the cost is zero. (Alternatively split it into `tests/extended/test_mismatch_defense.py` without the marker. Implementer's call.)

```python
@pytest.mark.live_api
def test_mismatch_defense_no_http():
    """Immediate-declared deep-research model fails synchronously, no HTTP."""
    cm = ConfigManager()
    cm.load_all_layers({})
    bg_model = next(m.id for m in KNOWN_MODELS
                    if m.provider == "openai" and m.kind == "background")
    mode_config = {"provider": "openai", "model": bg_model, "kind": "immediate"}
    provider = create_provider("openai", cm, mode_config=mode_config)

    with pytest.raises(ModeKindMismatchError):
        asyncio.run(provider.submit("ping", mode="_mismatch_check_"))
```

The error must be raised before any HTTP call — verify by either using `pytest-httpx` to assert no request was made, or by inspecting that the test runs in well under network round-trip latency (e.g. `time.perf_counter()` < 100ms).

---

## Verification gate (final commit)

Before declaring P20 done:

```bash
just check                          # lint + typecheck on src/
just test-fix                       # auto-fix on tests/
just test-lint                      # lint on tests/
just test-typecheck                 # typecheck on tests/
uv run pytest -q                    # default suite untouched
uv run pytest -m live_api -v        # 8/8 pass with live OpenAI key
gh workflow run "Live-API Workflow Tests (weekly)"
gh run watch                        # confirm green via Actions
```

Then:

- Update CHANGELOG entry via release-please conventional commits.
- Tag through release-please's normal flow (no manual version bump).

## Commit cadence

One commit per logical chunk:

1. `feat(testing): register live_api pytest marker (P20-T01)`
2. `ci: add weekly live-api workflow (P20-T02)`
3. `docs(testing): document live_api marker (P20-T03)`
4. `test(live_api): add live_cli_env fixture and assertion helpers (P20-TS01, P20-TS02)`
5. `test(live_api): cover immediate streaming, file out, append, no-metadata (P20-TS03..TS06)`
6. `test(live_api): cover CLI api key secret leak and mismatch defense (P20-TS07, P20-TS08)`

## Cost & maintenance

- Per-run cost: <$0.20. 6 immediate streams (cents each), 1 secret-leak test (cents), 1 no-HTTP test (free).
- Annual: ~$10/year.
- Maintenance burden: when a new CLI flag with user-visible streaming/file behavior ships, add a corresponding `live_api` test. Out-of-scope flags (multi-provider, `--combined`, `--auto`-chain) stay deferred until P22+ ship real Perplexity/Gemini providers.
