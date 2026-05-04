# P31 — Interactive Init Wizard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the "Interactive setup wizard not yet implemented" placeholder in `init_command()` with a real wizard that collects providers, API-key strategy, and default mode, then writes the resulting TOML config — preserving unknown sections on `--force` round-trips.

**Architecture:** A new `src/thoth/init_wizard.py` module owns all interactive prompting and returns a frozen `WizardAnswers` dataclass. `init_command()` in `commands.py` becomes a dispatcher that picks between the existing static-starter path (non-interactive / JSON) and the wizard path. The wizard accepts an injected `prompt_fn` and `env` mapping so unit tests never touch real stdin or `os.environ`. A new `_apply_wizard_answers(doc, answers)` helper merges answers into a `tomlkit` document, used by both fresh-doc and `--force` round-trip writes.

**Tech Stack:** Python 3.11+, Click (CLI), `rich.prompt` (text prompts), `tomlkit` (round-trip TOML), `pytest`, `pexpect` (thoth_test integration).

**Spec:** [docs/superpowers/specs/2026-05-03-p31-interactive-init-design.md](../specs/2026-05-03-p31-interactive-init-design.md)

---

## File structure

| File | Status | Responsibility |
|---|---|---|
| `src/thoth/init_wizard.py` | **new** | `WizardAnswers` and `ProviderChoice` dataclasses. `run()` entry point. Q1/Q2/Q3 prompt helpers. Numbered-list helper. Review-and-confirm loop. `ScriptedPrompts` test harness lives next to it but is exported under a `_testing` submodule path so production imports don't pull it in. |
| `src/thoth/commands.py` | **modify** | `init_command` becomes a dispatcher. Add `_apply_wizard_answers(doc, answers)` and `_load_or_build_doc(target, force)` helpers. Replace lines 217–224 (placeholder + write) with a branch that calls the wizard or falls through to the static path. |
| `tests/test_init_wizard.py` | **new** | Unit-tests for the wizard module: TS01-a through TS01-k (the wizard-internal cases). Uses a deterministic `ScriptedPrompts` stub. |
| `tests/test_init_command_dispatch.py` | **new** | Dispatcher-level tests: TS01-l (`--non-interactive` skips wizard), TS01-m (`--json` envelope regression), `--force` round-trip preserves unknown sections. |
| `thoth_test` | **modify** | Add one `pexpect`-driven case `M2T-INTERACTIVE-INIT` that scripts the wizard against the real binary. |
| `projects/P31-interactive-init-command.md` | **modify** | Flip TS01/T01/T02 status as work lands. |
| `PROJECTS.md` | **modify** | Update P31 trunk row glyph from `[ ]` to `[~]` (in progress) and to `[x]` at the end. |

---

## Task 0: Bootstrap — flip P31 to in-progress

**Files:**
- Modify: `PROJECTS.md`
- Modify: `projects/P31-interactive-init-command.md`

- [ ] **Step 1: Mark P31 in progress on the trunk**

In `PROJECTS.md`, locate the line:

```markdown
- [ ] **P31** — [Interactive Init Command](projects/P31-interactive-init-command.md)
```

Change to:

```markdown
- [~] **P31** — [Interactive Init Command](projects/P31-interactive-init-command.md)
```

- [ ] **Step 2: Add Spec/Plan refs to the project file**

In `projects/P31-interactive-init-command.md`, replace the `**References**` block:

```markdown
**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)
```

with:

```markdown
**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)
- **Spec:** `docs/superpowers/specs/2026-05-03-p31-interactive-init-design.md`
- **Plan:** `docs/superpowers/plans/2026-05-03-p31-interactive-init.md`
```

Also change `**Status:** `[ ]` Scoped, not started.` to `**Status:** `[~]` In progress.`

- [ ] **Step 3: Commit**

```bash
git add PROJECTS.md projects/P31-interactive-init-command.md
git commit -m "chore(p31): flip to in-progress, link spec + plan"
```

---

## Task 1: Wizard data model + ScriptedPrompts harness (TDD)

Define the dataclasses and the test stub. No prompt logic yet. This task delivers the contract every later task relies on.

**Files:**
- Create: `src/thoth/init_wizard.py`
- Create: `tests/test_init_wizard.py`

- [ ] **Step 1: Write failing test for `WizardAnswers` shape**

Create `tests/test_init_wizard.py`:

```python
"""Unit tests for src/thoth/init_wizard.py — P31."""

from __future__ import annotations

from pathlib import Path

import pytest

from thoth.init_wizard import ProviderChoice, ScriptedPrompts, WizardAnswers


def test_provider_choice_is_frozen() -> None:
    pc = ProviderChoice(name="openai", storage="env_ref", literal_value=None)
    with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
        pc.name = "gemini"  # type: ignore[misc]


def test_wizard_answers_is_frozen(tmp_path: Path) -> None:
    a = WizardAnswers(
        providers=(ProviderChoice("openai", "env_ref", None),),
        default_mode="thinking",
        target_path=tmp_path / "thoth.config.toml",
    )
    with pytest.raises(Exception):
        a.default_mode = "default"  # type: ignore[misc]


def test_scripted_prompts_returns_in_order() -> None:
    sp = ScriptedPrompts(["a", "b", "c"])
    assert sp("ignored prompt") == "a"
    assert sp("ignored prompt") == "b"
    assert sp("ignored prompt") == "c"


def test_scripted_prompts_raises_when_exhausted() -> None:
    sp = ScriptedPrompts(["only"])
    sp("p")
    with pytest.raises(AssertionError, match="ScriptedPrompts exhausted"):
        sp("p2")
```

- [ ] **Step 2: Run test to confirm it fails**

Run: `uv run pytest tests/test_init_wizard.py -v`
Expected: `ImportError` / `ModuleNotFoundError` for `thoth.init_wizard`.

- [ ] **Step 3: Create the wizard module skeleton**

Create `src/thoth/init_wizard.py`:

```python
"""Interactive `thoth init` wizard — P31.

Module is intentionally I/O-free. `run()` returns `WizardAnswers`; the
caller in `commands.py` is responsible for merging answers into a
`tomlkit` document and writing the file.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

PromptFn = Callable[[str], str]
ProviderName = Literal["openai", "perplexity", "gemini"]
KeyStorage = Literal["env_ref", "literal", "skip"]
DefaultMode = Literal["default", "thinking", "deep_research", "interactive"]


@dataclass(frozen=True)
class ProviderChoice:
    name: ProviderName
    storage: KeyStorage
    literal_value: str | None  # set only when storage == "literal"


@dataclass(frozen=True)
class WizardAnswers:
    providers: tuple[ProviderChoice, ...]
    default_mode: DefaultMode
    target_path: Path


class ScriptedPrompts:
    """Deterministic stub for `prompt_fn` in tests.

    Each call returns the next scripted answer. Raises AssertionError if
    drained — that catches tests that wire fewer answers than the wizard
    actually asks for.
    """

    def __init__(self, answers: list[str]) -> None:
        self._answers = list(answers)
        self._idx = 0

    def __call__(self, _prompt: str) -> str:
        assert self._idx < len(self._answers), (
            f"ScriptedPrompts exhausted after {self._idx} answers"
        )
        reply = self._answers[self._idx]
        self._idx += 1
        return reply
```

- [ ] **Step 4: Run tests to confirm they pass**

Run: `uv run pytest tests/test_init_wizard.py -v`
Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/thoth/init_wizard.py tests/test_init_wizard.py
git commit -m "feat(p31): add WizardAnswers/ProviderChoice + ScriptedPrompts harness"
```

---

## Task 2: Numbered-list helper

A small reusable primitive used by Q1, Q2 (per-provider 3-way choice), and Q3. Test it independently because the failure modes (malformed input, empty input, retry exhaustion) live here.

**Files:**
- Modify: `src/thoth/init_wizard.py`
- Modify: `tests/test_init_wizard.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_init_wizard.py`:

```python
from thoth.init_wizard import pick_one, pick_many
from thoth.errors import ThothError


def test_pick_one_returns_indexed_value() -> None:
    sp = ScriptedPrompts(["2"])
    assert pick_one(["a", "b", "c"], prompt_fn=sp, default_index=0) == "b"


def test_pick_one_default_on_empty_input() -> None:
    sp = ScriptedPrompts([""])
    assert pick_one(["a", "b", "c"], prompt_fn=sp, default_index=2) == "c"


def test_pick_one_retries_then_errors_on_garbage() -> None:
    sp = ScriptedPrompts(["x", "0", "99"])  # 3 bad answers
    with pytest.raises(ThothError, match="invalid selection"):
        pick_one(["a", "b"], prompt_fn=sp, default_index=0)


def test_pick_many_parses_comma_input() -> None:
    sp = ScriptedPrompts(["1,3"])
    assert pick_many(["a", "b", "c"], prompt_fn=sp) == ["a", "c"]


def test_pick_many_handles_whitespace() -> None:
    sp = ScriptedPrompts([" 1 , 2 "])
    assert pick_many(["a", "b", "c"], prompt_fn=sp) == ["a", "b"]


def test_pick_many_dedupes_preserves_order() -> None:
    sp = ScriptedPrompts(["3,1,3"])
    assert pick_many(["a", "b", "c"], prompt_fn=sp) == ["c", "a"]


def test_pick_many_empty_returns_empty_list() -> None:
    sp = ScriptedPrompts(["", ""])  # 2 empty re-prompts then accept
    assert pick_many(["a", "b"], prompt_fn=sp) == []
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `uv run pytest tests/test_init_wizard.py -v -k "pick_"`
Expected: ImportError for `pick_one` / `pick_many`.

- [ ] **Step 3: Implement helpers in `src/thoth/init_wizard.py`**

Add to `src/thoth/init_wizard.py`:

```python
from thoth.errors import ThothError

_MAX_RETRIES = 3


def _format_menu(options: list[str]) -> str:
    return "\n".join(f"  {i + 1}) {opt}" for i, opt in enumerate(options))


def pick_one(
    options: list[str],
    *,
    prompt_fn: PromptFn,
    default_index: int,
    label: str = "Choose",
) -> str:
    """Render a numbered list, return the user's pick.

    `default_index` is the 0-based index that an empty input maps to.
    Retries up to `_MAX_RETRIES` times on garbage input, then raises.
    """
    menu = _format_menu(options)
    default_label = options[default_index]
    full_prompt = f"{label}:\n{menu}\n[default: {default_label}] > "
    for _ in range(_MAX_RETRIES):
        raw = prompt_fn(full_prompt).strip()
        if not raw:
            return options[default_index]
        try:
            n = int(raw)
        except ValueError:
            continue
        if 1 <= n <= len(options):
            return options[n - 1]
    raise ThothError("invalid selection")


def pick_many(
    options: list[str],
    *,
    prompt_fn: PromptFn,
    label: str = "Choose (comma-separated)",
) -> list[str]:
    """Render a numbered list, parse comma-separated picks.

    Empty input re-prompts once. A second empty input returns `[]`
    (interpreted as "skip all" by the caller).
    """
    menu = _format_menu(options)
    full_prompt = f"{label}:\n{menu}\n> "
    for empty_seen in range(2):
        raw = prompt_fn(full_prompt).strip()
        if not raw:
            if empty_seen == 1:
                return []
            continue
        picked: list[str] = []
        seen: set[int] = set()
        valid = True
        for part in raw.split(","):
            part = part.strip()
            try:
                n = int(part)
            except ValueError:
                valid = False
                break
            if not (1 <= n <= len(options)):
                valid = False
                break
            if n not in seen:
                seen.add(n)
                picked.append(options[n - 1])
        if valid and picked:
            return picked
        # garbage → loop again as if empty (but consume retry budget)
    raise ThothError("invalid selection")
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_init_wizard.py -v -k "pick_"`
Expected: 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/thoth/init_wizard.py tests/test_init_wizard.py
git commit -m "feat(p31): add pick_one/pick_many numbered-list helpers"
```

---

## Task 3: Q1 — provider multi-select

**Files:**
- Modify: `src/thoth/init_wizard.py`
- Modify: `tests/test_init_wizard.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_init_wizard.py`:

```python
from thoth.init_wizard import prompt_providers


def test_prompt_providers_picks_openai_only() -> None:
    sp = ScriptedPrompts(["1"])
    picks = prompt_providers(prompt_fn=sp)
    assert picks == ["openai"]


def test_prompt_providers_multi_input() -> None:
    sp = ScriptedPrompts(["1,3"])
    assert prompt_providers(prompt_fn=sp) == ["openai", "gemini"]


def test_prompt_providers_skip_all_picks_skip() -> None:
    # 4 = "skip all" sentinel — distinct from empty input
    sp = ScriptedPrompts(["4"])
    assert prompt_providers(prompt_fn=sp) == []


def test_prompt_providers_empty_then_empty_is_skip_all() -> None:
    sp = ScriptedPrompts(["", ""])
    assert prompt_providers(prompt_fn=sp) == []
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `uv run pytest tests/test_init_wizard.py -v -k "prompt_providers"`
Expected: ImportError.

- [ ] **Step 3: Implement**

Add to `src/thoth/init_wizard.py`:

```python
PROVIDER_OPTIONS: tuple[ProviderName, ...] = ("openai", "perplexity", "gemini")
ENV_VAR_BY_PROVIDER: dict[ProviderName, str] = {
    "openai": "OPENAI_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


def prompt_providers(*, prompt_fn: PromptFn) -> list[ProviderName]:
    """Q1: render provider multi-select, return picked provider names.

    The user can pick by number (`1,3`) or pick option 4 ("skip all").
    Two consecutive empty inputs collapse to "skip all" — see spec
    'Empty Q1 selection' edge case.
    """
    options = [*PROVIDER_OPTIONS, "skip all"]
    picks = pick_many(options, prompt_fn=prompt_fn, label="Pick providers")
    if not picks or "skip all" in picks:
        return []
    # mypy: pick_many returns list[str]; narrow to ProviderName
    return [p for p in picks if p in PROVIDER_OPTIONS]  # type: ignore[misc]
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_init_wizard.py -v -k "prompt_providers"`
Expected: 4 pass.

- [ ] **Step 5: Commit**

```bash
git add src/thoth/init_wizard.py tests/test_init_wizard.py
git commit -m "feat(p31): add Q1 provider multi-select prompt"
```

---

## Task 4: Q2 — per-provider key storage

**Files:**
- Modify: `src/thoth/init_wizard.py`
- Modify: `tests/test_init_wizard.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_init_wizard.py`:

```python
from thoth.init_wizard import prompt_key_for_provider


def test_key_env_detected_user_accepts() -> None:
    sp = ScriptedPrompts(["y"])  # accept env-var
    pc = prompt_key_for_provider(
        provider="openai",
        env={"OPENAI_API_KEY": "sk-test-12345"},
        prompt_fn=sp,
    )
    assert pc == ProviderChoice("openai", "env_ref", None)


def test_key_env_detected_user_rejects_pastes_literal() -> None:
    sp = ScriptedPrompts(["n", "1", "sk-mine"])
    pc = prompt_key_for_provider(
        provider="openai",
        env={"OPENAI_API_KEY": "sk-other"},
        prompt_fn=sp,
    )
    assert pc == ProviderChoice("openai", "literal", "sk-mine")


def test_key_env_missing_paste_literal() -> None:
    sp = ScriptedPrompts(["1", "sk-paste"])  # paste-now branch
    pc = prompt_key_for_provider(
        provider="perplexity",
        env={},
        prompt_fn=sp,
    )
    assert pc == ProviderChoice("perplexity", "literal", "sk-paste")


def test_key_env_missing_user_will_set_env_later() -> None:
    sp = ScriptedPrompts(["2"])  # env-ref-without-current-value branch
    pc = prompt_key_for_provider(
        provider="gemini",
        env={},
        prompt_fn=sp,
    )
    assert pc == ProviderChoice("gemini", "env_ref", None)


def test_key_env_missing_skip() -> None:
    sp = ScriptedPrompts(["3"])
    pc = prompt_key_for_provider(
        provider="openai",
        env={},
        prompt_fn=sp,
    )
    assert pc == ProviderChoice("openai", "skip", None)


def test_key_env_empty_string_treated_as_missing() -> None:
    sp = ScriptedPrompts(["1", "sk-paste"])
    pc = prompt_key_for_provider(
        provider="openai",
        env={"OPENAI_API_KEY": ""},  # empty string ≠ set
        prompt_fn=sp,
    )
    assert pc == ProviderChoice("openai", "literal", "sk-paste")


def test_key_literal_value_trimmed_once() -> None:
    sp = ScriptedPrompts(["1", "  sk-pad  "])
    pc = prompt_key_for_provider(
        provider="openai",
        env={},
        prompt_fn=sp,
    )
    assert pc == ProviderChoice("openai", "literal", "sk-pad")
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `uv run pytest tests/test_init_wizard.py -v -k "test_key_"`
Expected: ImportError.

- [ ] **Step 3: Implement**

Add to `src/thoth/init_wizard.py`:

```python
def _last4(value: str) -> str:
    return value[-4:] if len(value) >= 4 else "***"


def prompt_key_for_provider(
    *,
    provider: ProviderName,
    env: dict[str, str],
    prompt_fn: PromptFn,
) -> ProviderChoice:
    """Q2: detect-then-decide for one provider's API key."""
    var = ENV_VAR_BY_PROVIDER[provider]
    detected = env.get(var, "")
    if detected:
        reply = prompt_fn(
            f"${var} detected (...{_last4(detected)}) — use it? [Y/n] "
        ).strip().lower()
        if reply in ("", "y", "yes"):
            return ProviderChoice(provider, "env_ref", None)
        # fall through to the missing-env branch
    options = [
        f"Paste {var} now (stored in this file)",
        f"I'll set ${var} myself (write '${{{var}}}' reference)",
        "Skip this provider",
    ]
    pick = pick_one(
        options, prompt_fn=prompt_fn, default_index=0, label=f"{provider} key"
    )
    if pick == options[0]:
        raw = prompt_fn(f"Paste {var}: ")
        return ProviderChoice(provider, "literal", raw.strip())
    if pick == options[1]:
        return ProviderChoice(provider, "env_ref", None)
    return ProviderChoice(provider, "skip", None)
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_init_wizard.py -v -k "test_key_"`
Expected: 7 pass.

- [ ] **Step 5: Commit**

```bash
git add src/thoth/init_wizard.py tests/test_init_wizard.py
git commit -m "feat(p31): add Q2 per-provider key storage prompt"
```

---

## Task 5: Q3 — default-mode pick

**Files:**
- Modify: `src/thoth/init_wizard.py`
- Modify: `tests/test_init_wizard.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_init_wizard.py`:

```python
from thoth.init_wizard import prompt_default_mode


def test_default_mode_pick_thinking() -> None:
    sp = ScriptedPrompts(["2"])
    assert prompt_default_mode(prompt_fn=sp, current="default") == "thinking"


def test_default_mode_empty_keeps_current() -> None:
    sp = ScriptedPrompts([""])
    assert prompt_default_mode(prompt_fn=sp, current="deep_research") == "deep_research"


def test_default_mode_empty_with_no_current_uses_default() -> None:
    sp = ScriptedPrompts([""])
    assert prompt_default_mode(prompt_fn=sp, current=None) == "default"
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `uv run pytest tests/test_init_wizard.py -v -k "default_mode"`
Expected: ImportError.

- [ ] **Step 3: Implement**

Add to `src/thoth/init_wizard.py`:

```python
DEFAULT_MODE_OPTIONS: tuple[DefaultMode, ...] = (
    "default",
    "thinking",
    "deep_research",
    "interactive",
)
DEFAULT_MODE_DESCRIPTIONS: dict[DefaultMode, str] = {
    "default": "default — the shipped research mode",
    "thinking": "thinking — fast / cheap reasoning",
    "deep_research": "deep_research — multi-provider deep research",
    "interactive": "interactive — drop into REPL on bare `thoth`",
}


def prompt_default_mode(
    *, prompt_fn: PromptFn, current: DefaultMode | None
) -> DefaultMode:
    """Q3: pick general.default_mode."""
    descs = [DEFAULT_MODE_DESCRIPTIONS[m] for m in DEFAULT_MODE_OPTIONS]
    base = current if current in DEFAULT_MODE_OPTIONS else "default"
    default_index = DEFAULT_MODE_OPTIONS.index(base)
    label = "Default mode"
    chosen_desc = pick_one(
        descs, prompt_fn=prompt_fn, default_index=default_index, label=label
    )
    return DEFAULT_MODE_OPTIONS[descs.index(chosen_desc)]
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_init_wizard.py -v -k "default_mode"`
Expected: 3 pass.

- [ ] **Step 5: Commit**

```bash
git add src/thoth/init_wizard.py tests/test_init_wizard.py
git commit -m "feat(p31): add Q3 default-mode pick"
```

---

## Task 6: Review-and-confirm + `run()` entry

Pulls Q1–Q3 together with the review screen and the cancel/edit/write loop. This is the wizard's public entry point.

**Files:**
- Modify: `src/thoth/init_wizard.py`
- Modify: `tests/test_init_wizard.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_init_wizard.py`:

```python
from thoth.init_wizard import run


def test_run_happy_path_openai_only(tmp_path: Path) -> None:
    answers = run(
        target=tmp_path / "thoth.config.toml",
        prefill=None,
        prompt_fn=ScriptedPrompts(
            [
                "1",  # Q1: openai only
                "y",  # Q2: use $OPENAI_API_KEY
                "2",  # Q3: thinking
                "y",  # review: write
            ]
        ),
        env={"OPENAI_API_KEY": "sk-test"},
    )
    assert answers is not None
    assert answers.providers == (ProviderChoice("openai", "env_ref", None),)
    assert answers.default_mode == "thinking"


def test_run_review_cancel_returns_none(tmp_path: Path) -> None:
    result = run(
        target=tmp_path / "thoth.config.toml",
        prefill=None,
        prompt_fn=ScriptedPrompts(["4", "1", "n"]),  # skip all, mode default, cancel
        env={},
    )
    assert result is None


def test_run_review_edit_reprompts(tmp_path: Path) -> None:
    answers = run(
        target=tmp_path / "thoth.config.toml",
        prefill=None,
        prompt_fn=ScriptedPrompts(
            [
                # First pass
                "1",  # openai
                "y",  # env-var
                "1",  # default mode
                "e",  # edit
                # Second pass
                "2",  # perplexity
                "y",  # env-var
                "2",  # thinking
                "y",  # write
            ]
        ),
        env={"OPENAI_API_KEY": "sk-1", "PERPLEXITY_API_KEY": "sk-2"},
    )
    assert answers is not None
    assert answers.providers == (ProviderChoice("perplexity", "env_ref", None),)
    assert answers.default_mode == "thinking"


def test_run_keyboard_interrupt_aborts(tmp_path: Path) -> None:
    import click

    def boom(_: str) -> str:
        raise KeyboardInterrupt

    with pytest.raises(click.Abort):
        run(
            target=tmp_path / "thoth.config.toml",
            prefill=None,
            prompt_fn=boom,
            env={},
        )


def test_run_skip_all_zero_providers(tmp_path: Path) -> None:
    answers = run(
        target=tmp_path / "thoth.config.toml",
        prefill=None,
        prompt_fn=ScriptedPrompts(["4", "1", "y"]),  # skip all, default, write
        env={},
    )
    assert answers is not None
    assert answers.providers == ()
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `uv run pytest tests/test_init_wizard.py -v -k "test_run_"`
Expected: ImportError for `run`.

- [ ] **Step 3: Implement**

Add to `src/thoth/init_wizard.py`:

```python
import click


@dataclass(frozen=True)
class _Prefill:
    providers: tuple[ProviderChoice, ...] = ()
    default_mode: DefaultMode | None = None


def _format_review(answers: WizardAnswers) -> str:
    lines = [f"Target: {answers.target_path}"]
    if not answers.providers:
        lines.append("Providers: (none — `${ENV}` references kept as-is)")
    else:
        for p in answers.providers:
            if p.storage == "env_ref":
                lines.append(f"  {p.name} → ${ENV_VAR_BY_PROVIDER[p.name]}")
            elif p.storage == "literal":
                tail = _last4(p.literal_value or "")
                lines.append(f"  {p.name} → literal (...{tail})")
            else:
                lines.append(f"  {p.name} → skip")
    lines.append(f"Default mode: {answers.default_mode}")
    return "\n".join(lines)


def _collect(
    *,
    target: Path,
    prefill: _Prefill,
    prompt_fn: PromptFn,
    env: dict[str, str],
) -> WizardAnswers:
    picked = prompt_providers(prompt_fn=prompt_fn)
    provider_choices: list[ProviderChoice] = []
    for name in picked:
        provider_choices.append(
            prompt_key_for_provider(provider=name, env=env, prompt_fn=prompt_fn)
        )
    default_mode = prompt_default_mode(
        prompt_fn=prompt_fn, current=prefill.default_mode
    )
    return WizardAnswers(
        providers=tuple(provider_choices),
        default_mode=default_mode,
        target_path=target,
    )


def run(
    *,
    target: Path,
    prefill: _Prefill | None,
    prompt_fn: PromptFn,
    env: dict[str, str],
) -> WizardAnswers | None:
    """Run the interactive wizard. Return answers, or None if cancelled.

    `prefill` carries values from an existing TOML file when `--force` is
    passed. None means a clean run.
    """
    pf = prefill or _Prefill()
    try:
        while True:
            answers = _collect(
                target=target, prefill=pf, prompt_fn=prompt_fn, env=env
            )
            review = _format_review(answers)
            decision = prompt_fn(
                f"\n{review}\n\nWrite this? [Y]es / [n]o / [e]dit > "
            ).strip().lower()
            if decision in ("", "y", "yes"):
                return answers
            if decision in ("n", "no"):
                return None
            # treat anything else as edit; loop
            pf = _Prefill(
                providers=answers.providers,
                default_mode=answers.default_mode,
            )
    except KeyboardInterrupt:
        click.echo("Init cancelled.", err=True)
        raise click.Abort() from None
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_init_wizard.py -v -k "test_run_"`
Expected: 5 pass.

- [ ] **Step 5: Commit**

```bash
git add src/thoth/init_wizard.py tests/test_init_wizard.py
git commit -m "feat(p31): add run() entry with review-and-confirm loop"
```

---

## Task 7: `_apply_wizard_answers` — merge into tomlkit doc

This is the bridge between the wizard and the file. Pure function operating on a `tomlkit` doc.

**Files:**
- Modify: `src/thoth/commands.py`
- Create: `tests/test_init_command_dispatch.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_init_command_dispatch.py`:

```python
"""Dispatcher + merge tests for `thoth init` — P31."""

from __future__ import annotations

from pathlib import Path

import tomlkit

from thoth.commands import _apply_wizard_answers, _build_starter_document
from thoth.init_wizard import ProviderChoice, WizardAnswers


def _make(answers: tuple[ProviderChoice, ...], mode: str = "default") -> WizardAnswers:
    return WizardAnswers(
        providers=answers,
        default_mode=mode,  # type: ignore[arg-type]
        target_path=Path("/dev/null"),
    )


def test_apply_env_ref_writes_dollar_brace() -> None:
    doc = _build_starter_document()
    _apply_wizard_answers(doc, _make((ProviderChoice("openai", "env_ref", None),)))
    assert doc["providers"]["openai"]["api_key"] == "${OPENAI_API_KEY}"


def test_apply_literal_value_stored_inline() -> None:
    doc = _build_starter_document()
    _apply_wizard_answers(
        doc, _make((ProviderChoice("openai", "literal", "sk-real"),))
    )
    assert doc["providers"]["openai"]["api_key"] == "sk-real"


def test_apply_skip_leaves_existing_value_untouched() -> None:
    doc = _build_starter_document()
    doc["providers"]["openai"]["api_key"] = "previously-set"
    _apply_wizard_answers(doc, _make((ProviderChoice("openai", "skip", None),)))
    assert doc["providers"]["openai"]["api_key"] == "previously-set"


def test_apply_default_mode_updated() -> None:
    doc = _build_starter_document()
    _apply_wizard_answers(doc, _make((), mode="thinking"))
    assert doc["general"]["default_mode"] == "thinking"


def test_apply_preserves_unknown_sections() -> None:
    doc = _build_starter_document()
    # Simulate a user-edited section the wizard doesn't know about.
    custom = tomlkit.table()
    custom["my_key"] = "my_value"
    doc["custom_section"] = custom
    _apply_wizard_answers(doc, _make((), mode="thinking"))
    assert doc["custom_section"]["my_key"] == "my_value"
    # Profiles, paths, execution, output also still present.
    for section in ("paths", "execution", "output", "profiles"):
        assert section in doc


def test_apply_creates_missing_general_table() -> None:
    doc = tomlkit.document()
    doc["providers"] = tomlkit.table()
    _apply_wizard_answers(doc, _make((), mode="thinking"))
    assert doc["general"]["default_mode"] == "thinking"


def test_apply_creates_missing_provider_table() -> None:
    doc = tomlkit.document()  # totally empty
    _apply_wizard_answers(
        doc, _make((ProviderChoice("gemini", "env_ref", None),), mode="default")
    )
    assert doc["providers"]["gemini"]["api_key"] == "${GEMINI_API_KEY}"
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `uv run pytest tests/test_init_command_dispatch.py -v`
Expected: ImportError for `_apply_wizard_answers`.

- [ ] **Step 3: Implement**

Add to `src/thoth/commands.py` (above the `CommandHandler` class, after the existing `_build_starter_document`):

```python
def _apply_wizard_answers(doc: tomlkit.TOMLDocument, answers) -> None:
    """Merge `WizardAnswers` into a tomlkit document in place.

    Touches only `[general].default_mode` and `[providers.<name>].api_key`.
    All other sections are preserved verbatim. Missing tables are created.
    """
    from thoth.init_wizard import ENV_VAR_BY_PROVIDER

    # general.default_mode
    general = doc.get("general")
    if general is None or not hasattr(general, "keys"):
        general = tomlkit.table()
        doc["general"] = general
    general["default_mode"] = answers.default_mode

    # providers.<name>.api_key
    providers = doc.get("providers")
    if providers is None or not hasattr(providers, "keys"):
        providers = tomlkit.table()
        doc["providers"] = providers
    for choice in answers.providers:
        if choice.storage == "skip":
            continue
        prov_table = providers.get(choice.name)
        if prov_table is None or not hasattr(prov_table, "keys"):
            prov_table = tomlkit.table()
            providers[choice.name] = prov_table
        if choice.storage == "env_ref":
            var = ENV_VAR_BY_PROVIDER[choice.name]
            prov_table["api_key"] = f"${{{var}}}"
        else:  # literal
            prov_table["api_key"] = choice.literal_value or ""
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_init_command_dispatch.py -v`
Expected: 7 pass.

- [ ] **Step 5: Commit**

```bash
git add src/thoth/commands.py tests/test_init_command_dispatch.py
git commit -m "feat(p31): add _apply_wizard_answers tomlkit merge helper"
```

---

## Task 8: Pre-fill from existing TOML

When `--force` is set on an existing file, parse it and seed the wizard's defaults.

**Files:**
- Modify: `src/thoth/commands.py`
- Modify: `tests/test_init_command_dispatch.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_init_command_dispatch.py`:

```python
from thoth.commands import _load_or_build_doc, _prefill_from_doc


def test_prefill_extracts_default_mode() -> None:
    doc = _build_starter_document()
    doc["general"]["default_mode"] = "deep_research"
    pf = _prefill_from_doc(doc)
    assert pf.default_mode == "deep_research"


def test_prefill_returns_none_when_missing() -> None:
    doc = tomlkit.document()
    pf = _prefill_from_doc(doc)
    assert pf.default_mode is None
    assert pf.providers == ()


def test_prefill_ignores_unknown_default_mode() -> None:
    doc = _build_starter_document()
    doc["general"]["default_mode"] = "made-up"
    pf = _prefill_from_doc(doc)
    assert pf.default_mode is None  # don't pre-fill garbage


def test_load_or_build_returns_existing_doc(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    p.write_text('version = 1\n[general]\ndefault_mode = "thinking"\n')
    doc = _load_or_build_doc(p, force=True)
    assert doc["general"]["default_mode"] == "thinking"


def test_load_or_build_returns_starter_when_missing(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _load_or_build_doc(p, force=False)
    # starter doc has known shape
    assert "profiles" in doc
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `uv run pytest tests/test_init_command_dispatch.py -v -k "prefill or load_or_build"`
Expected: ImportError.

- [ ] **Step 3: Implement**

Add to `src/thoth/commands.py`:

```python
def _prefill_from_doc(doc: tomlkit.TOMLDocument):
    """Extract wizard-relevant fields from an existing tomlkit doc."""
    from thoth.init_wizard import (
        DEFAULT_MODE_OPTIONS,
        _Prefill,
    )

    general = doc.get("general") or {}
    raw_mode = general.get("default_mode") if hasattr(general, "get") else None
    mode = raw_mode if raw_mode in DEFAULT_MODE_OPTIONS else None

    # Provider pre-fill is intentionally empty: api_key strings can't be
    # round-tripped without exposing user secrets in prompts. The wizard
    # re-asks each picked provider's key from scratch on `--force`.
    return _Prefill(providers=(), default_mode=mode)


def _load_or_build_doc(target: Path, *, force: bool) -> tomlkit.TOMLDocument:
    """Return the doc to merge wizard answers into.

    Existing file + force → parse it (preserves unknown sections).
    Anything else → fresh starter doc.
    """
    if force and target.exists():
        try:
            return tomlkit.parse(target.read_text())
        except Exception as exc:  # tomlkit raises a variety of errors
            raise ThothError(
                f"Cannot parse existing config at {target}: {exc}. "
                "Pass --non-interactive to overwrite with defaults, "
                "or fix the file."
            ) from exc
    return _build_starter_document()
```

No rename needed — `_Prefill` is defined as a module-private dataclass in Task 6 inside `init_wizard.py`; cross-module imports of underscore-prefixed names within the same `thoth` package are an established pattern in this codebase. Just import it where needed (`from thoth.init_wizard import _Prefill, DEFAULT_MODE_OPTIONS`).

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_init_command_dispatch.py -v -k "prefill or load_or_build"`
Expected: 5 pass.

- [ ] **Step 5: Commit**

```bash
git add src/thoth/commands.py tests/test_init_command_dispatch.py
git commit -m "feat(p31): add _prefill_from_doc + _load_or_build_doc helpers"
```

---

## Task 9: Wire the dispatcher

Replace the placeholder in `init_command` with the real interactive branch.

**Files:**
- Modify: `src/thoth/commands.py`
- Modify: `tests/test_init_command_dispatch.py`

- [ ] **Step 1: Write failing dispatcher tests**

Append to `tests/test_init_command_dispatch.py`:

```python
from thoth.commands import CommandHandler
from thoth.config import ConfigManager


def test_dispatch_non_interactive_uses_static_starter(
    tmp_path: Path, monkeypatch
) -> None:
    """Regression: --non-interactive must NOT call init_wizard.run()."""
    called = {"flag": False}

    def boom(**_: object) -> object:
        called["flag"] = True
        raise AssertionError("wizard.run should not be called")

    import thoth.init_wizard as wiz

    monkeypatch.setattr(wiz, "run", boom)
    target = tmp_path / "thoth.config.toml"
    h = CommandHandler(ConfigManager())
    h.init_command(config_path=str(target), force=False, non_interactive=True)
    assert target.exists()
    assert called["flag"] is False


def test_dispatch_interactive_writes_wizard_output(
    tmp_path: Path, monkeypatch
) -> None:
    """Wizard answers land in the file."""
    target = tmp_path / "thoth.config.toml"
    answers = WizardAnswers(
        providers=(ProviderChoice("openai", "literal", "sk-stub"),),
        default_mode="thinking",
        target_path=target,
    )

    import thoth.init_wizard as wiz

    monkeypatch.setattr(wiz, "run", lambda **_: answers)
    h = CommandHandler(ConfigManager())
    h.init_command(config_path=str(target), force=False)
    written = tomlkit.parse(target.read_text())
    assert written["general"]["default_mode"] == "thinking"
    assert written["providers"]["openai"]["api_key"] == "sk-stub"


def test_dispatch_wizard_cancel_no_file_written(
    tmp_path: Path, monkeypatch
) -> None:
    target = tmp_path / "thoth.config.toml"

    import thoth.init_wizard as wiz

    monkeypatch.setattr(wiz, "run", lambda **_: None)
    h = CommandHandler(ConfigManager())
    h.init_command(config_path=str(target), force=False)
    assert not target.exists()


def test_dispatch_force_roundtrip_preserves_unknown(
    tmp_path: Path, monkeypatch
) -> None:
    target = tmp_path / "thoth.config.toml"
    target.write_text(
        'version = 1\n'
        '[general]\ndefault_mode = "default"\n'
        '[mysection]\nkeep_me = "yes"\n'
    )
    answers = WizardAnswers(
        providers=(),
        default_mode="thinking",
        target_path=target,
    )

    import thoth.init_wizard as wiz

    monkeypatch.setattr(wiz, "run", lambda **_: answers)
    h = CommandHandler(ConfigManager())
    h.init_command(config_path=str(target), force=True)
    written = tomlkit.parse(target.read_text())
    assert written["mysection"]["keep_me"] == "yes"
    assert written["general"]["default_mode"] == "thinking"


def test_dispatch_json_envelope_regression(tmp_path: Path) -> None:
    """TS01-m: --json --non-interactive path is unchanged by P31."""
    from click.testing import CliRunner

    from thoth.cli import cli

    runner = CliRunner()
    target = tmp_path / "thoth.config.toml"
    result = runner.invoke(
        cli,
        ["init", "--json", "--non-interactive", "--config", str(target)],
    )
    assert result.exit_code == 0, result.output
    # The exact JSON shape comes from get_init_data() which P31 doesn't
    # touch; just assert the envelope is valid JSON and references the
    # target path.
    import json

    payload = json.loads(result.output)
    assert "data" in payload or "ok" in payload  # tolerant of either env shape
    assert target.exists()
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `uv run pytest tests/test_init_command_dispatch.py -v -k "dispatch"`
Expected: 4 fail (current `init_command` doesn't accept `non_interactive`, doesn't dispatch).

- [ ] **Step 3: Modify `init_command`**

Replace lines 185–224 of `src/thoth/commands.py` (the existing `init_command` body) with:

```python
def init_command(
    self,
    config_path: str | Path | None = None,
    *,
    user: bool = False,
    hidden: bool = False,
    force: bool = False,
    non_interactive: bool = False,
    **params,
):
    """Initialize Thoth configuration"""
    if user and hidden:
        raise ThothError(
            "thoth init: --user and --hidden are mutually exclusive",
        )

    target = self._resolve_init_target(config_path, user=user, hidden=hidden)
    if target.exists() and not force:
        raise ThothError(
            f"thoth init: refusing to overwrite existing {target}. "
            "Pass --force to overwrite.",
        )

    console.print("[bold]Welcome to Thoth Research Assistant Setup![/bold]\n")
    console.print("Checking environment...")
    console.print(f"✓ Python {sys.version.split()[0]} detected")
    console.print("✓ UV package manager available")
    console.print(f"✓ Operating System: {sys.platform} (supported)\n")
    console.print(f"Configuration file will be created at: {target}\n")

    target.parent.mkdir(parents=True, exist_ok=True)

    if non_interactive:
        doc = _build_starter_document()
        target.write_text(tomlkit.dumps(doc))
        console.print(f"\n[green]✓[/green] Configuration saved to {target}")
        console.print('\nYou can now run: thoth deep_research "your prompt"')
        return

    # Interactive wizard path
    import os

    from thoth import init_wizard

    base_doc = _load_or_build_doc(target, force=force)
    prefill = _prefill_from_doc(base_doc) if force and target.exists() else None

    def _real_prompt(p: str) -> str:
        from rich.prompt import Prompt

        return Prompt.ask(p, default="")

    answers = init_wizard.run(
        target=target,
        prefill=prefill,
        prompt_fn=_real_prompt,
        env=dict(os.environ),
    )
    if answers is None:
        console.print("[yellow]Init cancelled — no file written.[/yellow]")
        return

    _apply_wizard_answers(base_doc, answers)
    target.write_text(tomlkit.dumps(base_doc))
    console.print(f"\n[green]✓[/green] Configuration saved to {target}")
    console.print('\nYou can now run: thoth deep_research "your prompt"')
```

- [ ] **Step 4: Update CLI leaf to pass `non_interactive` through**

In `src/thoth/cli_subcommands/init.py`, find the block:

```python
    extra_kwargs: dict[str, bool] = {}
    if user:
        extra_kwargs["user"] = True
    if hidden:
        extra_kwargs["hidden"] = True
    if force:
        extra_kwargs["force"] = True
    handler.init_command(config_path=config_path, **extra_kwargs)
```

Change to:

```python
    extra_kwargs: dict[str, bool] = {}
    if user:
        extra_kwargs["user"] = True
    if hidden:
        extra_kwargs["hidden"] = True
    if force:
        extra_kwargs["force"] = True
    if non_interactive:
        extra_kwargs["non_interactive"] = True
    handler.init_command(config_path=config_path, **extra_kwargs)
```

- [ ] **Step 5: Run all P31 tests**

Run: `uv run pytest tests/test_init_wizard.py tests/test_init_command_dispatch.py tests/test_init_ships_profiles.py -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/thoth/commands.py src/thoth/cli_subcommands/init.py tests/test_init_command_dispatch.py
git commit -m "feat(p31): wire interactive wizard into init_command dispatcher"
```

---

## Task 10: Integration test in thoth_test

Drive the wizard through real stdin to catch any TUI regression the unit tests miss.

**Files:**
- Modify: `thoth_test`

- [ ] **Step 1: Find the right insertion point**

Run: `grep -n "M2T-02" thoth_test`
Expected: a single line near the existing init test case (around line 2070 per pre-flight check).

- [ ] **Step 2: Add the new test case**

Immediately after the `M2T-02` `TestCase(...)` closing `)`, add:

```python
    TestCase(
        test_id="M2T-INTERACTIVE-INIT",
        description="Interactive init wizard collects answers and writes config",
        command=[THOTH_EXECUTABLE, "init", "--config", "./test_interactive.toml"],
        # pexpect-driven: each entry is (expect_pattern, send_string)
        interactive_inputs=[
            (r"Pick providers", "1"),                  # Q1: openai
            (r"OPENAI_API_KEY detected.*use it", "y"), # Q2: env-var
            (r"Default mode", "2"),                    # Q3: thinking
            (r"Write this", "y"),                      # review: yes
        ],
        expected_stdout_patterns=[r"Configuration saved to"],
        expected_exit_code=0,
        provider="mock",
        api_key_method="env",  # ensures OPENAI_API_KEY is in env
        cleanup_files=["test_interactive.toml"],
    ),
```

If the existing `TestCase` schema does NOT have an `interactive_inputs` field, this task expands to also add that field to the `TestCase` dataclass and its pexpect runner. Run: `grep -n "interactive_inputs\|class TestCase" thoth_test | head -10` first; if only one line (the dataclass definition), the field needs to be added — see Task 10b below.

- [ ] **Step 3: Run the integration suite**

Run: `./thoth_test -r --id M2T-INTERACTIVE-INIT -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add thoth_test
git commit -m "test(p31): add M2T-INTERACTIVE-INIT pexpect integration case"
```

### Task 10b (conditional — only if `interactive_inputs` field doesn't exist)

- [ ] Add `interactive_inputs: list[tuple[str, str]] = field(default_factory=list)` to the `TestCase` dataclass (~line 127).
- [ ] In the test runner where `pexpect.spawn(...)` is invoked, after spawn but before `wait()`, loop:
  ```python
  for pattern, send in tc.interactive_inputs:
      child.expect(pattern, timeout=10)
      child.sendline(send)
  ```
- [ ] Commit separately as `feat(thoth_test): support interactive_inputs for pexpect cases`.

---

## Task 11: Final verification + project flip

**Files:**
- Modify: `PROJECTS.md`
- Modify: `projects/P31-interactive-init-command.md`

- [ ] **Step 1: Run the full lefthook-equivalent gate**

Run sequentially:

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run ty check src/
uv run pytest -q
./thoth_test -r --skip-interactive -q
./thoth_test -r --id M2T-INTERACTIVE-INIT
```

Expected: all green.

- [ ] **Step 2: Flip P31 to done in trunk**

In `PROJECTS.md`, change:

```markdown
- [~] **P31** — [Interactive Init Command](projects/P31-interactive-init-command.md)
```

to:

```markdown
- [x] **P31** — [Interactive Init Command](projects/P31-interactive-init-command.md)
```

- [ ] **Step 3: Flip every task in the project file**

In `projects/P31-interactive-init-command.md`:

- Change `**Status:** `[~]` In progress.` to `**Status:** `[x]` Completed.`
- Flip `[ ] [P31-TS01]` → `[x] [P31-TS01]`
- Flip `[ ] [P31-T01]` → `[x] [P31-T01]`
- Flip `[ ] [P31-T02]` → `[x] [P31-T02]`

- [ ] **Step 4: Final commit**

```bash
git add PROJECTS.md projects/P31-interactive-init-command.md
git commit -m "chore(p31): mark P31 done — interactive init wizard shipped"
```

- [ ] **Step 5: Push branch and open PR**

```bash
git push -u origin p31-interactive-init
gh pr create --title "feat(p31): interactive init wizard" --body "$(cat <<'EOF'
## Summary
- Replace placeholder in `init_command()` with a real interactive wizard
- Detect-then-decide API-key handling for openai, perplexity, gemini
- Default-mode pick from the four built-ins
- Review-and-confirm before writing; cancel returns 0 without touching disk
- `--force` round-trips existing TOML, preserving unknown sections

## Spec / Plan
- Spec: `docs/superpowers/specs/2026-05-03-p31-interactive-init-design.md`
- Plan: `docs/superpowers/plans/2026-05-03-p31-interactive-init.md`

## Test plan
- [ ] Unit: `uv run pytest tests/test_init_wizard.py tests/test_init_command_dispatch.py -v`
- [ ] Integration: `./thoth_test -r --id M2T-INTERACTIVE-INIT`
- [ ] Manual smoke: in a tmp dir, `OPENAI_API_KEY=sk-x thoth init --config ./demo.toml` and walk the wizard
- [ ] `--force` round-trip: edit a `[mysection]` into the resulting file, re-run with `--force`, verify `mysection` survives
EOF
)"
```

---

## Self-review notes

- **Spec coverage**: every `TS01-a … TS01-m` row in the spec maps to a named test in tasks 1–9. TS01-h (`KeyboardInterrupt`) is in Task 6. TS01-l/m are in Task 9. TS01-k is in Task 7.
- **Type consistency**: `WizardAnswers`, `ProviderChoice`, `_Prefill`, `PromptFn`, `ProviderName`, `KeyStorage`, `DefaultMode` — used identically in every task that imports them.
- **`_apply_wizard_answers` signature**: takes `(doc, answers)` everywhere it appears.
- **`_load_or_build_doc` signature**: keyword-only `force=` everywhere.
- **`init_wizard.run()` signature**: keyword-only `target=`, `prefill=`, `prompt_fn=`, `env=` everywhere; returns `WizardAnswers | None`.
- **No placeholders**: every step has either a code block or an exact command. No "TBD" / "implement later" / "similar to Task N".
- **Frequent commits**: 11 tasks, one commit per task (Task 10 may add a second commit if 10b fires). All commits use Conventional Commits format per repo policy.
- **TDD bias**: every task that adds production code has its tests written and run-failing first (per CLAUDE.md TDD rule and P31-TS01).
