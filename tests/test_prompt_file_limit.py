"""Tests for the prompt-file size cap (BUG-03)."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from thoth.cli import cli


def _make_dummy_run(monkeypatch):
    """Stub run_research so a happy-path invocation does not actually run."""
    captured = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return 0

    monkeypatch.setattr("thoth.run.run_research", fake_run)
    return captured


def test_prompt_file_oversized_rejected(tmp_path: Path, monkeypatch):
    _make_dummy_run(monkeypatch)
    big = tmp_path / "big.txt"
    big.write_bytes(b"x" * (1024 * 1024 + 1))

    r = CliRunner().invoke(cli, ["--prompt-file", str(big), "default"])
    assert r.exit_code != 0
    assert "exceeds" in r.output


def test_prompt_file_under_limit_accepted(tmp_path: Path, monkeypatch):
    captured = _make_dummy_run(monkeypatch)
    small = tmp_path / "small.txt"
    small.write_text("hello world")

    r = CliRunner().invoke(cli, ["--prompt-file", str(small), "default"])
    assert r.exit_code == 0, r.output
    assert captured.get("prompt") == "hello world"


def test_prompt_stdin_oversized_rejected(monkeypatch):
    _make_dummy_run(monkeypatch)
    payload = "x" * (1024 * 1024 + 1)
    r = CliRunner().invoke(cli, ["--prompt-file", "-", "default"], input=payload)
    assert r.exit_code != 0
    assert "exceeds" in r.output


def test_prompt_file_non_utf8_rejected(tmp_path: Path, monkeypatch):
    _make_dummy_run(monkeypatch)
    bad = tmp_path / "latin1.txt"
    bad.write_bytes(b"\xff\xfe non-utf8 bytes")

    r = CliRunner().invoke(cli, ["--prompt-file", str(bad), "default"])
    assert r.exit_code != 0
    assert "UTF-8" in r.output or "utf-8" in r.output


def test_prompt_max_bytes_config_override(tmp_path: Path, monkeypatch):
    """User can shrink the cap via [execution].prompt_max_bytes in config."""
    _make_dummy_run(monkeypatch)

    cfg = tmp_path / "thoth.config.toml"
    cfg.write_text('version = "2.0"\n[execution]\nprompt_max_bytes = 50\n')
    long_file = tmp_path / "long.txt"
    long_file.write_text("x" * 100)

    r = CliRunner().invoke(cli, ["--config", str(cfg), "--prompt-file", str(long_file), "default"])
    assert r.exit_code != 0
    assert "exceeds" in r.output
