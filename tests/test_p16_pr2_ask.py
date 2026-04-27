"""P16 PR2 — `ask` subcommand tests (Categories A + G)."""

from __future__ import annotations

from click.testing import CliRunner

from thoth.cli import cli


def _stub_run_research(monkeypatch):
    captured: dict[str, object] = {}

    def fake(**kwargs):
        captured.update(kwargs)
        return None

    monkeypatch.setattr("thoth.run.run_research", fake)
    return captured


# Category A: ask happy paths


def test_ask_with_positional_prompt(monkeypatch):
    captured = _stub_run_research(monkeypatch)
    r = CliRunner().invoke(cli, ["ask", "how", "does", "DNS", "work"])
    assert r.exit_code == 0, r.output
    assert captured["mode"] == "default"
    assert captured["prompt"] == "how does DNS work"


def test_ask_with_explicit_mode(monkeypatch):
    captured = _stub_run_research(monkeypatch)
    r = CliRunner().invoke(cli, ["ask", "--mode", "deep_research", "topic"])
    assert r.exit_code == 0, r.output
    assert captured["mode"] == "deep_research"
    assert captured["prompt"] == "topic"


def test_ask_with_prompt_flag(monkeypatch):
    captured = _stub_run_research(monkeypatch)
    r = CliRunner().invoke(cli, ["ask", "--prompt", "via flag"])
    assert r.exit_code == 0, r.output
    assert captured["prompt"] == "via flag"


def test_ask_with_prompt_file(monkeypatch, tmp_path):
    captured = _stub_run_research(monkeypatch)
    pf = tmp_path / "p.txt"
    pf.write_text("file prompt content")
    r = CliRunner().invoke(cli, ["ask", "--prompt-file", str(pf)])
    assert r.exit_code == 0, r.output
    assert captured["prompt"] == "file prompt content"


def test_ask_via_group_level_flags(monkeypatch):
    """Q3-PR2-C: `thoth --mode X ask "..."` works (group form)."""
    captured = _stub_run_research(monkeypatch)
    r = CliRunner().invoke(cli, ["--mode", "deep_research", "ask", "topic"])
    assert r.exit_code == 0, r.output
    assert captured["mode"] == "deep_research"


def test_ask_subcommand_mode_wins_over_group_mode(monkeypatch):
    """Q3-PR2-C: subcommand value wins on conflict (Click natural)."""
    captured = _stub_run_research(monkeypatch)
    r = CliRunner().invoke(
        cli,
        ["--mode", "default", "ask", "--mode", "deep_research", "topic"],
    )
    assert r.exit_code == 0, r.output
    assert captured["mode"] == "deep_research"


# Category G: ask mutex tests


def test_ask_positional_and_prompt_flag_rejected(monkeypatch):
    _stub_run_research(monkeypatch)
    r = CliRunner().invoke(cli, ["ask", "positional", "--prompt", "flag"])
    assert r.exit_code == 2
    assert "positional" in r.output.lower() or "prompt" in r.output.lower()


def test_ask_positional_and_prompt_file_rejected(monkeypatch, tmp_path):
    _stub_run_research(monkeypatch)
    pf = tmp_path / "p.txt"
    pf.write_text("x")
    r = CliRunner().invoke(cli, ["ask", "positional", "--prompt-file", str(pf)])
    assert r.exit_code == 2


def test_ask_prompt_and_prompt_file_rejected(monkeypatch, tmp_path):
    _stub_run_research(monkeypatch)
    pf = tmp_path / "p.txt"
    pf.write_text("x")
    r = CliRunner().invoke(cli, ["ask", "--prompt", "p", "--prompt-file", str(pf)])
    assert r.exit_code == 2


def test_ask_no_prompt_at_all_rejected(monkeypatch):
    _stub_run_research(monkeypatch)
    r = CliRunner().invoke(cli, ["ask"])
    assert r.exit_code == 2
    assert "prompt" in r.output.lower()
