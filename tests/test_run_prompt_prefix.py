"""P21-TS09: integration — prompt_prefix wiring into the prompt assembly.

These tests exercise the assembly helper that `run_research` calls. They
cover:
  - When a prefix resolves, the assembled prompt is f"{prefix}\\n\\n{user_prompt}".
  - When no prefix resolves, the prompt is unchanged (no leading whitespace).
  - The mode's `system_prompt` is independent of the prefix path.

The full run_research call is exercised by the thoth_test integration suite.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from thoth.config import ConfigManager
from thoth.config_profiles import assemble_prompt_with_prefix


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _cm(isolated: Path, body: str, *, profile: str | None = None) -> ConfigManager:
    from thoth.paths import user_config_file

    _write(user_config_file(), body)
    cm = ConfigManager()
    cli_args: dict[str, object] = {}
    if profile:
        cli_args["_profile"] = profile
    cm.load_all_layers(cli_args)
    return cm


def test_no_prefix_returns_prompt_unchanged(isolated_thoth_home: Path) -> None:
    cm = _cm(isolated_thoth_home, 'version = "2.0"\n')
    result = assemble_prompt_with_prefix(cm, "default", "hello world")
    assert result == "hello world"


def test_general_prefix_prepended_with_blank_line(isolated_thoth_home: Path) -> None:
    cm = _cm(
        isolated_thoth_home,
        'version = "2.0"\n[general]\nprompt_prefix = "Be thorough."\n',
    )
    result = assemble_prompt_with_prefix(cm, "default", "research vector dbs")
    assert result == "Be thorough.\n\nresearch vector dbs"


def test_active_profile_prefix_replaces_general(isolated_thoth_home: Path) -> None:
    cm = _cm(
        isolated_thoth_home,
        """version = "2.0"
[general]
prompt_prefix = "GLOBAL"

[profiles.deep]
prompt_prefix = "Cite primary sources."
""",
        profile="deep",
    )
    result = assemble_prompt_with_prefix(cm, "deep_research", "compare X and Y")
    assert result == "Cite primary sources.\n\ncompare X and Y"
    assert "GLOBAL" not in result


def test_profile_mode_specific_prefix_wins(isolated_thoth_home: Path) -> None:
    cm = _cm(
        isolated_thoth_home,
        """version = "2.0"
[profiles.deep]
prompt_prefix = "GENERAL_PROFILE"

[profiles.deep.modes.deep_research]
prompt_prefix = "DEEP_RESEARCH_ONLY"
""",
        profile="deep",
    )
    deep = assemble_prompt_with_prefix(cm, "deep_research", "topic")
    other = assemble_prompt_with_prefix(cm, "thinking", "topic")
    assert deep == "DEEP_RESEARCH_ONLY\n\ntopic"
    assert other == "GENERAL_PROFILE\n\ntopic"


def test_empty_user_prompt_still_assembles(isolated_thoth_home: Path) -> None:
    cm = _cm(
        isolated_thoth_home,
        'version = "2.0"\n[general]\nprompt_prefix = "PREFIX"\n',
    )
    # Edge case: empty user prompt. Caller's responsibility to validate
    # non-empty prompts; this helper just assembles what it's given.
    assert assemble_prompt_with_prefix(cm, "default", "") == "PREFIX\n\n"


@pytest.mark.parametrize("user_prompt", ["short", "multi\nline\nprompt", "  whitespace  "])
def test_user_prompt_preserved_verbatim(isolated_thoth_home: Path, user_prompt: str) -> None:
    cm = _cm(
        isolated_thoth_home,
        'version = "2.0"\n[general]\nprompt_prefix = "PREFIX"\n',
    )
    result = assemble_prompt_with_prefix(cm, "default", user_prompt)
    assert result == f"PREFIX\n\n{user_prompt}"
