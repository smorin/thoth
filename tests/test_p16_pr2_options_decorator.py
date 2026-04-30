"""P16 PR2 — _research_options decorator unit test."""

from __future__ import annotations

import click
from click.testing import CliRunner

from thoth.cli_subcommands._options import _RESEARCH_OPTIONS, _research_options


def test_research_options_decorator_adds_all_research_flags():
    # Catches accidental additions/removals in _RESEARCH_OPTIONS.
    # P18 Phase E added --out (repeatable) and --append; P21 added --profile;
    # P18-T27 added --cancel-on-interrupt/--no-cancel-on-interrupt.
    assert len(_RESEARCH_OPTIONS) == 25, (
        f"expected 25 research-options entries (21 from PR2 + 2 from P18 Phase E + "
        f"1 from P21 + 1 from P18-T27), got {len(_RESEARCH_OPTIONS)}"
    )

    @click.command()
    @_research_options
    def victim(**kwargs):
        click.echo("ok")

    out = CliRunner().invoke(victim, ["--help"]).output
    # Spot-check representative options from across the stack
    for opt in (
        "--mode",
        "--prompt-file",
        "--provider",
        "--api-key-openai",
        "--pick-model",
        "--out",  # P18 Phase E
        "--cancel-on-interrupt",  # P18-T27
    ):
        assert opt in out, f"expected {opt} in --help output, got: {out}"
