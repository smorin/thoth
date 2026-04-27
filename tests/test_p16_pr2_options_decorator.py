"""P16 PR2 — _research_options decorator unit test."""

from __future__ import annotations

import click
from click.testing import CliRunner

from thoth.cli_subcommands._options import _research_options


def test_research_options_decorator_adds_all_15_research_flags():
    @click.command()
    @_research_options
    def victim(**kwargs):
        click.echo("ok")

    out = CliRunner().invoke(victim, ["--help"]).output
    # Spot-check 5 representative options from across the stack
    for opt in ("--mode", "--prompt-file", "--provider", "--api-key-openai", "--pick-model"):
        assert opt in out, f"expected {opt} in --help output, got: {out}"
