"""Documentation coverage checks for user-visible command surfaces."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
JSON_OUTPUT_DOC = REPO_ROOT / "docs" / "json-output.md"


def _section(text: str, heading: str) -> str:
    start = text.index(heading)
    rest = text[start + len(heading) :]
    next_heading = re.search(r"\n#{2,3} ", rest)
    if next_heading is None:
        return rest
    return rest[: next_heading.start()]


def test_readme_main_command_reference_lists_all_registered_top_level_commands() -> None:
    from thoth.cli import cli

    text = README.read_text(encoding="utf-8")
    section = _section(text, "### Main Commands")
    documented = set(re.findall(r"^\| ([a-z][a-z-]*) \|", section, flags=re.MULTILINE))
    registered = {
        name for name, command in cli.commands.items() if not getattr(command, "hidden", False)
    }

    assert registered <= documented


def test_readme_profile_docs_do_not_describe_shipped_cli_as_future_work() -> None:
    text = README.read_text(encoding="utf-8")

    assert "CLI management coming in P21b" not in text
    assert "Once P21b ships" not in text


def test_readme_interactive_slash_docs_cover_fullscreen_and_fallback_commands() -> None:
    text = README.read_text(encoding="utf-8")

    assert "/keybindings" in text
    assert "/multiline" in text


def test_json_output_docs_cover_json_command_families() -> None:
    text = JSON_OUTPUT_DOC.read_text(encoding="utf-8")
    required_snippets = [
        "`ask --json`",
        "`init --json --non-interactive`",
        "`status OP_ID --json`",
        "`list --json`",
        "`providers list --json`",
        "`providers models --json`",
        "`providers check --json`",
        "`config get KEY --json`",
        "`config set KEY VALUE --json`",
        "`config unset KEY --json`",
        "`config list --json`",
        "`config path --json`",
        "`config edit --json`",
        "`config profiles list --json`",
        "`config profiles show NAME --json`",
        "`config profiles current --json`",
        "`config profiles set-default NAME --json`",
        "`config profiles unset-default --json`",
        "`config profiles add NAME --json`",
        "`config profiles set NAME KEY VALUE --json`",
        "`config profiles unset NAME KEY --json`",
        "`config profiles remove NAME --json`",
        "`modes list --json`",
        "`resume OP_ID --json`",
        "`cancel OP_ID --json`",
        "`completion <shell> --install --json`",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in text]
    assert missing == []
