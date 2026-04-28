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


def _mock_stream(prompt: str, mode: str = "thinking") -> str:
    return f"# Mock streaming response (mode={mode})\n\nEcho: {prompt}\n\nDone."


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


def test_ask_forwards_out_and_append_to_research_runner(monkeypatch, tmp_path):
    captured = _stub_run_research(monkeypatch)
    target = tmp_path / "answer.md"

    r = CliRunner().invoke(
        cli,
        ["ask", "topic", "--out", str(target), "--append"],
    )

    assert r.exit_code == 0, r.output
    assert captured["out_specs"] == (str(target),)
    assert captured["append"] is True


def test_ask_out_file_writes_streamed_mock_response(isolated_thoth_home, monkeypatch, tmp_path):
    monkeypatch.setenv("MOCK_API_KEY", "test")
    target = tmp_path / "p18-smoke.md"
    expected = _mock_stream("test 1")

    r = CliRunner().invoke(
        cli,
        [
            "ask",
            "test 1",
            "--mode",
            "thinking",
            "--provider",
            "mock",
            "--out",
            str(target),
        ],
    )

    assert r.exit_code == 0, r.output
    assert r.output == ""
    assert target.read_text() == expected


def test_ask_out_comma_list_tees_to_stdout_and_file(isolated_thoth_home, monkeypatch, tmp_path):
    monkeypatch.setenv("MOCK_API_KEY", "test")
    target = tmp_path / "p18-tee.md"
    expected = _mock_stream("test 2 teed")

    r = CliRunner().invoke(
        cli,
        [
            "ask",
            "test 2 teed",
            "--mode",
            "thinking",
            "--provider",
            "mock",
            "--out",
            f"-,{target}",
        ],
    )

    assert r.exit_code == 0, r.output
    assert r.output == expected
    assert target.read_text() == expected


def test_ask_out_repeatable_form_tees_to_stdout_and_file(
    isolated_thoth_home, monkeypatch, tmp_path
):
    monkeypatch.setenv("MOCK_API_KEY", "test")
    target = tmp_path / "p18-tee2.md"
    expected = _mock_stream("test 3")

    r = CliRunner().invoke(
        cli,
        [
            "ask",
            "test 3",
            "--mode",
            "thinking",
            "--provider",
            "mock",
            "--out",
            "-",
            "--out",
            str(target),
        ],
    )

    assert r.exit_code == 0, r.output
    assert r.output == expected
    assert target.read_text() == expected


def test_ask_out_append_concatenates_second_run(isolated_thoth_home, monkeypatch, tmp_path):
    monkeypatch.setenv("MOCK_API_KEY", "test")
    target = tmp_path / "p18-append.md"
    target.write_text("stale")

    first = _mock_stream("first run")
    first_result = CliRunner().invoke(
        cli,
        [
            "ask",
            "first run",
            "--mode",
            "thinking",
            "--provider",
            "mock",
            "--out",
            str(target),
        ],
    )

    assert first_result.exit_code == 0, first_result.output
    assert first_result.output == ""
    assert target.read_text() == first

    second = _mock_stream("second run")
    second_result = CliRunner().invoke(
        cli,
        [
            "ask",
            "second run",
            "--mode",
            "thinking",
            "--provider",
            "mock",
            "--out",
            str(target),
            "--append",
        ],
    )

    assert second_result.exit_code == 0, second_result.output
    assert second_result.output == ""
    assert target.read_text() == first + second


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


def test_ask_interactive_flag_rejected(monkeypatch):
    _stub_run_research(monkeypatch)
    r = CliRunner().invoke(cli, ["ask", "topic", "--interactive"])
    assert r.exit_code == 2
    assert "--interactive does not apply" in r.output


def test_ask_clarify_flag_rejected(monkeypatch):
    _stub_run_research(monkeypatch)
    r = CliRunner().invoke(cli, ["ask", "topic", "--clarify"])
    assert r.exit_code == 2
    assert "--clarify does not apply" in r.output


def test_ask_pick_model_flag_rejected(monkeypatch):
    _stub_run_research(monkeypatch)
    r = CliRunner().invoke(cli, ["ask", "topic", "--pick-model"])
    assert r.exit_code == 2
    assert "--pick-model does not apply" in r.output
