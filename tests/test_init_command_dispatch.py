"""Dispatcher + merge tests for `thoth init` — P31."""

from __future__ import annotations

from pathlib import Path

import tomlkit

from thoth.commands import _apply_wizard_answers, _build_starter_document
from thoth.init_wizard import ProviderChoice, WizardAnswers


def _make(answers: tuple[ProviderChoice, ...], mode: str = "default") -> WizardAnswers:
    return WizardAnswers(
        providers=answers,
        default_mode=mode,  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
        target_path=Path("/dev/null"),
    )


def test_apply_env_ref_writes_dollar_brace() -> None:
    doc = _build_starter_document()
    _apply_wizard_answers(doc, _make((ProviderChoice("openai", "env_ref", None),)))
    assert doc["providers"]["openai"]["api_key"] == "${OPENAI_API_KEY}"  # ty: ignore[not-subscriptable]


def test_apply_literal_value_stored_inline() -> None:
    doc = _build_starter_document()
    _apply_wizard_answers(doc, _make((ProviderChoice("openai", "literal", "sk-real"),)))
    assert doc["providers"]["openai"]["api_key"] == "sk-real"  # ty: ignore[not-subscriptable]


def test_apply_skip_leaves_existing_value_untouched() -> None:
    doc = _build_starter_document()
    doc["providers"]["openai"]["api_key"] = "previously-set"  # ty: ignore[not-subscriptable,invalid-assignment]
    _apply_wizard_answers(doc, _make((ProviderChoice("openai", "skip", None),)))
    assert doc["providers"]["openai"]["api_key"] == "previously-set"  # ty: ignore[not-subscriptable]


def test_apply_default_mode_updated() -> None:
    doc = _build_starter_document()
    _apply_wizard_answers(doc, _make((), mode="thinking"))
    assert doc["general"]["default_mode"] == "thinking"  # ty: ignore[not-subscriptable]


def test_apply_preserves_unknown_sections() -> None:
    doc = _build_starter_document()
    # Simulate a user-edited section the wizard doesn't know about.
    custom = tomlkit.table()
    custom["my_key"] = "my_value"
    doc["custom_section"] = custom
    _apply_wizard_answers(doc, _make((), mode="thinking"))
    assert doc["custom_section"]["my_key"] == "my_value"  # ty: ignore[not-subscriptable]
    # Profiles, paths, execution, output also still present.
    for section in ("paths", "execution", "output", "profiles"):
        assert section in doc


def test_apply_creates_missing_general_table() -> None:
    doc = tomlkit.document()
    doc["providers"] = tomlkit.table()
    _apply_wizard_answers(doc, _make((), mode="thinking"))
    assert doc["general"]["default_mode"] == "thinking"  # ty: ignore[not-subscriptable]


def test_apply_creates_missing_provider_table() -> None:
    doc = tomlkit.document()  # totally empty
    _apply_wizard_answers(doc, _make((ProviderChoice("gemini", "env_ref", None),), mode="default"))
    assert doc["providers"]["gemini"]["api_key"] == "${GEMINI_API_KEY}"  # ty: ignore[not-subscriptable]
