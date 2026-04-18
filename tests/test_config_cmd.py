"""Tests for the `thoth config` subcommand."""

from __future__ import annotations

from pathlib import Path

import pytest

from thoth.config_cmd import config_command


def test_get_returns_merged_value(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = config_command("get", ["general.default_mode"])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == "default"


def test_get_missing_key_exits_nonzero(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = config_command("get", ["nonexistent.key"])
    assert rc == 1


def test_get_layer_defaults(isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # Write a user override, confirm --layer defaults still returns the default.
    user_toml = Path(isolated_thoth_home) / "config" / "thoth" / "config.toml"
    user_toml.parent.mkdir(parents=True, exist_ok=True)
    user_toml.write_text('version = "2.0"\n[general]\ndefault_mode = "exploration"\n')

    rc = config_command("get", ["--layer", "defaults", "general.default_mode"])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == "default"


def test_get_raw_preserves_env_template(
    isolated_thoth_home: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    rc = config_command("get", ["--raw", "providers.openai.api_key"])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == "${OPENAI_API_KEY}"


def test_set_writes_user_toml(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = config_command("set", ["general.default_mode", "exploration"])
    assert rc == 0

    from thoth.paths import user_config_file

    path = user_config_file()
    assert path.exists()
    content = path.read_text()
    assert "exploration" in content

    rc2 = config_command("get", ["general.default_mode"])
    out = capsys.readouterr().out.strip().splitlines()[-1]
    assert rc2 == 0
    assert out == "exploration"


def test_set_project_writes_project_toml(
    isolated_thoth_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = config_command("set", ["--project", "general.default_mode", "deep_dive"])
    assert rc == 0
    project_path = tmp_path / "thoth.toml"
    assert project_path.exists()
    assert "deep_dive" in project_path.read_text()

    from thoth.paths import user_config_file

    assert not user_config_file().exists()


def test_set_parses_bool(isolated_thoth_home: Path) -> None:
    rc = config_command("set", ["execution.parallel_providers", "false"])
    assert rc == 0
    cm_rc = config_command("get", ["execution.parallel_providers"])
    assert cm_rc == 0


def test_set_parses_int(isolated_thoth_home: Path) -> None:
    import tomllib

    from thoth.paths import user_config_file

    rc = config_command("set", ["execution.poll_interval", "15"])
    assert rc == 0

    data = tomllib.loads(user_config_file().read_text())
    assert data["execution"]["poll_interval"] == 15


def test_set_string_flag_forces_string(isolated_thoth_home: Path) -> None:
    import tomllib

    from thoth.paths import user_config_file

    rc = config_command("set", ["--string", "execution.poll_interval", "15"])
    assert rc == 0

    data = tomllib.loads(user_config_file().read_text())
    assert data["execution"]["poll_interval"] == "15"


def test_unset_removes_key(isolated_thoth_home: Path) -> None:
    import tomllib

    from thoth.paths import user_config_file

    config_command("set", ["general.default_mode", "exploration"])
    rc = config_command("unset", ["general.default_mode"])
    assert rc == 0

    data = tomllib.loads(user_config_file().read_text())
    assert "general" not in data


def test_unset_missing_key_is_noop(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = config_command("unset", ["general.default_mode"])
    assert rc == 0


def test_unset_project_target(
    isolated_thoth_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import tomllib

    monkeypatch.chdir(tmp_path)
    config_command("set", ["--project", "general.default_mode", "deep_dive"])
    rc = config_command("unset", ["--project", "general.default_mode"])
    assert rc == 0
    data = tomllib.loads((tmp_path / "thoth.toml").read_text())
    assert "general" not in data


def test_list_prints_toml(isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = config_command("list", [])
    out = capsys.readouterr().out
    assert rc == 0
    assert 'version = "2.0"' in out
    assert "[general]" in out


def test_list_keys_emits_sorted_dotted(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = config_command("list", ["--keys"])
    out = capsys.readouterr().out.strip().splitlines()
    assert rc == 0
    assert "general.default_mode" in out
    assert out == sorted(out)


def test_list_json_is_valid_json(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import json

    rc = config_command("list", ["--json"])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "version" in data


def test_list_layer_shows_one_layer(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_command("set", ["general.default_mode", "exploration"])
    capsys.readouterr()
    rc = config_command("list", ["--layer", "defaults"])
    out = capsys.readouterr().out
    assert rc == 0
    assert 'default_mode = "default"' in out


def test_path_prints_user_config_path(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from thoth.paths import user_config_file

    rc = config_command("path", [])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == str(user_config_file())


def test_path_project_prints_project_path(
    isolated_thoth_home: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = config_command("path", ["--project"])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == str(tmp_path / "thoth.toml")


def test_get_masks_api_key_by_default(
    isolated_thoth_home: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-abcdef123456wxyz")
    rc = config_command("get", ["providers.openai.api_key"])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == "****wxyz"


def test_get_show_secrets_reveals(
    isolated_thoth_home: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-abcdef123456wxyz")
    rc = config_command("get", ["--show-secrets", "providers.openai.api_key"])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == "sk-abcdef123456wxyz"


def test_list_masks_api_keys_by_default(
    isolated_thoth_home: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-abcdef123456wxyz")
    rc = config_command("list", [])
    out = capsys.readouterr().out
    assert rc == 0
    assert "sk-abcdef123456wxyz" not in out
    assert "****wxyz" in out


def test_set_preserves_existing_comments(isolated_thoth_home: Path) -> None:
    from thoth.paths import user_config_file

    path = user_config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '# my header comment\nversion = "2.0"\n\n'
        "[general]\n# default mode picks the LLM prompt shape\n"
        'default_mode = "default"\n'
    )

    rc = config_command("set", ["general.default_mode", "exploration"])
    assert rc == 0

    content = path.read_text()
    assert "# my header comment" in content
    assert "# default mode picks the LLM prompt shape" in content
    assert "exploration" in content
