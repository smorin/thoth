from __future__ import annotations

import tomllib
from pathlib import Path

from thoth.config_document import ConfigDocument


def test_profile_value_keeps_dotted_profile_name_literal(tmp_path: Path) -> None:
    path = tmp_path / "thoth.config.toml"

    doc = ConfigDocument.load(path)
    assert doc.ensure_profile("foo.bar") is True
    doc.set_profile_value("foo.bar", "general.default_mode", "thinking")
    doc.save()

    text = path.read_text()
    data = tomllib.loads(text)
    assert set(data["profiles"]) == {"foo.bar"}
    assert data["profiles"]["foo.bar"]["general"]["default_mode"] == "thinking"
    assert "[profiles.foo.bar" not in text


def test_unset_profile_value_preserves_empty_parent_table(tmp_path: Path) -> None:
    path = tmp_path / "thoth.config.toml"
    doc = ConfigDocument.load(path)
    doc.set_profile_value("foo.bar", "general.default_mode", "thinking")
    doc.save()

    doc = ConfigDocument.load(path)
    assert doc.unset_profile_value("foo.bar", "general.default_mode") is True
    doc.save()

    data = tomllib.loads(path.read_text())
    assert data["profiles"]["foo.bar"]["general"] == {}


def test_unset_config_value_can_prune_empty_parent_tables(tmp_path: Path) -> None:
    path = tmp_path / "thoth.config.toml"
    doc = ConfigDocument.load(path)
    doc.set_config_value("general.default_mode", "thinking")
    doc.save()

    doc = ConfigDocument.load(path)
    assert doc.unset_config_value("general.default_mode", prune_empty=True) is True
    doc.save()

    data = tomllib.loads(path.read_text())
    assert "general" not in data


def test_unset_default_profile_preserves_general_table(tmp_path: Path) -> None:
    path = tmp_path / "thoth.config.toml"
    doc = ConfigDocument.load(path)
    doc.set_default_profile("fast")
    doc.save()

    doc = ConfigDocument.load(path)
    assert doc.unset_default_profile() is True
    doc.save()

    data = tomllib.loads(path.read_text())
    assert data["general"] == {}


def test_unset_default_profile_if_only_removes_matching_name(tmp_path: Path) -> None:
    path = tmp_path / "thoth.config.toml"
    doc = ConfigDocument.load(path)
    doc.set_default_profile("fast")
    doc.save()

    doc = ConfigDocument.load(path)
    assert doc.unset_default_profile_if("slow") is False
    assert doc.default_profile_name() == "fast"
    assert doc.unset_default_profile_if("fast") is True
    doc.save()

    data = tomllib.loads(path.read_text())
    assert "default_profile" not in data["general"]


def test_profile_mutations_preserve_comments(tmp_path: Path) -> None:
    path = tmp_path / "thoth.config.toml"
    path.write_text(
        '# pinned profile\n[profiles.fast.general]\n# default mode\ndefault_mode = "thinking"\n'
    )

    doc = ConfigDocument.load(path)
    doc.set_profile_value("fast", "general.timeout", 30)
    doc.save()

    text = path.read_text()
    assert "# pinned profile" in text
    assert "# default mode" in text

    doc = ConfigDocument.load(path)
    assert doc.unset_profile_value("fast", "general.timeout") is True
    doc.save()

    text = path.read_text()
    assert "# pinned profile" in text
    assert "# default mode" in text
