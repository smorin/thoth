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
