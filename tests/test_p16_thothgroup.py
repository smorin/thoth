"""P16-TS02..06: ThothGroup unit tests."""

from __future__ import annotations

import click
import pytest
from click.testing import CliRunner

from thoth.help import ThothGroup


@pytest.fixture
def fake_group() -> click.Group:
    """Minimal ThothGroup with one registered subcommand for testing."""

    @click.group(cls=ThothGroup)
    def cli():
        pass

    @cli.command(name="known")
    def known_cmd():
        click.echo("known invoked")

    return cli


def test_resolve_command_returns_none_for_unknown(fake_group):
    """P16-TS02: resolve_command returns None for unregistered args
    (so invoke can take over for mode-positional / bare-prompt fallback)."""
    ctx = click.Context(fake_group)
    result = fake_group.resolve_command(ctx, ["unknown_word"])
    assert result == (None, None, ["unknown_word"]) or result is None


def test_invoke_routes_mode_positional(fake_group, monkeypatch):
    """P16-TS03: invoke routes BUILTIN_MODES first arg to research path."""
    captured = {}

    def fake_run(mode, prompt, ctx_obj):
        captured["mode"] = mode
        captured["prompt"] = prompt
        captured["ctx_obj"] = ctx_obj

    # Stub _run_research_default in the help module
    monkeypatch.setattr("thoth.help._run_research_default", fake_run)
    monkeypatch.setattr("thoth.config.BUILTIN_MODES", {"deep_research", "default"})

    runner = CliRunner()
    result = runner.invoke(fake_group, ["deep_research", "explain", "X"])

    assert captured == {"mode": "deep_research", "prompt": "explain X", "ctx_obj": None}
    assert result.exit_code == 0


def test_invoke_routes_bare_prompt(fake_group, monkeypatch):
    """P16-TS04: invoke routes unknown first-word to default-mode bare-prompt."""
    captured = {}

    def fake_run(mode, prompt, ctx_obj):
        captured["mode"] = mode
        captured["prompt"] = prompt

    monkeypatch.setattr("thoth.help._run_research_default", fake_run)
    monkeypatch.setattr("thoth.config.BUILTIN_MODES", {"deep_research", "default"})

    runner = CliRunner()
    result = runner.invoke(fake_group, ["explain", "transformers"])

    assert captured == {"mode": "default", "prompt": "explain transformers"}
    assert result.exit_code == 0


def test_invoke_routes_registered_subcommand(fake_group):
    """P16-TS05: invoke routes a registered subcommand via standard Click."""
    runner = CliRunner()
    result = runner.invoke(fake_group, ["known"])
    assert result.exit_code == 0
    assert "known invoked" in result.output


def test_init_subcommand_registered():
    """P16-TS06: init is registered as a Click subcommand on the cli group."""
    from thoth.cli import cli

    assert "init" in cli.commands


def test_init_subcommand_invokes_handler(monkeypatch):
    """P16-TS07: thoth init dispatches through Click to CommandHandler.init_command."""
    from thoth.cli import cli

    called = {}

    def fake_init(self, config_path=None):
        called["config_path"] = config_path

    monkeypatch.setattr("thoth.commands.CommandHandler.init_command", fake_init)

    runner = CliRunner()
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0
    assert "config_path" in called


def test_status_subcommand_registered():
    from thoth.cli import cli
    assert "status" in cli.commands


def test_status_requires_op_id():
    """P16-TS08: thoth status (no OP_ID) → Click missing-arg error, exit 2."""
    from thoth.cli import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["status"])
    assert result.exit_code == 2
    assert "Missing argument" in result.output or "OP_ID" in result.output


def test_status_invokes_handler(monkeypatch):
    from thoth.cli import cli
    called = {}

    def fake_status(self, operation_id):
        called["op_id"] = operation_id

    monkeypatch.setattr(
        "thoth.commands.CommandHandler.status_command", fake_status
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["status", "abc123"])
    assert result.exit_code == 0
    assert called["op_id"] == "abc123"


def test_list_subcommand_registered():
    from thoth.cli import cli
    assert "list" in cli.commands


def test_list_all_flag(monkeypatch):
    from thoth.cli import cli
    called = {}

    def fake_list(self, show_all=False):
        called["show_all"] = show_all

    monkeypatch.setattr("thoth.commands.CommandHandler.list_command", fake_list)
    runner = CliRunner()
    result = runner.invoke(cli, ["list", "--all"])
    assert result.exit_code == 0
    assert called["show_all"] is True


def test_providers_subgroup_registered():
    from thoth.cli import cli
    assert "providers" in cli.commands
    assert isinstance(cli.commands["providers"], click.Group)


def test_providers_list_invokes_correct_function(monkeypatch):
    from thoth.cli import cli
    called = {}

    def fake_list(cfg):
        called["invoked"] = True
        return 0

    monkeypatch.setattr("thoth.commands.providers_list", fake_list)
    runner = CliRunner()
    result = runner.invoke(cli, ["providers", "list"])
    assert result.exit_code == 0
    assert called["invoked"] is True


def test_config_subgroup_registered():
    from thoth.cli import cli
    assert "config" in cli.commands
    assert isinstance(cli.commands["config"], click.Group)


def test_config_list_invokes_handler(monkeypatch):
    from thoth.cli import cli
    called = {}

    def fake_config_command(op, rest):
        called["op"] = op
        called["rest"] = rest
        return 0

    monkeypatch.setattr("thoth.config_cmd.config_command", fake_config_command)
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "list"])
    assert result.exit_code == 0
    assert called["op"] == "list"


def test_modes_registered():
    from thoth.cli import cli
    assert "modes" in cli.commands


def test_modes_list_invokes_handler(monkeypatch):
    from thoth.cli import cli
    called = {}

    def fake_modes_command(op, rest):
        called["op"] = op
        return 0

    monkeypatch.setattr("thoth.modes_cmd.modes_command", fake_modes_command)
    runner = CliRunner()
    result = runner.invoke(cli, ["modes"])
    assert result.exit_code == 0
    # When no op is given, modes shows the list (current behavior)
    assert called["op"] is None or called["op"] == "list"
