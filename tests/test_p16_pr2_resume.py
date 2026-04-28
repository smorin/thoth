"""P16 PR2 — `resume` subcommand tests (Categories A + F).

The Category A/F tests below stub `thoth.run.resume_operation` to verify
CLI-side forwarding into the function's kwargs. The "honor downstream"
test at the bottom of the file exercises the *body* of `resume_operation`
to verify the honored kwargs are actually threaded into
`OutputManager(...)`, `create_provider(...)`, and `_poll_display(...)`
(Q1-PR2-C contract; PR2 review-fix C1).
"""

from __future__ import annotations

import asyncio

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


# Category C1 (PR2 review-fix): honored kwargs are threaded into the
# real `resume_operation` body — into OutputManager, create_provider,
# and _poll_display. Without this test, the CLI-side stubs above pass
# while the function body silently drops the kwargs.


def test_resume_operation_threads_honored_kwargs_to_downstream(monkeypatch):
    """P16-PR2-C1: resume_operation passes quiet/no_metadata/timeout_override/cli_api_keys downstream."""
    from datetime import datetime

    from thoth import run as run_mod
    from thoth.models import OperationStatus

    captured: dict[str, object] = {}

    class _StopResume(Exception):
        pass

    # Capture OutputManager kwargs.
    class FakeOutputManager:
        def __init__(self, config, no_metadata=False):
            captured["om_no_metadata"] = no_metadata

    # Capture create_provider kwargs and short-circuit before reconnect.
    def fake_create_provider(provider_name, config, **kwargs):
        captured["cp_provider_name"] = provider_name
        captured["cp_cli_api_key"] = kwargs.get("cli_api_key")
        captured["cp_timeout_override"] = kwargs.get("timeout_override")
        captured["cp_mode_config"] = kwargs.get("mode_config")
        # Raise a sentinel so we short-circuit before _poll_display is reached.
        raise _StopResume()

    # Build a synthetic running operation so resume_operation reaches the
    # create_provider site.
    now = datetime.now()
    op = OperationStatus(
        id="research-20260101-000000-deadbeefdeadbeef",
        prompt="test resume threading",
        mode="default",
        status="running",
        created_at=now,
        updated_at=now,
        providers={"mock": {"status": "running", "job_id": "job-1"}},
    )

    # Stub CheckpointManager.load → return our op; .save → noop.
    async def fake_load(self, operation_id):
        return op

    async def fake_save(self, operation):
        return None

    monkeypatch.setattr(run_mod.CheckpointManager, "load", fake_load)
    monkeypatch.setattr(run_mod.CheckpointManager, "save", fake_save)
    monkeypatch.setattr(run_mod, "OutputManager", FakeOutputManager)
    monkeypatch.setattr(run_mod, "create_provider", fake_create_provider)

    # Now invoke resume_operation with the honor-set; expect _StopResume from
    # fake_create_provider, but only AFTER OutputManager has captured its kwargs.
    coro = run_mod.resume_operation(
        op.id,
        quiet=True,
        no_metadata=True,
        timeout_override=42.5,
        cli_api_keys={"mock": "mock-key-from-cli"},
    )
    # create_provider raises _StopResume; resume_operation lets it propagate
    # (it only catches APIKeyError/ProviderError/ThothError). Catch it here.
    with pytest.raises(_StopResume):
        asyncio.run(coro)

    # Assertions: every honored kwarg landed on the right downstream call.
    assert captured["om_no_metadata"] is True, "OutputManager did not receive no_metadata=True"
    assert captured["cp_cli_api_key"] == "mock-key-from-cli", (
        "create_provider did not receive cli_api_key from cli_api_keys.get(provider_name)"
    )
    assert captured["cp_timeout_override"] == 42.5, (
        "create_provider did not receive timeout_override"
    )
    assert captured["cp_provider_name"] == "mock"
