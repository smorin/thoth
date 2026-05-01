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


def test_unset_mode_value_drops_key(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("brief", "model", "gpt-4o-mini")
    doc.set_mode_value("brief", "temperature", 0.2)
    assert doc.unset_mode_value("brief", "temperature") == (True, False)
    doc.save()
    text = p.read_text()
    assert "model" in text
    assert "temperature" not in text


def test_unset_mode_value_prunes_empty_table(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("brief", "model", "gpt-4o-mini")
    # Removing the only key should prune the empty [modes.brief] table.
    assert doc.unset_mode_value("brief", "model") == (True, True)
    doc.save()
    text = p.read_text()
    assert "modes.brief" not in text


def test_unset_mode_value_idempotent_when_absent(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("brief", "model", "gpt-4o-mini")
    assert doc.unset_mode_value("brief", "missing_key") == (False, False)


def test_unset_mode_value_in_overlay_tier(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("cheap", "model", "gpt-4o-mini", profile="dev")
    assert doc.unset_mode_value("cheap", "model", profile="dev") == (True, True)
    doc.save()
    assert "cheap" not in p.read_text()


def test_remove_mode_drops_table(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("brief", "model", "gpt-4o-mini")
    doc.set_mode_value("brief", "temperature", 0.2)
    assert doc.remove_mode("brief") is True
    doc.save()
    assert "modes.brief" not in p.read_text()


def test_remove_mode_idempotent_when_absent(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    assert doc.remove_mode("nonexistent") is False


def test_remove_mode_in_overlay_tier(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("cheap", "model", "gpt-4o-mini", profile="dev")
    assert doc.remove_mode("cheap", profile="dev") is True
    doc.save()
    assert "profiles.dev.modes.cheap" not in p.read_text()


def test_rename_mode_succeeds(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("old", "model", "gpt-4o-mini")
    doc.set_mode_value("old", "temperature", 0.2)
    assert doc.rename_mode("old", "new") is True
    doc.save()
    text = p.read_text()
    assert "[modes.new]" in text
    assert "[modes.old]" not in text
    assert 'model = "gpt-4o-mini"' in text
    assert "temperature = 0.2" in text


def test_rename_mode_when_old_absent(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    assert doc.rename_mode("missing", "new") is False


def test_rename_mode_when_new_already_exists(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("old", "model", "a")
    doc.set_mode_value("new", "model", "b")
    # The CLI layer is responsible for the DST_NAME_TAKEN error code; the
    # primitive returns False so the layer can map to the right error.
    assert doc.rename_mode("old", "new") is False


def test_rename_mode_in_overlay(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("old", "model", "x", profile="dev")
    assert doc.rename_mode("old", "new", profile="dev") is True
    doc.save()
    text = p.read_text()
    assert "profiles.dev.modes.new" in text
    assert "profiles.dev.modes.old" not in text


def test_copy_mode_base_to_base(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("src", "model", "gpt-4o-mini")
    doc.set_mode_value("src", "temperature", 0.2)
    assert doc.copy_mode("src", "dst") is True
    doc.save()
    text = p.read_text()
    assert "[modes.src]" in text
    assert "[modes.dst]" in text


def test_copy_mode_base_to_overlay(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("src", "model", "gpt-4o-mini")
    assert doc.copy_mode("src", "dst", profile="dev") is True
    doc.save()
    text = p.read_text()
    assert "[modes.src]" in text
    assert "[profiles.dev.modes.dst]" in text


def test_copy_mode_overlay_to_base(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("src", "model", "gpt-4o-mini", profile="dev")
    assert doc.copy_mode("src", "dst", from_profile="dev") is True
    doc.save()
    text = p.read_text()
    assert "[profiles.dev.modes.src]" in text
    assert "[modes.dst]" in text


def test_copy_mode_overlay_to_overlay_cross_profile(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("src", "model", "gpt-4o-mini", profile="dev")
    assert doc.copy_mode("src", "dst", from_profile="dev", profile="ci") is True
    doc.save()
    text = p.read_text()
    assert "profiles.dev.modes.src" in text
    assert "profiles.ci.modes.dst" in text


def test_copy_mode_when_dst_already_exists(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("src", "model", "a")
    doc.set_mode_value("dst", "model", "b")
    assert doc.copy_mode("src", "dst") is False


def test_copy_mode_when_src_absent_falls_back_to_caller_provided_data(
    tmp_path: Path,
) -> None:
    """The primitive has no notion of BUILTIN_MODES; the CLI layer is
    responsible for layering builtin+override before calling. When SRC is
    truly absent in the file, the primitive returns False."""
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    assert doc.copy_mode("missing", "dst") is False
