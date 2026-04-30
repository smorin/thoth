from pathlib import Path

from thoth.config_legacy import LEGACY_PROJECT_PATHS
from thoth.errors import APIKeyError, format_config_context


def test_context_path_exists_env_set(tmp_path, monkeypatch):
    cfg = tmp_path / "thoth.config.toml"
    cfg.write_text("")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")
    out = format_config_context(cfg, env_vars=["OPENAI_API_KEY"])
    assert str(cfg) in out
    assert "(exists)" in out
    assert "OPENAI_API_KEY" in out
    assert "(set)" in out


def test_context_path_missing_env_unset(tmp_path, monkeypatch):
    cfg = tmp_path / "missing.toml"
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    out = format_config_context(cfg, env_vars=["OPENAI_API_KEY"])
    assert "(does not exist)" in out
    assert "(unset)" in out


def test_context_multiple_env_vars(tmp_path, monkeypatch):
    monkeypatch.setenv("A", "1")
    monkeypatch.delenv("B", raising=False)
    out = format_config_context(tmp_path / "c.toml", env_vars=["A", "B"])
    assert "A" in out and "(set)" in out
    assert "B" in out and "(unset)" in out


def test_context_no_env_vars(tmp_path):
    out = format_config_context(tmp_path / "c.toml", env_vars=[])
    assert "Config file:" in out
    assert "Env checked:" not in out


def test_api_key_error_includes_config_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    err = APIKeyError("openai")
    assert err.suggestion is not None
    assert "thoth.config.toml" in err.suggestion
    assert "OPENAI_API_KEY" in err.suggestion
    assert "(unset)" in err.suggestion
    assert "Detected legacy" not in err.suggestion


def test_api_key_error_includes_legacy_config_guidance(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    legacy_path = Path(LEGACY_PROJECT_PATHS[0])
    (tmp_path / legacy_path).write_text(
        'version = "2.0"\n[providers.openai]\napi_key = "sk-legacy"\n'
    )

    err = APIKeyError("openai")

    assert err.suggestion is not None
    assert f"Detected legacy file: {legacy_path}" in err.suggestion
    assert "These filenames are no longer read" in err.suggestion
    assert "Rename to thoth.config.toml" in err.suggestion
