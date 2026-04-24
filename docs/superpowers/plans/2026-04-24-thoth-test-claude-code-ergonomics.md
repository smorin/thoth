# thoth_test Claude-Code Ergonomics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add machine-readable output, precise selectors, and a self-rerun loop to `thoth_test` so Claude Code and hooks can consume it without shell-scraping.

**Architecture:** Single-file additions to the existing `thoth_test` uv-shebang script. Introduce a pure-Python `resolve_selection()` helper and JSON cache I/O. Add `pytest` coverage via `tests/test_thoth_test_cli.py` — unit tests import `thoth_test` as a module; integration tests subprocess-invoke `./thoth_test`.

**Tech Stack:** Python 3.11+, Click (already a dep), Rich (already a dep), pytest, uv shebang.

**Spec:** `docs/superpowers/specs/2026-04-24-thoth-test-claude-code-ergonomics-design.md`

---

## File Structure

**Modify:**
- `thoth_test` — add flags, resolver, cache I/O, list printers, fenced-failure printer, `-q` branch.
- `.gitignore` — add `.thoth_test_cache/` and `test_outputs/`.
- `CLAUDE.md` — replace workaround guidance with new flags (Task 8).

**Create:**
- `tests/test_thoth_test_cli.py` — pytest coverage for the new CLI surface.

No new production modules. `thoth_test` stays a single file.

### Module-level additions to `thoth_test`

Near existing constants (line ~60):
```python
CACHE_DIR = Path(".thoth_test_cache")
CACHE_FILE = CACHE_DIR / "last_run.json"
REPORT_SCHEMA_VERSION = 1
```

Helpers added (location noted per task):
- `resolve_selection(all_tests, *, test, provider_filter, interactive, skip_interactive, ids, last_failed) -> tuple[list[TestCase], list[str]]` — returns `(selected_tests, warnings)`.
- `serialize_run_report(runner, invocation) -> dict`
- `write_cache(report, path=CACHE_FILE) -> None` (atomic)
- `read_last_failed(path=CACHE_FILE) -> list[str]`
- `print_list_tsv(tests)`, `print_list_json(tests)`
- `print_fenced_failure(result, test_case)`

### Pytest importability

`thoth_test` is currently a shebang script with no `.py` extension. Pytest tests import it via a helper:
```python
import importlib.util, pathlib
spec = importlib.util.spec_from_loader(
    "thoth_test_mod",
    importlib.machinery.SourceFileLoader("thoth_test_mod", str(pathlib.Path(__file__).resolve().parent.parent / "thoth_test"))
)
thoth_test_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(thoth_test_mod)
```
Wrap this in a `conftest.py` fixture or a module-level import helper in the test file.

---

## Task 1: Add cache directory to `.gitignore`

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Append entries**

Add to `.gitignore`, in the `# Testing` section (after line 31 `.pytest_cache/`):

```
# thoth_test runner state
.thoth_test_cache/
test_outputs/
```

- [ ] **Step 2: Verify not already tracked**

Run: `git ls-files | grep -E '(thoth_test_cache|test_outputs)' || echo "clean"`
Expected: `clean`

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: gitignore .thoth_test_cache/ and test_outputs/"
```

---

## Task 2: Extract `resolve_selection()` helper (behaviour-preserving refactor)

**Goal:** Move today's inline filter logic in `main()` (lines ~2759–2815) into a pure function that later tasks can extend with `--id` and `--last-failed`.

**Files:**
- Modify: `thoth_test` (new function near line ~460, call site in `main()` near line ~2759)
- Test: `tests/test_thoth_test_cli.py` (new file)

- [ ] **Step 1: Write the failing test**

Create `tests/test_thoth_test_cli.py`:

```python
"""CLI-surface tests for the thoth_test runner itself."""

import importlib.machinery
import importlib.util
import pathlib

import pytest


@pytest.fixture(scope="module")
def thoth_test_mod():
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    loader = importlib.machinery.SourceFileLoader("thoth_test_mod", str(repo_root / "thoth_test"))
    spec = importlib.util.spec_from_loader("thoth_test_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_resolve_selection_provider_filter_keeps_agnostic(thoth_test_mod):
    TC = thoth_test_mod.TestCase
    all_tests = [
        TC(test_id="A", description="agnostic", command=["x"]),
        TC(test_id="B", description="mock only", command=["x"], provider="mock"),
        TC(test_id="C", description="openai only", command=["x"], provider="openai"),
    ]
    selected, warnings = thoth_test_mod.resolve_selection(
        all_tests,
        test=None,
        provider_filter=["mock"],
        interactive=False,
        skip_interactive=False,
        ids=[],
        last_failed=False,
    )
    ids = [t.test_id for t in selected]
    assert ids == ["A", "B"]
    assert warnings == []


def test_resolve_selection_substring_pattern(thoth_test_mod):
    TC = thoth_test_mod.TestCase
    all_tests = [
        TC(test_id="M1T-01", description="alpha", command=["x"]),
        TC(test_id="M1T-02", description="beta cancelled", command=["x"]),
        TC(test_id="OTHER", description="gamma", command=["x"]),
    ]
    selected, _ = thoth_test_mod.resolve_selection(
        all_tests,
        test="cancelled",
        provider_filter=None,
        interactive=False,
        skip_interactive=False,
        ids=[],
        last_failed=False,
    )
    assert [t.test_id for t in selected] == ["M1T-02"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_thoth_test_cli.py -v`
Expected: FAIL with `AttributeError: module 'thoth_test_mod' has no attribute 'resolve_selection'`.

- [ ] **Step 3: Add the helper**

Add to `thoth_test`, immediately before the `# Test Runner` section banner (around line ~703):

```python
# ============================================================================
# Selection Resolver
# ============================================================================


def resolve_selection(
    all_tests: list[TestCase],
    *,
    test: str | None,
    provider_filter: list[str] | None,
    interactive: bool,
    skip_interactive: bool,
    ids: list[str],
    last_failed: bool,
) -> tuple[list[TestCase], list[str]]:
    """Pure filter-composition for main().

    Returns (selected_tests, warnings). ``ids`` and ``last_failed`` overrides
    are handled in later tasks; this task only covers the pre-existing
    filters so the refactor is behaviour-preserving.
    """
    warnings: list[str] = []
    selected = list(all_tests)

    if interactive:
        selected = [t for t in selected if getattr(t, "is_interactive", False)]
    if skip_interactive:
        selected = [t for t in selected if not getattr(t, "is_interactive", False)]

    if test:
        needle = test
        selected = [
            t for t in selected
            if needle in t.test_id or needle.lower() in t.description.lower()
        ]

    if provider_filter:
        kept = []
        for t in selected:
            if not t.provider:
                kept.append(t)
            elif t.provider in provider_filter:
                kept.append(t)
        selected = kept

    return selected, warnings
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_thoth_test_cli.py -v`
Expected: PASS (both tests green).

- [ ] **Step 5: Wire `main()` to call the new helper (behaviour-preserving)**

In `thoth_test`, replace the filter block inside `main()` (lines ~2759 to the line immediately before `if verbose:`, i.e., just after "Show breakdown" block) with:

```python
    tests_to_run, selection_warnings = resolve_selection(
        all_tests,
        test=test,
        provider_filter=requested_providers,
        interactive=interactive,
        skip_interactive=skip_interactive,
        ids=[],
        last_failed=False,
    )
    for w in selection_warnings:
        console.print(f"[yellow]{w}[/yellow]")

    if interactive:
        console.print(f"Running {len(tests_to_run)} interactive mode tests")
    elif test:
        console.print(f"Running {len(tests_to_run)} tests matching '{test}'")
    else:
        console.print(f"Total tests: {len(tests_to_run)}")

    if requested_providers:
        provider_counts: dict[str, int] = {p: 0 for p in requested_providers}
        provider_counts["none"] = 0
        for t in tests_to_run:
            key = t.provider if t.provider in requested_providers else ("none" if not t.provider else t.provider)
            if key in provider_counts:
                provider_counts[key] += 1
        console.print(
            f"Filtered to {len(tests_to_run)} tests for provider(s): {', '.join(requested_providers)}"
        )
        breakdown = [f"{p}: {provider_counts[p]}" for p in requested_providers if provider_counts[p]]
        if provider_counts["none"]:
            breakdown.append(f"provider-agnostic: {provider_counts['none']}")
        if breakdown:
            console.print(f"Test breakdown: {', '.join(breakdown)}")
```

- [ ] **Step 6: Regression check — full suite still passes**

Run: `./thoth_test -r --provider mock --skip-interactive`
Expected: same PASS/FAIL counts as before the refactor; exit 0.

- [ ] **Step 7: Commit**

```bash
git add thoth_test tests/test_thoth_test_cli.py
git commit -m "refactor(thoth_test): extract resolve_selection() helper"
```

---

## Task 3: Add `--list` and `--list-json`

**Files:**
- Modify: `thoth_test` (add list printers near line ~700; add CLI options; early-exit in `main()`)
- Test: `tests/test_thoth_test_cli.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_thoth_test_cli.py`:

```python
import json
import subprocess
import pathlib


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _run_thoth_test(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["./thoth_test", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_list_tsv_shape():
    proc = _run_thoth_test("--list")
    assert proc.returncode == 0
    lines = [line for line in proc.stdout.splitlines() if line]
    assert lines, "expected at least one test listed"
    for line in lines:
        parts = line.split("\t")
        assert len(parts) == 4, f"expected 4 tab-separated fields, got {len(parts)}: {line!r}"


def test_list_json_shape():
    proc = _run_thoth_test("--list-json")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert isinstance(data, list)
    assert data, "expected at least one test"
    entry = data[0]
    for key in ("test_id", "provider", "test_type", "description", "is_interactive"):
        assert key in entry, f"missing key {key!r} in {entry!r}"


def test_list_and_list_json_mutually_exclusive():
    proc = _run_thoth_test("--list", "--list-json")
    assert proc.returncode == 2
    assert "mutually exclusive" in proc.stderr.lower()


def test_list_respects_provider_filter():
    all_proc = _run_thoth_test("--list")
    filtered_proc = _run_thoth_test("--list", "--provider", "mock")
    assert all_proc.returncode == 0 and filtered_proc.returncode == 0
    all_ids = {line.split("\t")[0] for line in all_proc.stdout.splitlines() if line}
    filtered_ids = {line.split("\t")[0] for line in filtered_proc.stdout.splitlines() if line}
    assert filtered_ids <= all_ids
    assert filtered_ids, "mock filter should keep at least mock-provider tests"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_thoth_test_cli.py -k "list" -v`
Expected: FAIL — "no such option: --list" or similar.

- [ ] **Step 3: Add list printers**

Add to `thoth_test` near line ~700 (before the Selection Resolver banner):

```python
def print_list_tsv(tests: list[TestCase]) -> None:
    for t in tests:
        provider = t.provider or "none"
        sys.stdout.write(f"{t.test_id}\t{provider}\t{t.test_type}\t{t.description}\n")


def print_list_json(tests: list[TestCase]) -> None:
    payload = [
        {
            "test_id": t.test_id,
            "provider": t.provider,
            "test_type": t.test_type,
            "description": t.description,
            "is_interactive": bool(getattr(t, "is_interactive", False)),
        }
        for t in tests
    ]
    sys.stdout.write(json.dumps(payload) + "\n")
```

- [ ] **Step 4: Add CLI options and early-exit branch**

In `thoth_test`, inside the `@click.command()` decorator chain above `def main(...)`, add:

```python
@click.option("--list", "list_flag", is_flag=True, help="Print tests without running them (TSV).")
@click.option("--list-json", "list_json_flag", is_flag=True, help="Print tests without running them (JSON).")
@click.option("--id", "ids", multiple=True, help="Exact-match test IDs to run (repeatable). Overrides other filters.")
```

Add `list_flag`, `list_json_flag`, `ids` to the `main(...)` signature.

In `main()`, immediately after `_ensure_test_config_home()`:

```python
    if list_flag and list_json_flag:
        click.echo("--list and --list-json are mutually exclusive", err=True)
        sys.exit(2)
    if list_flag or list_json_flag:
        # Parse provider filter the same way -r does, so listing previews filtering.
        preview_providers: list[str] | None = None
        if provider and all_providers:
            click.echo("Error: Cannot specify both --provider and --all-providers", err=True)
            sys.exit(2)
        if provider:
            preview_providers = [p.strip() for p in provider.split(",")]
        elif all_providers:
            preview_providers = ["mock", "openai", "perplexity"]

        preview_tests, _ = resolve_selection(
            all_tests,
            test=test,
            provider_filter=preview_providers,
            interactive=interactive,
            skip_interactive=skip_interactive,
            ids=list(ids),
            last_failed=False,
        )
        if list_flag:
            print_list_tsv(preview_tests)
        else:
            print_list_json(preview_tests)
        sys.exit(0)
```

(`ids` is wired through but not yet acted on inside `resolve_selection` — that comes in Task 4.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_thoth_test_cli.py -k "list" -v`
Expected: PASS (4 tests green).

- [ ] **Step 6: Commit**

```bash
git add thoth_test tests/test_thoth_test_cli.py
git commit -m "feat(thoth_test): add --list and --list-json for test discovery"
```

---

## Task 4: Implement `--id` exact-match selection

**Files:**
- Modify: `thoth_test` — extend `resolve_selection` to honour `ids`.
- Test: `tests/test_thoth_test_cli.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_thoth_test_cli.py`:

```python
def test_id_exact_match_runs_only_that_test(thoth_test_mod):
    TC = thoth_test_mod.TestCase
    all_tests = [
        TC(test_id="A", description="a", command=["x"]),
        TC(test_id="AB", description="ab", command=["x"]),
        TC(test_id="B", description="b", command=["x"]),
    ]
    selected, warnings = thoth_test_mod.resolve_selection(
        all_tests,
        test=None,
        provider_filter=None,
        interactive=False,
        skip_interactive=False,
        ids=["A"],
        last_failed=False,
    )
    assert [t.test_id for t in selected] == ["A"]
    assert warnings == []


def test_id_unknown_warns_but_does_not_error(thoth_test_mod):
    TC = thoth_test_mod.TestCase
    all_tests = [TC(test_id="A", description="a", command=["x"])]
    selected, warnings = thoth_test_mod.resolve_selection(
        all_tests,
        test=None,
        provider_filter=None,
        interactive=False,
        skip_interactive=False,
        ids=["DOES-NOT-EXIST"],
        last_failed=False,
    )
    assert selected == []
    assert any("DOES-NOT-EXIST" in w for w in warnings)


def test_id_overrides_provider_filter_and_marks_requested_but_filtered(thoth_test_mod):
    TC = thoth_test_mod.TestCase
    all_tests = [
        TC(test_id="OA", description="openai test", command=["x"], provider="openai"),
        TC(test_id="MK", description="mock test", command=["x"], provider="mock"),
    ]
    selected, warnings = thoth_test_mod.resolve_selection(
        all_tests,
        test=None,
        provider_filter=["mock"],
        interactive=False,
        skip_interactive=False,
        ids=["OA"],
        last_failed=False,
    )
    assert [t.test_id for t in selected] == ["OA"]
    # requested_but_filtered flag is set on the TestCase by resolver
    assert getattr(selected[0], "_requested_but_filtered", False) is True
    assert any("OA" in w and "provider" in w.lower() for w in warnings)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_thoth_test_cli.py -k "id_" -v`
Expected: FAIL — `ids` not honoured; `_requested_but_filtered` attr missing.

- [ ] **Step 3: Extend `resolve_selection`**

Replace the body of `resolve_selection` in `thoth_test` with:

```python
def resolve_selection(
    all_tests: list[TestCase],
    *,
    test: str | None,
    provider_filter: list[str] | None,
    interactive: bool,
    skip_interactive: bool,
    ids: list[str],
    last_failed: bool,
) -> tuple[list[TestCase], list[str]]:
    warnings: list[str] = []

    # --id and --last-failed short-circuit the other filters per spec.
    # (--last-failed resolution lands in Task 6; for now treat it as a no-op.)
    if ids:
        by_id = {t.test_id: t for t in all_tests}
        selected: list[TestCase] = []
        for wanted in ids:
            t = by_id.get(wanted)
            if t is None:
                warnings.append(f"--id {wanted} not found, ignoring")
                continue
            # Detect mismatch against other filters and annotate the TestCase.
            mismatch_reasons = []
            if provider_filter and t.provider and t.provider not in provider_filter:
                mismatch_reasons.append(f"provider={t.provider} not in --provider {provider_filter}")
            if interactive and not getattr(t, "is_interactive", False):
                mismatch_reasons.append("not an interactive test but --interactive set")
            if skip_interactive and getattr(t, "is_interactive", False):
                mismatch_reasons.append("interactive test but --skip-interactive set")
            t._requested_but_filtered = bool(mismatch_reasons)
            if mismatch_reasons:
                warnings.append(f"--id {wanted} runs despite filter mismatch: {'; '.join(mismatch_reasons)}")
            selected.append(t)
        return selected, warnings

    selected = list(all_tests)
    if interactive:
        selected = [t for t in selected if getattr(t, "is_interactive", False)]
    if skip_interactive:
        selected = [t for t in selected if not getattr(t, "is_interactive", False)]
    if test:
        needle = test
        selected = [
            t for t in selected
            if needle in t.test_id or needle.lower() in t.description.lower()
        ]
    if provider_filter:
        kept = []
        for t in selected:
            if not t.provider:
                kept.append(t)
            elif t.provider in provider_filter:
                kept.append(t)
        selected = kept
    for t in selected:
        t._requested_but_filtered = False
    return selected, warnings
```

- [ ] **Step 4: Wire `--id` into `main()`**

Replace the `tests_to_run, selection_warnings = resolve_selection(...)` call added in Task 2 Step 5 so it passes `ids=list(ids)`. (Parameter already wired into `main()` in Task 3 Step 4.)

Additionally emit selection warnings to stderr (not the Rich console):

```python
    for w in selection_warnings:
        click.echo(f"Warning: {w}", err=True)
```

(Remove any earlier yellow-console print of `selection_warnings` added in Task 2.)

- [ ] **Step 5: Run unit tests to verify they pass**

Run: `uv run pytest tests/test_thoth_test_cli.py -k "id_" -v`
Expected: PASS (3 tests green).

- [ ] **Step 6: Integration test — `--id` runs only one real test**

Append:

```python
def test_id_integration_runs_exactly_one_test():
    proc = _run_thoth_test("-r", "--id", "M1T-01", "-q")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "1 passed" in proc.stdout
```

Run: `uv run pytest tests/test_thoth_test_cli.py::test_id_integration_runs_exactly_one_test -v`
Expected: initially FAIL because `-q` lands in Task 8. Mark the test with `@pytest.mark.skip(reason="requires -q, landed in Task 8")` for now — unskip in Task 8 Step 4.

- [ ] **Step 7: Commit**

```bash
git add thoth_test tests/test_thoth_test_cli.py
git commit -m "feat(thoth_test): add --id for exact-match test selection"
```

---

## Task 5: Always-on last-run cache

**Goal:** Every `-r` invocation writes `.thoth_test_cache/last_run.json` atomically, containing the full v1 schema (stdout/stderr full for failures, null for passes).

**Files:**
- Modify: `thoth_test` — add serializer + atomic write; call from `generate_report`.
- Test: `tests/test_thoth_test_cli.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_thoth_test_cli.py`:

```python
def test_cache_written_on_every_run(tmp_path, monkeypatch):
    # Run in the repo (cache path is relative to cwd) but clean any prior state.
    cache_file = REPO_ROOT / ".thoth_test_cache" / "last_run.json"
    if cache_file.exists():
        cache_file.unlink()
    proc = _run_thoth_test("-r", "--id", "M1T-01")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert cache_file.exists(), "cache file should be written after every run"
    payload = json.loads(cache_file.read_text())
    assert payload["schema_version"] == 1
    assert payload["counts"]["total"] == 1
    assert payload["counts"]["passed"] == 1
    entry = payload["tests"][0]
    assert entry["test_id"] == "M1T-01"
    assert entry["passed"] is True
    assert entry["stdout"] is None  # passing tests hold no output blob
    assert entry["stderr"] is None


def test_cache_failure_includes_full_output(thoth_test_mod, tmp_path):
    # Unit-test the serializer with a synthetic failing result.
    runner = thoth_test_mod.TestRunner()
    runner.start_time = 0.0
    runner.filtered_tests = [
        thoth_test_mod.TestCase(test_id="F1", description="fail", command=["x"], provider="mock"),
    ]
    runner.results = [
        thoth_test_mod.TestResult(
            test_id="F1",
            passed=False,
            duration=0.1,
            stdout="big stdout payload",
            stderr="big stderr payload",
            exit_code=1,
            error_message="boom",
        )
    ]
    report = thoth_test_mod.serialize_run_report(runner, invocation=["./thoth_test", "-r"])
    [entry] = report["tests"]
    assert entry["passed"] is False
    assert entry["stdout"] == "big stdout payload"
    assert entry["stderr"] == "big stderr payload"
    assert report["schema_version"] == 1
    assert report["counts"]["failed"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_thoth_test_cli.py -k "cache" -v`
Expected: FAIL — `serialize_run_report` missing; cache file not written.

- [ ] **Step 3: Add serializer**

Add to `thoth_test` near line ~700 (next to the list printers):

```python
def serialize_run_report(runner: "TestRunner", invocation: list[str]) -> dict[str, Any]:
    started = getattr(runner, "_started_at_iso", None)
    finished = datetime.now(tz=__import__("datetime").timezone.utc).isoformat().replace("+00:00", "Z")
    duration_total = time.time() - runner.start_time

    counts = {
        "total": len(runner.results),
        "passed": sum(1 for r in runner.results if r.passed and not r.skipped),
        "failed": sum(1 for r in runner.results if not r.passed),
        "skipped": sum(1 for r in runner.results if r.skipped),
        "api_key_failures": sum(1 for r in runner.results if not r.passed and r.is_api_key_failure),
    }

    test_case_by_id = {tc.test_id: tc for tc in runner.filtered_tests}
    tests_payload = []
    for r in runner.results:
        tc = test_case_by_id.get(r.test_id)
        include_output = not r.passed and not r.skipped
        tests_payload.append({
            "test_id": r.test_id,
            "description": tc.description if tc else "",
            "provider": tc.provider if tc else None,
            "test_type": tc.test_type if tc else "subprocess",
            "passed": r.passed,
            "skipped": r.skipped,
            "duration_seconds": round(r.duration, 3),
            "exit_code": r.exit_code,
            "error_message": r.error_message,
            "is_api_key_failure": r.is_api_key_failure,
            "requested_but_filtered": bool(getattr(tc, "_requested_but_filtered", False)) if tc else False,
            "stdout": r.stdout if include_output else None,
            "stderr": r.stderr if include_output else None,
        })

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "started_at": started,
        "finished_at": finished,
        "duration_total_seconds": round(duration_total, 3),
        "invocation": invocation,
        "requested_providers": runner.requested_providers,
        "counts": counts,
        "tests": tests_payload,
    }


def write_cache_atomic(payload: dict[str, Any], path: Path = CACHE_FILE) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2))
        os.replace(tmp, path)
    except OSError as exc:
        console.print(f"[yellow]Warning: could not write {path}: {exc}[/yellow]")
```

Also in `TestRunner.__init__`, capture the start ISO timestamp:

```python
        self._started_at_iso = datetime.now(tz=__import__("datetime").timezone.utc).isoformat().replace("+00:00", "Z")
```

- [ ] **Step 4: Call it from `generate_report`**

At the very end of `generate_report`, **before** `sys.exit(...)`:

```python
        report = serialize_run_report(self, invocation=sys.argv)
        write_cache_atomic(report)
```

Cache invocation args come from `sys.argv` — that's the full CLI line as the user typed it, matching the spec.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_thoth_test_cli.py -k "cache" -v`
Expected: PASS (2 tests green).

- [ ] **Step 6: Regression check**

Run: `./thoth_test -r --provider mock --skip-interactive`
Expected: same counts as before; `.thoth_test_cache/last_run.json` exists and parses as JSON.

- [ ] **Step 7: Commit**

```bash
git add thoth_test tests/test_thoth_test_cli.py
git commit -m "feat(thoth_test): write last-run cache on every run"
```

---

## Task 6: Add `--last-failed`

**Files:**
- Modify: `thoth_test` — add cache reader; wire flag into resolver; exit 2 on missing/empty.
- Test: `tests/test_thoth_test_cli.py`

- [ ] **Step 1: Write failing tests**

Append:

```python
def test_last_failed_exits_2_when_no_cache(tmp_path):
    cache_file = REPO_ROOT / ".thoth_test_cache" / "last_run.json"
    if cache_file.exists():
        cache_file.unlink()
    proc = _run_thoth_test("-r", "--last-failed")
    assert proc.returncode == 2
    assert "no prior failures" in proc.stderr.lower()


def test_last_failed_reads_cache_and_reruns(tmp_path):
    # First, run a green test to populate cache with only passes.
    proc = _run_thoth_test("-r", "--id", "M1T-01")
    assert proc.returncode == 0
    # --last-failed against a cache with zero failures is also exit 2.
    proc2 = _run_thoth_test("-r", "--last-failed")
    assert proc2.returncode == 2
    assert "no prior failures" in proc2.stderr.lower()


def test_read_last_failed_returns_ids(thoth_test_mod, tmp_path):
    cache = tmp_path / "last_run.json"
    cache.write_text(json.dumps({
        "schema_version": 1,
        "tests": [
            {"test_id": "OK", "passed": True, "skipped": False},
            {"test_id": "BAD", "passed": False, "skipped": False},
        ],
    }))
    assert thoth_test_mod.read_last_failed(cache) == ["BAD"]


def test_read_last_failed_raises_on_missing(thoth_test_mod, tmp_path):
    with pytest.raises(FileNotFoundError):
        thoth_test_mod.read_last_failed(tmp_path / "nope.json")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_thoth_test_cli.py -k "last_failed" -v`
Expected: FAIL — `read_last_failed` and `--last-failed` flag don't exist.

- [ ] **Step 3: Add the cache reader**

Add to `thoth_test` near `write_cache_atomic`:

```python
def read_last_failed(path: Path = CACHE_FILE) -> list[str]:
    """Return test_ids of failing tests from the last run cache.

    Raises FileNotFoundError if the cache doesn't exist; returns [] if the
    cache exists but has no failures.
    """
    payload = json.loads(path.read_text())
    return [t["test_id"] for t in payload.get("tests", []) if not t.get("passed", True)]
```

- [ ] **Step 4: Add CLI option and wire into resolver**

Add to the `@click.command()` decorator chain:

```python
@click.option("--last-failed", "last_failed", is_flag=True, help="Rerun tests that failed in the most recent run.")
```

Add `last_failed` to the `main(...)` signature.

In `main()`, just after the existing `all` shorthand expansion:

```python
    if last_failed:
        try:
            failed_ids = read_last_failed()
        except FileNotFoundError:
            click.echo(
                "No prior failures to rerun (.thoth_test_cache/last_run.json missing or empty)",
                err=True,
            )
            sys.exit(2)
        if not failed_ids:
            click.echo(
                "No prior failures to rerun (.thoth_test_cache/last_run.json missing or empty)",
                err=True,
            )
            sys.exit(2)
        # Merge with any explicit --id (union).
        ids = tuple(list(ids) + [i for i in failed_ids if i not in ids])
        run = True  # --last-failed implies -r
```

Ensure this block runs **before** the `if not run:` help-and-exit check.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_thoth_test_cli.py -k "last_failed" -v`
Expected: PASS (4 tests green).

- [ ] **Step 6: Commit**

```bash
git add thoth_test tests/test_thoth_test_cli.py
git commit -m "feat(thoth_test): add --last-failed to rerun prior failures"
```

---

## Task 7: Add `--report-json PATH`

**Files:**
- Modify: `thoth_test` — accept `--report-json` and write the same payload atomically to the chosen path.
- Test: `tests/test_thoth_test_cli.py`

- [ ] **Step 1: Write failing tests**

Append:

```python
def test_report_json_writes_to_given_path(tmp_path):
    target = tmp_path / "run.json"
    proc = _run_thoth_test("-r", "--id", "M1T-01", "--report-json", str(target))
    assert proc.returncode == 0
    assert target.exists()
    payload = json.loads(target.read_text())
    assert payload["schema_version"] == 1
    assert payload["counts"]["total"] == 1


def test_report_json_matches_cache_content(tmp_path):
    target = tmp_path / "run.json"
    proc = _run_thoth_test("-r", "--id", "M1T-01", "--report-json", str(target))
    assert proc.returncode == 0
    cache_file = REPO_ROOT / ".thoth_test_cache" / "last_run.json"
    assert cache_file.exists()
    cache_payload = json.loads(cache_file.read_text())
    target_payload = json.loads(target.read_text())
    # finished_at may differ by one clock tick between writes; compare everything else.
    for key in ("schema_version", "invocation", "requested_providers", "counts", "tests"):
        assert cache_payload[key] == target_payload[key], f"mismatch on {key}"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_thoth_test_cli.py -k "report_json" -v`
Expected: FAIL — `--report-json` not recognized.

- [ ] **Step 3: Add CLI option and writer call**

Add to the `@click.command()` decorator chain:

```python
@click.option("--report-json", "report_json", type=click.Path(dir_okay=False), default=None, help="Also write the JSON report to PATH.")
```

Add `report_json` to the `main(...)` signature.

In `generate_report`, after the existing `write_cache_atomic(report)` line:

```python
        if getattr(self, "_report_json_path", None):
            write_cache_atomic(report, Path(self._report_json_path))
```

Plumb the path into the runner — in `main()` where `TestRunner(...)` is instantiated:

```python
    runner = TestRunner(
        verbose=verbose,
        save_output=save_output,
        requested_providers=requested_providers,
    )
    runner._report_json_path = report_json
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_thoth_test_cli.py -k "report_json" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add thoth_test tests/test_thoth_test_cli.py
git commit -m "feat(thoth_test): add --report-json for on-demand JSON export"
```

---

## Task 8: Add `-q` / `--quiet` with fenced failure blocks

**Files:**
- Modify: `thoth_test` — quiet branch in `run_all_tests` and `generate_report`; fenced printer.
- Test: `tests/test_thoth_test_cli.py` (also unskip the Task 4 integration test)

- [ ] **Step 1: Write failing tests**

Append:

```python
def test_quiet_suppresses_table_on_pass():
    proc = _run_thoth_test("-r", "--id", "M1T-01", "-q")
    assert proc.returncode == 0
    # The default-mode Results Table has a "Test Results" caption.
    assert "Test Results" not in proc.stdout
    # Summary line shape — "N passed, M failed, K skipped in X.Ys"
    assert "1 passed" in proc.stdout
    assert "0 failed" in proc.stdout
    assert ".thoth_test_cache/last_run.json" in proc.stdout


def test_quiet_emits_fenced_failure_for_failing_test(thoth_test_mod, capsys):
    runner = thoth_test_mod.TestRunner(quiet=True)
    runner.start_time = 0.0
    runner.filtered_tests = [
        thoth_test_mod.TestCase(
            test_id="FAIL-1",
            description="deliberate failure",
            command=["x"],
            provider="mock",
        )
    ]
    runner.results = [
        thoth_test_mod.TestResult(
            test_id="FAIL-1",
            passed=False,
            duration=0.5,
            stdout="STDOUT-MARKER",
            stderr="STDERR-MARKER",
            exit_code=1,
            error_message="boom",
        )
    ]
    # Avoid sys.exit from generate_report.
    with pytest.raises(SystemExit):
        runner.generate_report()
    out = capsys.readouterr().out
    assert "===BEGIN FAILURE FAIL-1===" in out
    assert "===END FAILURE FAIL-1===" in out
    assert "STDOUT-MARKER" in out
    assert "STDERR-MARKER" in out
    # Table is suppressed in quiet mode.
    assert "Test Results" not in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_thoth_test_cli.py -k "quiet" -v`
Expected: FAIL — `quiet` kwarg missing; `-q` not recognized.

- [ ] **Step 3: Add the fenced printer**

Add to `thoth_test` near the list printers:

```python
def print_fenced_failure(result: TestResult, test_case: TestCase | None) -> None:
    desc = test_case.description if test_case else ""
    sys.stdout.write(f"===BEGIN FAILURE {result.test_id}===\n")
    sys.stdout.write(f"Test: {result.test_id} — {desc}\n")
    sys.stdout.write(f"Duration: {result.duration:.2f}s\n")
    sys.stdout.write(f"Exit code: {result.exit_code}\n")
    sys.stdout.write(f"Error: {result.error_message or ''}\n")
    sys.stdout.write("--- STDOUT ---\n")
    sys.stdout.write((result.stdout or "") + ("\n" if not (result.stdout or "").endswith("\n") else ""))
    sys.stdout.write("--- STDERR ---\n")
    sys.stdout.write((result.stderr or "") + ("\n" if not (result.stderr or "").endswith("\n") else ""))
    sys.stdout.write(f"===END FAILURE {result.test_id}===\n")
```

- [ ] **Step 4: Wire `-q` through `TestRunner` and `generate_report`**

Add `quiet: bool = False` to `TestRunner.__init__`, store as `self.quiet = quiet`.

In `run_all_tests`, branch on `self.quiet`:

```python
        if self.quiet:
            for test_case in test_cases:
                result = self.run_test(test_case)
                self.results.append(result)
        else:
            # existing Progress-bar loop
```

In `generate_report`, at the top:

```python
        if self.quiet:
            self._generate_quiet_report()
            return
```

Add a new method `_generate_quiet_report`:

```python
    def _generate_quiet_report(self):
        total_time = time.time() - self.start_time
        passed = sum(1 for r in self.results if r.passed and not r.skipped)
        failed = sum(1 for r in self.results if not r.passed)
        skipped = sum(1 for r in self.results if r.skipped)

        tc_by_id = {tc.test_id: tc for tc in self.filtered_tests}
        for r in self.results:
            if not r.passed:
                print_fenced_failure(r, tc_by_id.get(r.test_id))

        sys.stdout.write(
            f"thoth_test: {passed} passed, {failed} failed, {skipped} skipped "
            f"in {total_time:.1f}s (cache: {CACHE_FILE})\n"
        )

        report = serialize_run_report(self, invocation=sys.argv)
        write_cache_atomic(report)
        if getattr(self, "_report_json_path", None):
            write_cache_atomic(report, Path(self._report_json_path))

        sys.exit(0 if failed == 0 else 1)
```

- [ ] **Step 5: Add `-q` CLI option**

Add to the `@click.command()` decorator chain:

```python
@click.option("-q", "--quiet", "quiet", is_flag=True, help="Silent on pass; fenced failure blocks on fail.")
```

Add `quiet` to the `main(...)` signature. Pass through:

```python
    runner = TestRunner(
        verbose=verbose,
        save_output=save_output,
        requested_providers=requested_providers,
        quiet=quiet,
    )
```

- [ ] **Step 6: Unskip the Task 4 integration test**

Remove `@pytest.mark.skip(...)` from `test_id_integration_runs_exactly_one_test`.

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run pytest tests/test_thoth_test_cli.py -v`
Expected: every test passes (all 15+).

- [ ] **Step 8: Regression check**

Run: `./thoth_test -r --provider mock --skip-interactive`
Expected: same default-mode output as before the bundle; exit 0.

Run: `./thoth_test -r --provider mock --skip-interactive -q`
Expected: one summary line only (no table, no progress bar); exit 0.

- [ ] **Step 9: Commit**

```bash
git add thoth_test tests/test_thoth_test_cli.py
git commit -m "feat(thoth_test): add -q/--quiet mode with fenced failure blocks"
```

---

## Task 9: Update `CLAUDE.md` to use the new flags

**Files:**
- Modify: `CLAUDE.md` — replace grep-workaround guidance with direct flag usage.

- [ ] **Step 1: Replace the grep snippet**

In `CLAUDE.md`, find this block (under "Finding test IDs to rerun"):

````markdown
When a pre-commit hook fails on `./thoth_test`, grep to skip the 64-row
noise table:

```bash
./thoth_test -r --provider mock --skip-interactive 2>&1 | grep -A 30 "Failed Test Details"
```
````

Replace with:

````markdown
When a pre-commit hook fails on `./thoth_test`, use quiet mode to get just
the fenced failure blocks (no 64-row noise table):

```bash
./thoth_test -r --provider mock --skip-interactive -q
```

To rerun only what just failed:

```bash
./thoth_test -r --last-failed -q
```

To pick a specific test by exact ID:

```bash
./thoth_test -r --id M8T-03 -v
```
````

- [ ] **Step 2: Add discovery note**

Immediately before "### Flaky-test retry policy", add:

```markdown
### Discovering tests without running them

- TSV list: `./thoth_test --list`
- JSON list: `./thoth_test --list-json`
- Preview a filter: `./thoth_test --list --provider mock`
- Machine-readable run report is always at `.thoth_test_cache/last_run.json`
  (schema_version 1). Use `--report-json PATH` to also write a copy elsewhere.
```

- [ ] **Step 3: Soften the "two consecutive failures" guidance**

Find "Two consecutive failures of the same test = real bug." — keep it, but add a pointer:

```markdown
For flaky network tests, prefer `./thoth_test -r --last-failed -q` over
re-running the full suite.
```

- [ ] **Step 4: Verify no other parts of CLAUDE.md reference the old grep pattern**

Run: `grep -n "grep -A 30 \"Failed Test Details\"" CLAUDE.md`
Expected: no matches.

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude): use new thoth_test flags instead of grep workarounds"
```

---

## Final Verification

- [ ] **Run the full suite**

```bash
./thoth_test -r --provider mock --skip-interactive
```
Expected: same PASS count as pre-bundle baseline.

- [ ] **Run the pytest suite**

```bash
uv run pytest tests/test_thoth_test_cli.py -v
```
Expected: all tests green.

- [ ] **Run `just check`**

```bash
just check
```
Expected: lint + typecheck clean.

- [ ] **Manual smoke test of every new flag**

```bash
./thoth_test --list | head -5
./thoth_test --list-json | python -m json.tool | head -20
./thoth_test -r --id M1T-01 -q
./thoth_test -r --last-failed -q   # expect exit 2 with helpful message
./thoth_test -r --id M1T-01 --report-json /tmp/report.json && cat /tmp/report.json | python -m json.tool | head
```

---

## Self-Review

- **Spec coverage:** every Q1–Q5 decision is implemented (scope C, cache-by-default B, --id overrides B, -q silent-on-pass B, full stdout for failures only C). Fenced sentinels, mutual exclusion, exit code 2 — all covered.
- **Placeholder scan:** no "TBD", no "handle edge cases", no free-floating references. Every step has the code it needs.
- **Type consistency:** `resolve_selection` signature is identical across Tasks 2 and 4 (only the body is extended). `TestRunner.__init__` gains `quiet: bool = False` in Task 8 only — nothing earlier depends on it. `serialize_run_report` signature fixed in Task 5 and used unchanged in Tasks 7 and 8.
- **Commit sequence:** each task ends with a conventional-commit commit, matching the rollout plan in the spec.
