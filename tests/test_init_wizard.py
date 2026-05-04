"""Unit tests for src/thoth/init_wizard.py — P31."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from thoth.init_wizard import ProviderChoice, ScriptedPrompts, WizardAnswers


def test_provider_choice_is_frozen() -> None:
    pc = ProviderChoice(name="openai", storage="env_ref", literal_value=None)
    with pytest.raises(dataclasses.FrozenInstanceError):
        pc.name = "gemini"  # type: ignore[misc]  # ty: ignore[invalid-assignment]


def test_wizard_answers_is_frozen(tmp_path: Path) -> None:
    a = WizardAnswers(
        providers=(ProviderChoice("openai", "env_ref", None),),
        default_mode="thinking",
        target_path=tmp_path / "thoth.config.toml",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        a.default_mode = "default"  # type: ignore[misc]  # ty: ignore[invalid-assignment]


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
