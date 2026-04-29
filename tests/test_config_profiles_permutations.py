"""P21-TS08: permutation matrix over profile selection × tier × prefix × mode.

Axes:
  - selection_source: flag | env | config-pointer | none
  - tier:             user | project | both (project shadows)
  - prefix_present:   yes | no
  - mode:             deep_research | thinking | default

This file commits real TOML configs (inline strings) per case and asserts
the final ConfigManager state for each cell of the meaningful cross-product.
The shipped `init` examples are exercised via `_INIT_EXAMPLE_PROFILES`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from thoth.config import ConfigManager
from thoth.config_profiles import assemble_prompt_with_prefix, resolve_prompt_prefix


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


# ---------------------------------------------------------------------------
# Selection-source permutations (axis 1)
# ---------------------------------------------------------------------------


@pytest.fixture
def two_profile_user_config(isolated_thoth_home: Path) -> Path:
    from thoth.paths import user_config_file

    body = """version = "2.0"
[general]
default_mode = "default"

[profiles.fast.general]
default_mode = "thinking"
[profiles.fast]
prompt_prefix = "FAST_PREFIX"

[profiles.deep.general]
default_mode = "deep_research"
[profiles.deep]
prompt_prefix = "DEEP_PREFIX"
"""
    _write(user_config_file(), body)
    return user_config_file()


@pytest.mark.parametrize(
    "source,setup,expected_name,expected_source",
    [
        ("flag", {"_profile": "deep"}, "deep", "flag"),
        ("env", {}, "deep", "env"),
        ("config-pointer", {}, "fast", "config"),
        ("none", {}, None, "none"),
    ],
)
def test_selection_source_axis(
    two_profile_user_config: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    setup: dict,
    expected_name: str | None,
    expected_source: str,
) -> None:
    monkeypatch.delenv("THOTH_PROFILE", raising=False)

    if source == "env":
        monkeypatch.setenv("THOTH_PROFILE", "deep")
    elif source == "config-pointer":
        # Append general.default_profile = "fast" to the existing config.
        from thoth.paths import user_config_file

        existing = user_config_file().read_text()
        # Insert into [general] (already has default_mode); append a new key.
        new = existing.replace(
            '[general]\ndefault_mode = "default"',
            '[general]\ndefault_mode = "default"\ndefault_profile = "fast"',
        )
        user_config_file().write_text(new)

    cm = ConfigManager()
    cm.load_all_layers(setup)
    assert cm.profile_selection.name == expected_name
    assert cm.profile_selection.source == expected_source


# ---------------------------------------------------------------------------
# Tier permutations (axis 2): user | project | both (project shadows)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tier,user_block,project_block,expected_default_mode,expected_prefix",
    [
        # Profile only in user tier
        (
            "user",
            """version = "2.0"
[profiles.shared.general]
default_mode = "thinking"
[profiles.shared]
prompt_prefix = "USER_PREFIX"
""",
            None,
            "thinking",
            "USER_PREFIX",
        ),
        # Profile only in project tier
        (
            "project",
            'version = "2.0"\n',
            """version = "2.0"
[profiles.shared.general]
default_mode = "deep_research"
[profiles.shared]
prompt_prefix = "PROJECT_PREFIX"
""",
            "deep_research",
            "PROJECT_PREFIX",
        ),
        # Same-named profile in both tiers — project wholesale shadows user
        (
            "both",
            """version = "2.0"
[profiles.shared.general]
default_mode = "thinking"
[profiles.shared]
prompt_prefix = "USER_PREFIX"
""",
            """version = "2.0"
[profiles.shared.general]
default_mode = "deep_research"
[profiles.shared]
prompt_prefix = "PROJECT_PREFIX"
""",
            "deep_research",
            "PROJECT_PREFIX",
        ),
    ],
)
def test_tier_axis(
    isolated_thoth_home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tier: str,
    user_block: str,
    project_block: str | None,
    expected_default_mode: str,
    expected_prefix: str,
) -> None:
    from thoth.paths import user_config_file

    monkeypatch.delenv("THOTH_PROFILE", raising=False)
    monkeypatch.chdir(tmp_path)
    _write(user_config_file(), user_block)
    if project_block is not None:
        _write(tmp_path / "thoth.config.toml", project_block)

    cm = ConfigManager()
    cm.load_all_layers({"_profile": "shared"})
    assert cm.profile_selection.name == "shared"
    assert cm.get("general.default_mode") == expected_default_mode
    assert resolve_prompt_prefix(cm, "default") == expected_prefix
    if tier == "both":
        # Project tier wins wholesale
        assert cm.active_profile is not None
        assert cm.active_profile.tier == "project"


# ---------------------------------------------------------------------------
# Prefix-presence × mode axes (3 × 3)
# ---------------------------------------------------------------------------


_HIERARCHY_CONFIG = """version = "2.0"
[general]
prompt_prefix = "GENERAL"

[modes.deep_research]
prompt_prefix = "MODE_DEEP"

[profiles.alpha]
prompt_prefix = "PROFILE_ALPHA"

[profiles.alpha.modes.deep_research]
prompt_prefix = "PROFILE_ALPHA_DEEP"
"""


@pytest.mark.parametrize(
    "active_profile,mode,expected",
    [
        # No active profile → modes.M, then general
        (None, "deep_research", "MODE_DEEP"),
        (None, "thinking", "GENERAL"),
        (None, "default", "GENERAL"),
        # alpha active: profile.modes.M for deep; profile for others
        ("alpha", "deep_research", "PROFILE_ALPHA_DEEP"),
        ("alpha", "thinking", "PROFILE_ALPHA"),
        ("alpha", "default", "PROFILE_ALPHA"),
    ],
)
def test_prefix_hierarchy_per_mode(
    isolated_thoth_home: Path,
    active_profile: str | None,
    mode: str,
    expected: str,
) -> None:
    from thoth.paths import user_config_file

    _write(user_config_file(), _HIERARCHY_CONFIG)
    cm = ConfigManager()
    cli_args: dict[str, object] = {}
    if active_profile:
        cli_args["_profile"] = active_profile
    cm.load_all_layers(cli_args)

    assert resolve_prompt_prefix(cm, mode) == expected


# ---------------------------------------------------------------------------
# Use-case smoke tests — the shipped `init` example profiles, exercised end-to-end.
# ---------------------------------------------------------------------------


_INIT_EXAMPLE_CONFIG = """version = "2.0"
[general]
default_mode = "default"

[profiles.daily.general]
default_mode = "thinking"
default_project = "daily-notes"

[profiles.openai_deep.general]
default_mode = "deep_research"
[profiles.openai_deep.modes.deep_research]
providers = ["openai"]
parallel = false

[profiles.all_deep.general]
default_mode = "deep_research"
[profiles.all_deep.modes.deep_research]
providers = ["openai", "perplexity"]
parallel = true

[profiles.deep_research.general]
default_mode = "deep_research"
prompt_prefix = "Be thorough."
[profiles.deep_research.modes.deep_research]
providers = ["openai", "perplexity"]
parallel = true
prompt_prefix = "Be thorough. Cite primary sources. Include counter-arguments."
"""


@pytest.mark.parametrize(
    "profile,mode,expected_default_mode,expected_assembled",
    [
        (
            "daily",
            "thinking",
            "thinking",
            "topic",  # no prompt_prefix in daily
        ),
        (
            "openai_deep",
            "deep_research",
            "deep_research",
            "topic",  # no prefix in openai_deep
        ),
        (
            "deep_research",
            "deep_research",
            "deep_research",
            "Be thorough. Cite primary sources. Include counter-arguments.\n\ntopic",
        ),
        (
            "deep_research",
            "thinking",
            "deep_research",
            "Be thorough.\n\ntopic",
        ),
    ],
)
def test_shipped_examples_assemble_correctly(
    isolated_thoth_home: Path,
    profile: str,
    mode: str,
    expected_default_mode: str,
    expected_assembled: str,
) -> None:
    from thoth.paths import user_config_file

    _write(user_config_file(), _INIT_EXAMPLE_CONFIG)
    cm = ConfigManager()
    cm.load_all_layers({"_profile": profile})
    assert cm.get("general.default_mode") == expected_default_mode
    assert assemble_prompt_with_prefix(cm, mode, "topic") == expected_assembled


# ---------------------------------------------------------------------------
# Negative cases
# ---------------------------------------------------------------------------


def test_no_profile_active_ignores_profile_levels(isolated_thoth_home: Path) -> None:
    """When no profile is active, prefix from profile-only config returns None."""
    from thoth.paths import user_config_file

    _write(
        user_config_file(),
        """version = "2.0"
[profiles.unused]
prompt_prefix = "UNUSED"
""",
    )
    cm = ConfigManager()
    cm.load_all_layers({})
    assert cm.profile_selection.name is None
    assert resolve_prompt_prefix(cm, "default") is None
    assert assemble_prompt_with_prefix(cm, "default", "x") == "x"
