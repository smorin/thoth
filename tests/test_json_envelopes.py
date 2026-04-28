"""Category E — `--json` envelope contract per command (spec §8.3).

The JSON_COMMANDS list grows as each subcommand T06–T13 adds `--json`.
Category H meta-test in test_ci_lint_rules.py uses an AST walker against
src/thoth/cli_subcommands/ to assert this list stays complete.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

JSON_COMMANDS: list[tuple[str, list[str], int]] = [
    # (label, argv-after-cli, expected_exit_code)
    ("init_non_interactive", ["init", "--json", "--non-interactive"], 0),
    ("status_missing_op", ["status", "research-MISSING", "--json"], 6),
    ("list_empty", ["list", "--json"], 0),
    ("list_all_empty", ["list", "--all", "--json"], 0),
    # T09–T13 will append rows for providers, config, modes, ask,
    # resume per the spec §10 commit sequence.
]


@pytest.fixture
def cli():
    from thoth.cli import cli as _cli

    return _cli


@pytest.mark.parametrize("label,argv,exit_code", JSON_COMMANDS, ids=[c[0] for c in JSON_COMMANDS])
def test_json_envelope_contract(label, argv, exit_code, cli, isolated_thoth_home):
    runner = CliRunner()  # NOTE: drop mix_stderr=False — Click 8.3 removed it (PR2 precedent)
    result = runner.invoke(cli, argv, catch_exceptions=False)

    assert result.exit_code == exit_code, f"{label}: output={result.output}"
    payload = json.loads(result.output)
    assert isinstance(payload, dict), f"{label}: not a dict"
    assert payload.get("status") in ("ok", "error"), f"{label}: bad status field"
    if payload["status"] == "ok":
        assert isinstance(payload.get("data"), dict), f"{label}: ok-envelope missing data dict"
    else:
        err = payload.get("error")
        assert isinstance(err, dict), f"{label}: error-envelope missing error dict"
        assert isinstance(err.get("code"), str)
        assert isinstance(err.get("message"), str)


def test_init_json_without_non_interactive_emits_JSON_REQUIRES_NONINTERACTIVE(
    cli, isolated_thoth_home
):
    runner = CliRunner()
    result = runner.invoke(cli, ["init", "--json"], catch_exceptions=False)

    assert result.exit_code == 2
    payload = json.loads(result.output)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "JSON_REQUIRES_NONINTERACTIVE"


def test_status_json_missing_op_emits_OPERATION_NOT_FOUND(cli, isolated_thoth_home):
    runner = CliRunner()
    result = runner.invoke(cli, ["status", "research-MISSING", "--json"], catch_exceptions=False)

    assert result.exit_code == 6
    payload = json.loads(result.output)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "OPERATION_NOT_FOUND"
