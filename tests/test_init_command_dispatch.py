"""Dispatcher + merge tests for `thoth init` — P31."""

from __future__ import annotations

from pathlib import Path

import tomlkit

from thoth.commands import (
    CommandHandler,
    _apply_wizard_answers,
    _build_starter_document,
    _load_or_build_doc,
    _prefill_from_doc,
)
from thoth.config import ConfigManager
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


def test_dispatch_non_interactive_uses_static_starter(tmp_path: Path, monkeypatch) -> None:
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


def test_dispatch_interactive_writes_wizard_output(tmp_path: Path, monkeypatch) -> None:
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
    assert written["general"]["default_mode"] == "thinking"  # ty: ignore[not-subscriptable]
    assert written["providers"]["openai"]["api_key"] == "sk-stub"  # ty: ignore[not-subscriptable]


def test_dispatch_wizard_cancel_no_file_written(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "thoth.config.toml"

    import thoth.init_wizard as wiz

    monkeypatch.setattr(wiz, "run", lambda **_: None)
    h = CommandHandler(ConfigManager())
    h.init_command(config_path=str(target), force=False)
    assert not target.exists()


def test_dispatch_force_roundtrip_preserves_unknown(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "thoth.config.toml"
    target.write_text(
        'version = 1\n[general]\ndefault_mode = "default"\n[mysection]\nkeep_me = "yes"\n'
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
    assert written["mysection"]["keep_me"] == "yes"  # ty: ignore[not-subscriptable]
    assert written["general"]["default_mode"] == "thinking"  # ty: ignore[not-subscriptable]


def test_dispatch_json_envelope_regression(tmp_path: Path) -> None:
    """TS01-m: --json --non-interactive path is unchanged by P31."""
    from click.testing import CliRunner

    from thoth.cli import cli

    runner = CliRunner()
    target = tmp_path / "thoth.config.toml"
    result = runner.invoke(
        cli,
        ["--config", str(target), "init", "--json", "--non-interactive"],
    )
    assert result.exit_code == 0, result.output
    # The exact JSON shape comes from get_init_data() which P31 doesn't
    # touch; just assert the envelope is valid JSON and references the
    # target path.
    import json

    payload = json.loads(result.output)
    assert "data" in payload or "ok" in payload  # tolerant of either env shape
    assert target.exists()
