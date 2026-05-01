"""Pure unit tests for ConfigDocument mode primitives (P12 Task 2)."""

from __future__ import annotations

from pathlib import Path

from thoth.config_document import ConfigDocument


def _doc(path: Path) -> ConfigDocument:
    return ConfigDocument.load(path)


def test_ensure_mode_creates_table(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    assert doc.ensure_mode("brief") is True
    doc.save()
    assert "[modes.brief]" in p.read_text()


def test_ensure_mode_idempotent(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.ensure_mode("brief")
    assert doc.ensure_mode("brief") is False  # second call is no-op


def test_ensure_mode_with_profile(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    assert doc.ensure_mode("cheap", profile="dev") is True
    doc.save()
    assert "[profiles.dev.modes.cheap]" in p.read_text()


def test_set_mode_value_in_base_tier(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("brief", "model", "gpt-4o-mini")
    doc.save()
    text = p.read_text()
    assert "[modes.brief]" in text
    assert 'model = "gpt-4o-mini"' in text


def test_set_mode_value_in_overlay_tier(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("cheap", "model", "gpt-4o-mini", profile="dev")
    doc.save()
    text = p.read_text()
    assert "[profiles.dev.modes.cheap]" in text
    assert 'model = "gpt-4o-mini"' in text


def test_set_mode_value_dotted_key(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("brief", "limits.max_tokens", 1000)
    doc.save()
    text = p.read_text()
    assert "[modes.brief.limits]" in text
    assert "max_tokens = 1000" in text
