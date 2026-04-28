"""Category C — completion install behavior matrix (spec §6.3 + §9.1).

This file holds the minimal subset to validate the install dataclass and
the manual-mode path. The full TTY/non-TTY/force matrix lives here too;
T04 expands the parametrize coverage to the full 5-row matrix from
spec §6.3.
"""

from __future__ import annotations

import pytest


def test_install_manual_mode_returns_preview_action_and_writes_nothing(tmp_path):
    from thoth.completion.install import install

    rc_path = tmp_path / ".bashrc"
    result = install("bash", manual=True, rc_path=rc_path)

    assert result.action == "preview"
    assert "thoth completion" in result.message
    assert not rc_path.exists()


def test_install_manual_force_mutex_raises(tmp_path):
    import click

    from thoth.completion.install import install

    with pytest.raises(click.BadParameter, match="mutex"):
        install("bash", manual=True, force=True, rc_path=tmp_path / ".bashrc")


def test_install_force_writes_silently(tmp_path):
    from thoth.completion.install import install

    rc_path = tmp_path / ".bashrc"
    result = install("bash", force=True, rc_path=rc_path)

    assert result.action == "written"
    assert rc_path.exists()
    text = rc_path.read_text()
    assert "# >>> thoth completion >>>" in text
    assert "# <<< thoth completion <<<" in text


def test_install_force_overwrites_existing_block(tmp_path):
    from thoth.completion.install import install

    rc_path = tmp_path / ".bashrc"
    rc_path.write_text(
        "# user content above\n"
        "# >>> thoth completion >>>\n"
        "OLD CONTENT\n"
        "# <<< thoth completion <<<\n"
        "# user content below\n"
    )
    install("bash", force=True, rc_path=rc_path)

    text = rc_path.read_text()
    assert text.count("# >>> thoth completion >>>") == 1
    assert "OLD CONTENT" not in text
    assert "# user content above" in text
    assert "# user content below" in text


def test_install_fish_uses_fish_completion_path_when_default(tmp_path, monkeypatch):
    """Fish convention: ~/.config/fish/completions/thoth.fish (per spec §6.3)."""
    from thoth.completion.install import install

    monkeypatch.setenv("HOME", str(tmp_path))
    result = install("fish", force=True)

    assert result.path == tmp_path / ".config" / "fish" / "completions" / "thoth.fish"
    assert result.path.exists()


# === Category C (T04): full CLI install matrix tests ===

import json as _json  # noqa: E402

from click.testing import CliRunner  # noqa: E402


def _invoke(args: list[str], **kwargs):
    from thoth.cli import cli

    runner = CliRunner()
    return runner.invoke(cli, args, catch_exceptions=False, **kwargs)


def test_cli_install_non_tty_without_force_or_manual_refuses(monkeypatch, tmp_path):
    """spec §6.3 row: non-TTY + no --force/--manual --> INSTALL_REQUIRES_TTY."""
    monkeypatch.setenv("HOME", str(tmp_path))
    result = _invoke(["completion", "bash", "--install"])
    assert result.exit_code == 2
    assert "INSTALL_REQUIRES_TTY" in result.output


def test_cli_install_non_tty_with_force_writes_silently(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    result = _invoke(["completion", "bash", "--install", "--force"])
    assert result.exit_code == 0
    bashrc = tmp_path / ".bashrc"
    assert bashrc.exists()
    assert "_THOTH_COMPLETE" in bashrc.read_text()


def test_cli_install_manual_prints_block_never_writes(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    result = _invoke(["completion", "bash", "--install", "--manual"])
    assert result.exit_code == 0
    assert "# >>> thoth completion >>>" in result.output
    assert not (tmp_path / ".bashrc").exists()


def test_cli_install_manual_with_force_exits_2_mutex(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    result = _invoke(["completion", "bash", "--install", "--manual", "--force"])
    assert result.exit_code == 2


def test_cli_install_with_json_envelope_on_success(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    result = _invoke(["completion", "bash", "--install", "--force", "--json"])
    assert result.exit_code == 0
    payload = _json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["data"]["action"] == "written"
    assert payload["data"]["path"].endswith(".bashrc")
