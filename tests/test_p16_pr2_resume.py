"""P16 PR2 — `resume` subcommand tests (Categories A + F)."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from thoth.cli import cli


def _stub_resume(monkeypatch):
    captured: dict[str, object] = {}

    async def fake(operation_id, verbose=False, ctx=None, **kwargs):
        captured["operation_id"] = operation_id
        captured["verbose"] = verbose
        captured["ctx"] = ctx
        captured.update(kwargs)
        return None

    monkeypatch.setattr("thoth.run.resume_operation", fake)
    return captured


# Category A: resume happy paths


def test_resume_with_op_id(monkeypatch):
    captured = _stub_resume(monkeypatch)
    r = CliRunner().invoke(cli, ["resume", "op_test_001"])
    assert r.exit_code == 0, r.output
    assert captured["operation_id"] == "op_test_001"


def test_resume_missing_op_id_exits_2(monkeypatch):
    _stub_resume(monkeypatch)
    r = CliRunner().invoke(cli, ["resume"])
    assert r.exit_code == 2
    assert "OP_ID" in r.output or "argument" in r.output.lower()


# Category F: honor-list (each Q1-PR2-C honored option)


def test_resume_honors_verbose(monkeypatch):
    captured = _stub_resume(monkeypatch)
    r = CliRunner().invoke(cli, ["resume", "op_x", "--verbose"])
    assert r.exit_code == 0, r.output
    assert captured["verbose"] is True


def test_resume_honors_quiet(monkeypatch):
    captured = _stub_resume(monkeypatch)
    r = CliRunner().invoke(cli, ["resume", "op_x", "--quiet"])
    assert r.exit_code == 0, r.output
    assert captured.get("quiet") is True


def test_resume_honors_no_metadata(monkeypatch):
    captured = _stub_resume(monkeypatch)
    r = CliRunner().invoke(cli, ["resume", "op_x", "--no-metadata"])
    assert r.exit_code == 0, r.output
    assert captured.get("no_metadata") is True


def test_resume_honors_timeout(monkeypatch):
    captured = _stub_resume(monkeypatch)
    r = CliRunner().invoke(cli, ["resume", "op_x", "--timeout", "60.5"])
    assert r.exit_code == 0, r.output
    assert captured.get("timeout_override") == 60.5


def test_resume_honors_api_key_openai(monkeypatch):
    captured = _stub_resume(monkeypatch)
    r = CliRunner().invoke(cli, ["resume", "op_x", "--api-key-openai", "sk-test"])
    assert r.exit_code == 0, r.output
    assert captured.get("cli_api_keys", {}).get("openai") == "sk-test"


def test_resume_honors_api_key_perplexity(monkeypatch):
    captured = _stub_resume(monkeypatch)
    r = CliRunner().invoke(cli, ["resume", "op_x", "--api-key-perplexity", "pplx-test"])
    assert r.exit_code == 0, r.output
    assert captured.get("cli_api_keys", {}).get("perplexity") == "pplx-test"


def test_resume_honors_api_key_mock(monkeypatch):
    captured = _stub_resume(monkeypatch)
    r = CliRunner().invoke(cli, ["resume", "op_x", "--api-key-mock", "mock-test"])
    assert r.exit_code == 0, r.output
    assert captured.get("cli_api_keys", {}).get("mock") == "mock-test"


def test_resume_honors_config_path(monkeypatch, tmp_path):
    captured = _stub_resume(monkeypatch)
    cfg = tmp_path / "thoth.toml"
    cfg.write_text('version = "2.0"\n')
    r = CliRunner().invoke(cli, ["resume", "op_x", "--config", str(cfg)])
    assert r.exit_code == 0, r.output
    assert captured["operation_id"] == "op_x"


# Category E: reject-list — undeclared flags are rejected by Click natively


@pytest.mark.parametrize(
    "rejected_arg",
    [
        "--auto",
        "--input-file=x.txt",
        "--prompt=foo",
        "--prompt-file=foo.txt",
        "--combined",
        "--project=p",
        "--output-dir=o",
        "--async",
        "--pick-model",
        "--interactive",
        "--clarify",
    ],
)
def test_resume_rejects_undeclared_option(monkeypatch, rejected_arg):
    _stub_resume(monkeypatch)
    r = CliRunner().invoke(cli, ["resume", "op_x", rejected_arg])
    assert r.exit_code == 2, r.output
    assert "no such option" in r.output.lower() or "unexpected" in r.output.lower()
