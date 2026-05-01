"""Tests for thoth modes mutation commands (P12)."""

from __future__ import annotations


def test_parse_target_flags_defaults() -> None:
    from thoth.modes_cmd import _parse_target_flags

    flags, remaining, rc = _parse_target_flags([])
    assert rc == 0
    assert flags.project is False
    assert flags.config_path is None
    assert flags.profile is None
    assert flags.from_profile is None
    assert flags.force_string is False
    assert flags.override is False
    assert remaining == []


def test_parse_target_flags_project_success() -> None:
    from thoth.modes_cmd import _parse_target_flags

    flags, remaining, rc = _parse_target_flags(
        [
            "alpha",
            "--project",
            "--profile",
            "dev",
            "--from-profile",
            "ci",
            "--string",
            "--override",
            "beta",
            "--model",
            "gpt-4o-mini",
        ]
    )
    assert rc == 0
    assert flags.project is True
    assert flags.config_path is None
    assert flags.profile == "dev"
    assert flags.from_profile == "ci"
    assert flags.force_string is True
    assert flags.override is True
    assert remaining == ["alpha", "beta", "--model", "gpt-4o-mini"]


def test_parse_target_flags_config_success() -> None:
    from thoth.modes_cmd import _parse_target_flags

    flags, remaining, rc = _parse_target_flags(["alpha", "--config", "/tmp/x.toml", "beta"])
    assert rc == 0
    assert flags.project is False
    assert flags.config_path == "/tmp/x.toml"
    assert remaining == ["alpha", "beta"]


def test_parse_target_flags_project_config_conflict() -> None:
    from thoth.modes_cmd import _parse_target_flags

    flags, remaining, rc = _parse_target_flags(["--project", "--config", "/tmp/x.toml"])
    assert rc == 2
    # rc=2 signals USAGE_ERROR; the caller is responsible for the error
    # message (the Click wrapper emits structured JSON errors when needed).


def test_parse_target_flags_override_without_profile_allowed() -> None:
    from thoth.modes_cmd import _parse_target_flags

    flags, remaining, rc = _parse_target_flags(["--override"])
    assert rc == 0
    assert flags.override is True
    assert flags.profile is None
    # Operation-specific parsers decide whether --override is accepted.
    # P12 accepts it for add/copy and rejects it for set/unset/remove/rename.
