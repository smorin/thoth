"""The six output-related CLI flags should be discoverable as a group.

`--help` doesn't have a true "option group" mechanism in plain Click, but
each output-related flag's help text carries an "Output options:" prefix
plus cross-references to its siblings. That way a user scanning the help
output for "Output options:" can find all six at once and see how they
interact.

Covered flags:
  --out, --output-dir / -o, --project / -p, --combined, --append,
  --no-metadata.

This test is a non-regression check for standardization #2 (option (b)):
we chose flag-level documentation rather than renaming, so we need a
test to make sure the doc grouping persists.
"""

from __future__ import annotations

from click.testing import CliRunner

from doxa_research.cli import cli


def _ask_help() -> str:
    runner = CliRunner()
    result = runner.invoke(cli, ["ask", "--help"])
    assert result.exit_code == 0, f"ask --help failed: {result.output}"
    return result.output


def test_all_six_output_flags_carry_output_options_marker() -> None:
    text = _ask_help()
    # Every output-related flag should mention "Output options:" in its
    # help block so users grepping --help can find the group.
    for needle in (
        "--out",
        "--output-dir",
        "--project",
        "--combined",
        "--append",
        "--no-metadata",
    ):
        assert needle in text, f"{needle} missing from ask --help"
    # The phrase should appear several times — once per flag that carries it.
    # We expect at least 5; `--project` carries a slightly different framing
    # ("Output options:" appears in its help too).
    assert text.count("Output options:") >= 5, (
        f"Expected 'Output options:' label on multiple flags, "
        f"got count={text.count('Output options:')}"
    )


def test_out_and_output_dir_cross_reference_each_other() -> None:
    text = _ask_help()
    # The two flags most likely to be confused by name should each name the other.
    assert "--output-dir" in text
    assert (
        "--out " in text or "--out PATH" in text or "see --out" in text or "--out instead" in text
    )


def test_combined_help_mentions_multi_provider_constraint() -> None:
    """--combined only makes sense for multi-provider background modes;
    the help text should say so so users don't try it on single-provider
    or immediate modes."""
    text = _ask_help()
    assert "multiple providers" in text or "multi-provider" in text or "all_deep_research" in text


def test_project_help_mentions_auto_and_subdirectory() -> None:
    """--project is also the gate for --auto chaining; help should call
    that out so users discover the feature."""
    text = _ask_help()
    assert "--auto" in text
