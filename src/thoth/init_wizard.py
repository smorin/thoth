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
