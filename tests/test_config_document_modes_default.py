"""Pure unit tests for ConfigDocument default_mode primitives (P35 T01)."""

from __future__ import annotations

from pathlib import Path

from thoth.config_document import ConfigDocument


def _doc(path: Path) -> ConfigDocument:
    return ConfigDocument.load(path)


def test_default_mode_name_returns_none_when_unset(tmp_path: Path) -> None:
    doc = _doc(tmp_path / "thoth.config.toml")
    assert doc.default_mode_name() is None
    assert doc.default_mode_name(profile="work") is None


def test_set_default_mode_writes_general_key(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_default_mode("deep")
    doc.save()
    text = p.read_text()
    assert "[general]" in text
    assert 'default_mode = "deep"' in text


def test_set_default_mode_writes_profile_key(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.ensure_profile("work")
    doc.set_default_mode("deep", profile="work")
    doc.save()
    text = p.read_text()
    assert "[profiles.work]" in text
    assert 'default_mode = "deep"' in text


def test_default_mode_name_reads_back(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_default_mode("deep")
    doc.set_default_mode("fast", profile="work")
    doc.save()
    doc2 = _doc(p)
    assert doc2.default_mode_name() == "deep"
    assert doc2.default_mode_name(profile="work") == "fast"


def test_unset_default_mode_removes_general_key(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_default_mode("deep")
    assert doc.unset_default_mode() is True
    assert doc.default_mode_name() is None
    assert doc.unset_default_mode() is False  # idempotent


def test_unset_default_mode_leaves_general_table_in_place(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_default_mode("deep")
    doc.unset_default_mode()
    doc.save()
    assert "[general]" in p.read_text()


def test_unset_default_mode_removes_profile_key(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.ensure_profile("work")
    doc.set_default_mode("deep", profile="work")
    assert doc.unset_default_mode(profile="work") is True
    assert doc.default_mode_name(profile="work") is None
    assert doc.unset_default_mode(profile="work") is False


def test_has_profile_true_after_ensure(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    assert doc.has_profile("work") is False
    doc.ensure_profile("work")
    assert doc.has_profile("work") is True


def test_has_profile_false_for_general_table(tmp_path: Path) -> None:
    """Sanity: has_profile only checks [profiles.X], not [general]."""
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_default_mode("deep")
    assert doc.has_profile("work") is False


def test_target_has_profile_reads_only_target_file(tmp_path: Path) -> None:
    """target_has_profile inspects the target file only — NOT the merged catalog."""
    from thoth.config_write_context import ConfigWriteContext

    target = tmp_path / "custom.toml"
    doc = ConfigDocument.load(target)
    doc.ensure_profile("scoped")
    doc.save()

    ctx = ConfigWriteContext.resolve(project=False, config_path=target)
    assert ctx.target_has_profile("scoped") is True
    assert ctx.target_has_profile("missing") is False
