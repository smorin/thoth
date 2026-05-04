"""Dispatcher + merge tests for `thoth init` — P31."""

from __future__ import annotations

from pathlib import Path

import tomlkit

from thoth.commands import (
    _apply_wizard_answers,
    _build_starter_document,
    _load_or_build_doc,
    _prefill_from_doc,
)
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


def test_prefill_extracts_default_mode() -> None:
    doc = _build_starter_document()
    doc["general"]["default_mode"] = "deep_research"  # ty: ignore[invalid-assignment]
    pf = _prefill_from_doc(doc)
    assert pf.default_mode == "deep_research"


def test_prefill_returns_none_when_missing() -> None:
    doc = tomlkit.document()
    pf = _prefill_from_doc(doc)
    assert pf.default_mode is None
    assert pf.providers == ()


def test_prefill_ignores_unknown_default_mode() -> None:
    doc = _build_starter_document()
    doc["general"]["default_mode"] = "made-up"  # ty: ignore[invalid-assignment]
    pf = _prefill_from_doc(doc)
    assert pf.default_mode is None  # don't pre-fill garbage


def test_load_or_build_returns_existing_doc(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    p.write_text('version = 1\n[general]\ndefault_mode = "thinking"\n')
    doc = _load_or_build_doc(p, force=True)
    assert doc["general"]["default_mode"] == "thinking"  # ty: ignore[not-subscriptable]


def test_load_or_build_returns_starter_when_missing(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _load_or_build_doc(p, force=False)
    # starter doc has known shape
    assert "profiles" in doc
