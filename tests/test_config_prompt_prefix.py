"""P21-TS07: hierarchy tests for resolve_prompt_prefix.

Resolution order (most-specific first):
  1. profiles.<active>.modes.<MODE>.prompt_prefix
  2. profiles.<active>.prompt_prefix
  3. modes.<MODE>.prompt_prefix
  4. general.prompt_prefix
  5. None

More-specific REPLACES less-specific — no concatenation.
Empty string is treated as "unset" so a level can't accidentally erase outer values.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from thoth.config import ConfigManager
from thoth.config_profiles import resolve_prompt_prefix


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


def test_no_prefix_anywhere_returns_none(isolated_thoth_home: Path) -> None:
    cm = _cm(isolated_thoth_home, 'version = "2.0"\n')
    assert resolve_prompt_prefix(cm, "default") is None


def test_general_prompt_prefix_applies_when_no_other_levels(
    isolated_thoth_home: Path,
) -> None:
    cm = _cm(
        isolated_thoth_home,
        'version = "2.0"\n[general]\nprompt_prefix = "GLOBAL"\n',
    )
    assert resolve_prompt_prefix(cm, "default") == "GLOBAL"


def test_modes_prefix_overrides_general(isolated_thoth_home: Path) -> None:
    cm = _cm(
        isolated_thoth_home,
        """version = "2.0"
[general]
prompt_prefix = "GLOBAL"

[modes.deep_research]
prompt_prefix = "MODE"
""",
    )
    assert resolve_prompt_prefix(cm, "deep_research") == "MODE"
    # Other modes still get general
    assert resolve_prompt_prefix(cm, "default") == "GLOBAL"


def test_profile_prefix_overrides_modes_and_general(isolated_thoth_home: Path) -> None:
    cm = _cm(
        isolated_thoth_home,
        """version = "2.0"
[general]
prompt_prefix = "GLOBAL"

[modes.deep_research]
prompt_prefix = "MODE"

[profiles.fast]
prompt_prefix = "PROFILE"
""",
        profile="fast",
    )
    assert resolve_prompt_prefix(cm, "deep_research") == "PROFILE"
    assert resolve_prompt_prefix(cm, "default") == "PROFILE"


def test_profile_modes_prefix_is_most_specific(isolated_thoth_home: Path) -> None:
    cm = _cm(
        isolated_thoth_home,
        """version = "2.0"
[general]
prompt_prefix = "GLOBAL"

[modes.deep_research]
prompt_prefix = "MODE"

[profiles.fast]
prompt_prefix = "PROFILE"

[profiles.fast.modes.deep_research]
prompt_prefix = "PROFILE_MODE"
""",
        profile="fast",
    )
    assert resolve_prompt_prefix(cm, "deep_research") == "PROFILE_MODE"
    # default mode falls back to PROFILE
    assert resolve_prompt_prefix(cm, "default") == "PROFILE"


def test_no_active_profile_skips_profile_levels(isolated_thoth_home: Path) -> None:
    cm = _cm(
        isolated_thoth_home,
        """version = "2.0"
[general]
prompt_prefix = "GLOBAL"

[profiles.fast]
prompt_prefix = "PROFILE"
""",
    )
    # No --profile / THOTH_PROFILE / default_profile, so profile is not active
    assert cm.profile_selection.name is None
    assert resolve_prompt_prefix(cm, "default") == "GLOBAL"


def test_empty_string_is_treated_as_unset(isolated_thoth_home: Path) -> None:
    cm = _cm(
        isolated_thoth_home,
        """version = "2.0"
[general]
prompt_prefix = "GLOBAL"

[profiles.fast]
prompt_prefix = ""
""",
        profile="fast",
    )
    # Empty string at profile level should NOT override; falls through to general
    assert resolve_prompt_prefix(cm, "default") == "GLOBAL"


def test_replace_semantics_no_concatenation(isolated_thoth_home: Path) -> None:
    cm = _cm(
        isolated_thoth_home,
        """version = "2.0"
[general]
prompt_prefix = "OUTER"

[profiles.fast]
prompt_prefix = "INNER"
""",
        profile="fast",
    )
    # Result is exactly INNER, not "OUTER\n\nINNER"
    result = resolve_prompt_prefix(cm, "default")
    assert result == "INNER"
    assert "OUTER" not in (result or "")


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("deep_research", "PROFILE_MODE"),
        ("thinking", "PROFILE"),
        ("default", "PROFILE"),
    ],
)
def test_resolution_per_mode(isolated_thoth_home: Path, mode: str, expected: str) -> None:
    cm = _cm(
        isolated_thoth_home,
        """version = "2.0"
[profiles.fast]
prompt_prefix = "PROFILE"

[profiles.fast.modes.deep_research]
prompt_prefix = "PROFILE_MODE"
""",
        profile="fast",
    )
    assert resolve_prompt_prefix(cm, mode) == expected
