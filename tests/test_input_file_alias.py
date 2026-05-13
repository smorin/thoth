"""P24-TS22: CLI regression tests for `--input-file` as alias of `--prompt-file`.

Before P24-T25 these tests fail because `--input-file` is currently routed
into `run_research(..., input_file=...)` (which populates
`OperationStatus.input_files`) instead of being read into the effective
prompt. The spec for section 9 of P24 makes `--input-file PATH` a
backward-compatible alias for `--prompt-file PATH`: same read path, same
byte cap, same UTF-8 handling, same stdin (`-`) semantics, same mutex
rules, and identical provider payload / checkpoint metadata. Alias usage
must NOT populate `OperationStatus.input_files`.
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from thoth.cli import cli


def _stub_run_research(monkeypatch) -> dict:
    """Stub run_research and return the dict that captures its kwargs."""
    captured: dict = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return 0

    monkeypatch.setattr("thoth.run.run_research", fake_run)
    return captured


# --- Root form: thoth --input-file PATH MODE ---------------------------------


def test_input_file_root_reads_contents_as_prompt(tmp_path: Path, monkeypatch):
    captured = _stub_run_research(monkeypatch)
    f = tmp_path / "p.txt"
    f.write_text("hello from input-file")

    r = CliRunner().invoke(cli, ["--input-file", str(f), "default"])
    assert r.exit_code == 0, r.output
    assert captured.get("prompt") == "hello from input-file"


def test_input_file_root_does_not_populate_input_files(tmp_path: Path, monkeypatch):
    captured = _stub_run_research(monkeypatch)
    f = tmp_path / "p.txt"
    f.write_text("payload")

    r = CliRunner().invoke(cli, ["--input-file", str(f), "default"])
    assert r.exit_code == 0, r.output
    # Alias usage must not pass the path through as an input_file; otherwise
    # `OperationStatus.input_files` ends up rendered in checkpoint + metadata.
    assert captured.get("input_file") is None


def test_input_file_root_matches_prompt_file_kwargs(tmp_path: Path, monkeypatch):
    """Both flags must produce identical run_research kwargs (modulo flag-name)."""
    f = tmp_path / "p.txt"
    f.write_text("same payload either way")

    captured_pf = _stub_run_research(monkeypatch)
    r1 = CliRunner().invoke(cli, ["--prompt-file", str(f), "default"])
    assert r1.exit_code == 0, r1.output
    snapshot_pf = dict(captured_pf)

    captured_if = _stub_run_research(monkeypatch)
    r2 = CliRunner().invoke(cli, ["--input-file", str(f), "default"])
    assert r2.exit_code == 0, r2.output

    # Prompt body delivered to the provider must match exactly.
    assert captured_if.get("prompt") == snapshot_pf.get("prompt")
    # input_file kwarg must be absent for alias usage (load-bearing for
    # checkpoint metadata: no `input_files:` line rendered).
    assert captured_if.get("input_file") is None
    assert snapshot_pf.get("input_file") is None


def test_input_file_root_pick_model_counts_as_prompt_source(tmp_path: Path, monkeypatch):
    captured = _stub_run_research(monkeypatch)
    picked = {}

    def fake_pick(models):
        picked["called"] = True
        return "gpt-4o-mini"

    monkeypatch.setattr("thoth.interactive_picker.pick_model", fake_pick)
    f = tmp_path / "p.txt"
    f.write_text("prompt for model picker")

    r = CliRunner().invoke(cli, ["--input-file", str(f), "--mode", "default", "--pick-model"])

    assert r.exit_code == 0, r.output
    assert picked.get("called") is True
    assert captured.get("prompt") == "prompt for model picker"
    assert captured.get("input_file") is None
    assert captured.get("model_override") == "gpt-4o-mini"


def test_input_file_root_stdin(monkeypatch):
    captured = _stub_run_research(monkeypatch)
    r = CliRunner().invoke(cli, ["--input-file", "-", "default"], input="from stdin")
    assert r.exit_code == 0, r.output
    assert captured.get("prompt") == "from stdin"
    assert captured.get("input_file") is None


def test_input_file_root_oversized_rejected(tmp_path: Path, monkeypatch):
    _stub_run_research(monkeypatch)
    big = tmp_path / "big.txt"
    big.write_bytes(b"x" * (1024 * 1024 + 1))

    r = CliRunner().invoke(cli, ["--input-file", str(big), "default"])
    assert r.exit_code != 0
    assert "exceeds" in r.output


def test_input_file_root_non_utf8_rejected(tmp_path: Path, monkeypatch):
    _stub_run_research(monkeypatch)
    bad = tmp_path / "latin1.txt"
    bad.write_bytes(b"\xff\xfe non-utf8 bytes")

    r = CliRunner().invoke(cli, ["--input-file", str(bad), "default"])
    assert r.exit_code != 0
    assert "UTF-8" in r.output or "utf-8" in r.output


def test_input_file_root_mutex_with_prompt(tmp_path: Path, monkeypatch):
    _stub_run_research(monkeypatch)
    f = tmp_path / "p.txt"
    f.write_text("file-prompt")

    r = CliRunner().invoke(cli, ["--input-file", str(f), "--prompt", "inline", "default"])
    assert r.exit_code != 0
    assert "input-file" in r.output.lower() or "prompt" in r.output.lower()


def test_input_file_root_mutex_with_prompt_file(tmp_path: Path, monkeypatch):
    _stub_run_research(monkeypatch)
    a = tmp_path / "a.txt"
    a.write_text("a")
    b = tmp_path / "b.txt"
    b.write_text("b")

    r = CliRunner().invoke(cli, ["--input-file", str(a), "--prompt-file", str(b), "default"])
    assert r.exit_code != 0


def test_input_file_root_mutex_with_positional(tmp_path: Path, monkeypatch):
    _stub_run_research(monkeypatch)
    f = tmp_path / "p.txt"
    f.write_text("payload")

    r = CliRunner().invoke(cli, ["--input-file", str(f), "default", "extra prompt"])
    assert r.exit_code != 0


# --- ask subcommand form: thoth ask --input-file PATH ------------------------


def test_input_file_ask_reads_contents_as_prompt(tmp_path: Path, monkeypatch):
    captured = _stub_run_research(monkeypatch)
    f = tmp_path / "p.txt"
    f.write_text("ask prompt body")

    r = CliRunner().invoke(cli, ["ask", "--input-file", str(f)])
    assert r.exit_code == 0, r.output
    assert captured.get("prompt") == "ask prompt body"
    assert captured.get("input_file") is None


def test_input_file_ask_inherited_from_root(tmp_path: Path, monkeypatch):
    captured = _stub_run_research(monkeypatch)
    f = tmp_path / "p.txt"
    f.write_text("inherited body")

    r = CliRunner().invoke(cli, ["--input-file", str(f), "ask"])
    assert r.exit_code == 0, r.output
    assert captured.get("prompt") == "inherited body"
    assert captured.get("input_file") is None


def test_input_file_ask_stdin(monkeypatch):
    captured = _stub_run_research(monkeypatch)
    r = CliRunner().invoke(cli, ["ask", "--input-file", "-"], input="ask stdin")
    assert r.exit_code == 0, r.output
    assert captured.get("prompt") == "ask stdin"
    assert captured.get("input_file") is None


def test_input_file_ask_mutex_with_positional(tmp_path: Path, monkeypatch):
    _stub_run_research(monkeypatch)
    f = tmp_path / "p.txt"
    f.write_text("file")

    r = CliRunner().invoke(cli, ["ask", "--input-file", str(f), "inline prompt"])
    assert r.exit_code != 0


def test_input_file_ask_mutex_with_prompt(tmp_path: Path, monkeypatch):
    _stub_run_research(monkeypatch)
    f = tmp_path / "p.txt"
    f.write_text("file")

    r = CliRunner().invoke(cli, ["ask", "--input-file", str(f), "--prompt", "inline"])
    assert r.exit_code != 0


def test_input_file_ask_mutex_with_prompt_file(tmp_path: Path, monkeypatch):
    _stub_run_research(monkeypatch)
    a = tmp_path / "a.txt"
    a.write_text("a")
    b = tmp_path / "b.txt"
    b.write_text("b")

    r = CliRunner().invoke(cli, ["ask", "--input-file", str(a), "--prompt-file", str(b)])
    assert r.exit_code != 0
