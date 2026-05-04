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


from thoth.errors import ThothError  # noqa: E402
from thoth.init_wizard import pick_many, pick_one  # noqa: E402


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


from thoth.init_wizard import prompt_providers  # noqa: E402


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


from thoth.init_wizard import prompt_key_for_provider  # noqa: E402


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


from thoth.init_wizard import prompt_default_mode  # noqa: E402


def test_default_mode_pick_thinking() -> None:
    sp = ScriptedPrompts(["2"])
    assert prompt_default_mode(prompt_fn=sp, current="default") == "thinking"


def test_default_mode_empty_keeps_current() -> None:
    sp = ScriptedPrompts([""])
    assert prompt_default_mode(prompt_fn=sp, current="deep_research") == "deep_research"


def test_default_mode_empty_with_no_current_uses_default() -> None:
    sp = ScriptedPrompts([""])
    assert prompt_default_mode(prompt_fn=sp, current=None) == "default"
