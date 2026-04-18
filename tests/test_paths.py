"""Tests for XDG-compliant path helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from thoth import paths


@pytest.mark.parametrize(
    ("env_name", "func", "subpath"),
    [
        ("XDG_CONFIG_HOME", paths.user_config_dir, "thoth"),
        ("XDG_STATE_HOME", paths.user_state_dir, "thoth"),
        ("XDG_CACHE_HOME", paths.user_cache_dir, "thoth"),
    ],
)
def test_dir_honors_env_when_set(
    env_name: str,
    func,
    subpath: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(env_name, str(tmp_path))
    assert func() == tmp_path / subpath


@pytest.mark.parametrize(
    ("env_name", "func", "default_rel"),
    [
        ("XDG_CONFIG_HOME", paths.user_config_dir, ".config/thoth"),
        ("XDG_STATE_HOME", paths.user_state_dir, ".local/state/thoth"),
        ("XDG_CACHE_HOME", paths.user_cache_dir, ".cache/thoth"),
    ],
)
def test_dir_falls_back_when_env_unset(
    env_name: str,
    func,
    default_rel: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(env_name, raising=False)
    assert func() == Path.home() / default_rel


@pytest.mark.parametrize(
    ("env_name", "func", "default_rel"),
    [
        ("XDG_CONFIG_HOME", paths.user_config_dir, ".config/thoth"),
        ("XDG_STATE_HOME", paths.user_state_dir, ".local/state/thoth"),
        ("XDG_CACHE_HOME", paths.user_cache_dir, ".cache/thoth"),
    ],
)
def test_dir_falls_back_when_env_empty(
    env_name: str,
    func,
    default_rel: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Per XDG spec: empty string is treated as unset.
    monkeypatch.setenv(env_name, "")
    assert func() == Path.home() / default_rel


def test_user_config_file_under_config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert paths.user_config_file() == tmp_path / "thoth" / "config.toml"


def test_user_checkpoints_dir_under_state_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    assert paths.user_checkpoints_dir() == tmp_path / "thoth" / "checkpoints"


def test_user_model_cache_dir_under_cache_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    assert paths.user_model_cache_dir() == tmp_path / "thoth" / "model_cache"
