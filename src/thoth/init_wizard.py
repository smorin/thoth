"""Interactive `thoth init` wizard — P31.

Module is intentionally I/O-free. `run()` returns `WizardAnswers`; the
caller in `commands.py` is responsible for merging answers into a
`tomlkit` document and writing the file.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from thoth.errors import ThothError

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
    # pick_many returns list[str]; narrow to ProviderName
    return [p for p in picks if p in PROVIDER_OPTIONS]  # type: ignore[misc]  # ty: ignore[invalid-return-type]


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
        reply = (
            prompt_fn(f"${var} detected (...{_last4(detected)}) — use it? [Y/n] ").strip().lower()
        )
        if reply in ("", "y", "yes"):
            return ProviderChoice(provider, "env_ref", None)
        # fall through to the missing-env branch
    options = [
        f"Paste {var} now (stored in this file)",
        f"I'll set ${var} myself (write '${{{var}}}' reference)",
        "Skip this provider",
    ]
    pick = pick_one(options, prompt_fn=prompt_fn, default_index=0, label=f"{provider} key")
    if pick == options[0]:
        raw = prompt_fn(f"Paste {var}: ")
        return ProviderChoice(provider, "literal", raw.strip())
    if pick == options[1]:
        return ProviderChoice(provider, "env_ref", None)
    return ProviderChoice(provider, "skip", None)


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
