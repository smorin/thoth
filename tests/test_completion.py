"""Category B — completion script generation tests (spec §9.1)."""

from __future__ import annotations

import pytest


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
def test_generate_script_includes_THOTH_COMPLETE_marker(shell):
    from thoth.completion.script import generate_script

    out = generate_script(shell)
    assert "_THOTH_COMPLETE" in out
    assert shell in out


def test_generate_script_rejects_unknown_shell():
    from thoth.completion.script import generate_script

    with pytest.raises(ValueError, match="unsupported shell"):
        generate_script("powershell")


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
def test_fenced_block_brackets_with_thoth_completion_markers(shell):
    from thoth.completion.script import fenced_block

    out = fenced_block(shell)
    assert "# >>> thoth completion >>>" in out
    assert "# <<< thoth completion <<<" in out
    assert "_THOTH_COMPLETE" in out


# === Category B (T04): CLI invocation tests ===

import json as _json  # noqa: E402

from click.testing import CliRunner  # noqa: E402


def _invoke(args: list[str]):
    from thoth.cli import cli

    runner = CliRunner()
    return runner.invoke(cli, args, catch_exceptions=False)


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
def test_cli_completion_emits_eval_able_script(shell):
    result = _invoke(["completion", shell])
    assert result.exit_code == 0
    assert "_THOTH_COMPLETE" in result.output
    assert shell in result.output


def test_cli_completion_unsupported_shell_exits_2_no_json():
    result = _invoke(["completion", "powershell"])
    assert result.exit_code == 2


def test_cli_completion_unsupported_shell_with_json_emits_envelope():
    result = _invoke(["completion", "powershell", "--json"])
    assert result.exit_code == 2
    payload = _json.loads(result.output)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "UNSUPPORTED_SHELL"


def test_cli_completion_listed_in_help():
    result = _invoke(["--help"])
    assert "completion" in result.output
