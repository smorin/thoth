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
