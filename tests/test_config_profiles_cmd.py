from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from click.testing import CliRunner

from thoth.cli import cli
from thoth.config_cmd import (
    get_config_profile_add_data,
    get_config_profile_current_data,
    get_config_profile_list_data,
    get_config_profile_remove_data,
    get_config_profile_set_data,
    get_config_profile_set_default_data,
    get_config_profile_show_data,
    get_config_profile_unset_data,
    get_config_profile_unset_default_data,
)


def test_profile_add_set_show_unset_remove_round_trip(isolated_thoth_home: Path) -> None:
    add = get_config_profile_add_data("fast", project=False, config_path=None)
    assert add["created"] is True

    set_data = get_config_profile_set_data(
        "fast",
        "general.default_mode",
        "thinking",
        project=False,
        force_string=False,
        config_path=None,
    )
    assert set_data["wrote"] is True

    show = get_config_profile_show_data(
        "fast",
        show_secrets=False,
        config_path=None,
    )
    assert show["profile"]["general"]["default_mode"] == "thinking"

    unset = get_config_profile_unset_data(
        "fast",
        "general.default_mode",
        project=False,
        config_path=None,
    )
    assert unset["removed"] is True

    remove = get_config_profile_remove_data("fast", project=False, config_path=None)
    assert remove["removed"] is True


def test_profile_set_default_and_unset_default_write_general_default_profile(
    isolated_thoth_home: Path,
) -> None:
    get_config_profile_add_data("fast", project=False, config_path=None)
    set_default = get_config_profile_set_default_data("fast", project=False, config_path=None)
    assert set_default["default_profile"] == "fast"

    from thoth.paths import user_config_file

    data = tomllib.loads(user_config_file().read_text())
    assert data["general"]["default_profile"] == "fast"

    unset_default = get_config_profile_unset_default_data(project=False, config_path=None)
    assert unset_default["removed"] is True
    data = tomllib.loads(user_config_file().read_text())
    assert "default_profile" not in data.get("general", {})


def test_profile_project_conflicts_with_config_path(tmp_path: Path) -> None:
    data = get_config_profile_add_data(
        "fast",
        project=True,
        config_path=tmp_path / "custom.toml",
    )
    assert data["error"] == "PROJECT_CONFIG_CONFLICT"


def test_profile_list_reports_active_and_source(isolated_thoth_home: Path) -> None:
    get_config_profile_add_data("fast", project=False, config_path=None)
    get_config_profile_set_default_data("fast", project=False, config_path=None)
    data = get_config_profile_list_data(config_path=None)
    assert data["active_profile"] == "fast"
    assert data["selection_source"] == "config"
    assert [p["name"] for p in data["profiles"]] == ["fast"]


def test_profile_list_show_shadowed_includes_hidden_user_profile(
    isolated_thoth_home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B21: project same-name profile shadows user by default; --show-shadowed reveals it."""
    from thoth.paths import user_config_file

    user_config_file().parent.mkdir(parents=True, exist_ok=True)
    user_config_file().write_text(
        'version = "2.0"\n'
        "[general]\n"
        'default_profile = "prod"\n'
        "[profiles.prod.general]\n"
        'default_mode = "thinking"\n'
    )
    monkeypatch.chdir(tmp_path)
    (tmp_path / "thoth.config.toml").write_text(
        'version = "2.0"\n[profiles.prod.execution]\npoll_interval = 5\n'
    )

    default_data = get_config_profile_list_data(config_path=None, show_shadowed=False)
    assert [(p["name"], p["tier"]) for p in default_data["profiles"]] == [("prod", "project")]
    assert default_data["profiles"][0]["active"] is True
    assert default_data["profiles"][0]["shadowed"] is False

    shadowed_data = get_config_profile_list_data(config_path=None, show_shadowed=True)
    rows = {(p["name"], p["tier"]): p for p in shadowed_data["profiles"]}
    assert rows[("prod", "project")]["active"] is True
    assert rows[("prod", "project")]["shadowed"] is False
    assert rows[("prod", "user")]["active"] is False
    assert rows[("prod", "user")]["shadowed"] is True
    assert rows[("prod", "user")]["shadowed_by"]["tier"] == "project"


def test_profile_set_default_rejects_unknown_profile(isolated_thoth_home: Path) -> None:
    """B16: `set-default NAME` validates against the resolved catalog before persisting."""
    from thoth.errors import ConfigProfileError

    with pytest.raises(ConfigProfileError) as exc:
        get_config_profile_set_default_data("ghost", project=False, config_path=None)
    assert "ghost" in exc.value.message


def test_profile_add_is_idempotent(isolated_thoth_home: Path) -> None:
    """add NAME for an existing profile succeeds with created=False (no-op)."""
    first = get_config_profile_add_data("fast", project=False, config_path=None)
    assert first["created"] is True

    second = get_config_profile_add_data("fast", project=False, config_path=None)
    assert second["created"] is False
    assert second["profile"] == "fast"


def test_profile_remove_is_idempotent(isolated_thoth_home: Path) -> None:
    """remove NAME for a missing profile succeeds with removed=False (no-op)."""
    out = get_config_profile_remove_data("ghost", project=False, config_path=None)
    assert out["removed"] is False
    assert out["profile"] == "ghost"


def test_profile_set_default_accepts_project_only_profile_against_user_config(
    isolated_thoth_home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B16 cross-tier: `set-default prod` when prod lives in project tier writes pointer to user config."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "thoth.config.toml").write_text(
        'version = "2.0"\n[profiles.prod.general]\ndefault_mode = "thinking"\n'
    )

    out = get_config_profile_set_default_data("prod", project=False, config_path=None)
    assert out["default_profile"] == "prod"


def test_profile_set_default_repairs_dangling_default_profile(
    isolated_thoth_home: Path,
) -> None:
    """set-default should replace a broken pointer instead of resolving it first."""
    from thoth.paths import user_config_file

    user_config_file().parent.mkdir(parents=True, exist_ok=True)
    user_config_file().write_text(
        'version = "2.0"\n'
        "[general]\n"
        'default_profile = "ghost"\n'
        "[profiles.fast.general]\n"
        'default_mode = "thinking"\n'
    )

    out = get_config_profile_set_default_data("fast", project=False, config_path=None)

    assert out["default_profile"] == "fast"
    data = tomllib.loads(user_config_file().read_text())
    assert data["general"]["default_profile"] == "fast"


def test_profile_set_default_validates_against_custom_config_path(
    isolated_thoth_home: Path,
    tmp_path: Path,
) -> None:
    """B16: inherited --config PATH participates in set-default validation."""
    import tomllib

    custom_config = tmp_path / "custom.toml"
    custom_config.write_text(
        'version = "2.0"\n[profiles.fast.general]\ndefault_mode = "thinking"\n'
    )

    out = get_config_profile_set_default_data("fast", project=False, config_path=custom_config)
    assert out["default_profile"] == "fast"

    data = tomllib.loads(custom_config.read_text())
    assert data["general"]["default_profile"] == "fast"


def test_profile_remove_clears_matching_default_profile(
    isolated_thoth_home: Path,
) -> None:
    """Removing the default profile from a file should not leave that file dangling."""
    from thoth.paths import user_config_file

    user_config_file().parent.mkdir(parents=True, exist_ok=True)
    user_config_file().write_text(
        'version = "2.0"\n'
        "[general]\n"
        'default_profile = "fast"\n'
        "[profiles.fast.general]\n"
        'default_mode = "thinking"\n'
    )

    out = get_config_profile_remove_data("fast", project=False, config_path=None)

    assert out["removed"] is True
    assert out["unset_default_profile"] is True
    data = tomllib.loads(user_config_file().read_text())
    assert "default_profile" not in data["general"]
    listed = get_config_profile_list_data(config_path=None)
    assert listed["active_profile"] is None
    assert listed["profiles"] == []


def test_profile_unset_default_leaves_empty_general_table_in_place(
    isolated_thoth_home: Path,
) -> None:
    """B17: unset-default removes only general.default_profile; [general] remains."""
    import tomllib

    from thoth.paths import user_config_file

    get_config_profile_add_data("fast", project=False, config_path=None)
    get_config_profile_set_default_data("fast", project=False, config_path=None)
    get_config_profile_unset_default_data(project=False, config_path=None)

    data = tomllib.loads(user_config_file().read_text())
    assert "general" in data
    assert "default_profile" not in data["general"]


def test_profile_current_reports_runtime_active_and_source(
    isolated_thoth_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B12: `config profiles current` shows runtime active selection + source."""
    monkeypatch.delenv("THOTH_PROFILE", raising=False)
    get_config_profile_add_data("fast", project=False, config_path=None)
    get_config_profile_set_default_data("fast", project=False, config_path=None)

    monkeypatch.setenv("THOTH_PROFILE", "fast")
    data = get_config_profile_current_data(config_path=None)
    assert data["active_profile"] == "fast"
    assert data["selection_source"] == "env"


def test_profile_set_unset_preserves_tomlkit_comments(
    isolated_thoth_home: Path,
) -> None:
    """B9: TOML comments around the profile section survive set/unset."""
    from thoth.paths import user_config_file

    user_config_file().parent.mkdir(parents=True, exist_ok=True)
    user_config_file().write_text(
        '# pinned profile\n[profiles.fast.general]\n# default mode\ndefault_mode = "thinking"\n'
    )
    get_config_profile_set_data(
        "fast",
        "general.timeout",
        "30",
        project=False,
        force_string=False,
        config_path=None,
    )
    text = user_config_file().read_text()
    assert "# pinned profile" in text
    assert "# default mode" in text

    get_config_profile_unset_data(
        "fast",
        "general.timeout",
        project=False,
        config_path=None,
    )
    text = user_config_file().read_text()
    assert "# pinned profile" in text
    assert "# default mode" in text


def test_profile_unset_leaves_empty_parent_table_in_place(
    isolated_thoth_home: Path,
) -> None:
    """B17: unset removes only the leaf; empty parent tables remain."""
    import tomllib

    from thoth.paths import user_config_file

    get_config_profile_add_data("fast", project=False, config_path=None)
    get_config_profile_set_data(
        "fast",
        "general.default_mode",
        "thinking",
        project=False,
        force_string=False,
        config_path=None,
    )
    get_config_profile_unset_data(
        "fast",
        "general.default_mode",
        project=False,
        config_path=None,
    )

    data = tomllib.loads(user_config_file().read_text())
    assert "fast" in data["profiles"]
    assert "general" in data["profiles"]["fast"]
    assert "default_mode" not in data["profiles"]["fast"]["general"]


def test_profile_set_unset_handles_deep_four_level_path(
    isolated_thoth_home: Path,
) -> None:
    """B10: depth-4 path `profiles.fast.general.default_mode` set/unset round-trip."""
    import tomllib

    from thoth.paths import user_config_file

    get_config_profile_add_data("fast", project=False, config_path=None)
    set_out = get_config_profile_set_data(
        "fast",
        "general.default_mode",
        "thinking",
        project=False,
        force_string=False,
        config_path=None,
    )
    assert set_out["wrote"] is True

    data = tomllib.loads(user_config_file().read_text())
    assert data["profiles"]["fast"]["general"]["default_mode"] == "thinking"

    unset_out = get_config_profile_unset_data(
        "fast",
        "general.default_mode",
        project=False,
        config_path=None,
    )
    assert unset_out["removed"] is True


def test_dotted_profile_name_round_trips_as_single_profile(
    isolated_thoth_home: Path,
) -> None:
    """Profile names are identity values; only config keys are dotted paths."""
    from thoth.paths import user_config_file

    add_out = get_config_profile_add_data("foo.bar", project=False, config_path=None)
    assert add_out["created"] is True

    set_out = get_config_profile_set_data(
        "foo.bar",
        "general.default_mode",
        "thinking",
        project=False,
        force_string=False,
        config_path=None,
    )
    assert set_out["wrote"] is True

    text = user_config_file().read_text()
    data = tomllib.loads(text)
    assert set(data["profiles"]) == {"foo.bar"}
    assert data["profiles"]["foo.bar"]["general"]["default_mode"] == "thinking"
    assert "[profiles.foo.bar" not in text

    show = get_config_profile_show_data("foo.bar", show_secrets=False, config_path=None)
    assert show["profile"]["general"]["default_mode"] == "thinking"

    result = CliRunner().invoke(
        cli,
        ["--profile", "foo.bar", "config", "get", "general.default_mode"],
    )
    assert result.exit_code == 0, result.output
    assert result.output.strip().splitlines()[-1] == "thinking"

    unset_out = get_config_profile_unset_data(
        "foo.bar",
        "general.default_mode",
        project=False,
        config_path=None,
    )
    assert unset_out["removed"] is True

    data = tomllib.loads(user_config_file().read_text())
    assert data["profiles"]["foo.bar"]["general"] == {}


def test_config_profiles_click_set_and_set_default(isolated_thoth_home: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "profiles", "add", "fast"])
    assert result.exit_code == 0, result.output

    result = runner.invoke(
        cli,
        ["config", "profiles", "set", "fast", "general.default_mode", "thinking"],
    )
    assert result.exit_code == 0, result.output

    result = runner.invoke(cli, ["config", "profiles", "set-default", "fast"])
    assert result.exit_code == 0, result.output

    result = runner.invoke(cli, ["config", "get", "general.default_mode"])
    assert result.exit_code == 0, result.output
    assert result.output.strip().splitlines()[-1] == "thinking"


def test_config_profiles_click_set_accepts_dash_prefixed_number(
    isolated_thoth_home: Path,
) -> None:
    """BUG-003: profile set should parse VALUE like `config set`, including -1."""
    from thoth.paths import user_config_file

    runner = CliRunner()
    assert runner.invoke(cli, ["config", "profiles", "add", "fast"]).exit_code == 0

    result = runner.invoke(
        cli,
        ["config", "profiles", "set", "fast", "execution.poll_interval", "-1"],
    )

    assert result.exit_code == 0, result.output
    data = tomllib.loads(user_config_file().read_text())
    assert data["profiles"]["fast"]["execution"]["poll_interval"] == -1


def test_config_profiles_click_set_accepts_dash_prefixed_string(
    isolated_thoth_home: Path,
) -> None:
    """BUG-003: --string values that look like options should be preserved."""
    from thoth.paths import user_config_file

    runner = CliRunner()
    assert runner.invoke(cli, ["config", "profiles", "add", "fast"]).exit_code == 0

    result = runner.invoke(
        cli,
        ["config", "profiles", "set", "fast", "labels.example", "--string", "--weird"],
    )

    assert result.exit_code == 0, result.output
    data = tomllib.loads(user_config_file().read_text())
    assert data["profiles"]["fast"]["labels"]["example"] == "--weird"


def test_config_profiles_click_set_default_json_repairs_dangling_default(
    isolated_thoth_home: Path,
) -> None:
    from thoth.paths import user_config_file

    user_config_file().parent.mkdir(parents=True, exist_ok=True)
    user_config_file().write_text(
        'version = "2.0"\n'
        "[general]\n"
        'default_profile = "ghost"\n'
        "[profiles.fast.general]\n"
        'default_mode = "thinking"\n'
    )

    result = CliRunner().invoke(
        cli,
        ["config", "profiles", "set-default", "fast", "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = tomllib.loads(user_config_file().read_text())
    assert payload["general"]["default_profile"] == "fast"


def test_config_profiles_click_list_json(isolated_thoth_home: Path) -> None:
    import json

    runner = CliRunner()
    assert runner.invoke(cli, ["config", "profiles", "add", "fast"]).exit_code == 0
    result = runner.invoke(cli, ["config", "profiles", "list", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["data"]["profiles"][0]["name"] == "fast"


def test_config_profiles_click_remove_json_clears_default_then_list_succeeds(
    isolated_thoth_home: Path,
) -> None:
    import json

    runner = CliRunner()
    assert runner.invoke(cli, ["config", "profiles", "add", "fast"]).exit_code == 0
    assert runner.invoke(cli, ["config", "profiles", "set-default", "fast"]).exit_code == 0

    removed = runner.invoke(cli, ["config", "profiles", "remove", "fast", "--json"])
    assert removed.exit_code == 0, removed.output
    removed_payload = json.loads(removed.output)
    assert removed_payload["data"]["unset_default_profile"] is True

    listed = runner.invoke(cli, ["config", "profiles", "list", "--json"])
    assert listed.exit_code == 0, listed.output
    listed_payload = json.loads(listed.output)
    assert listed_payload["data"]["active_profile"] is None
    assert listed_payload["data"]["profiles"] == []


def test_config_profiles_click_list_show_shadowed_json(
    isolated_thoth_home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B21: list --show-shadowed is wired through Click and JSON."""
    import json

    from thoth.paths import user_config_file

    user_config_file().parent.mkdir(parents=True, exist_ok=True)
    user_config_file().write_text(
        'version = "2.0"\n[profiles.prod.general]\ndefault_mode = "thinking"\n'
    )
    monkeypatch.chdir(tmp_path)
    (tmp_path / "thoth.config.toml").write_text(
        'version = "2.0"\n[profiles.prod.execution]\npoll_interval = 5\n'
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "profiles", "list", "--show-shadowed", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    rows = {(p["name"], p["tier"]): p for p in payload["data"]["profiles"]}
    assert rows[("prod", "project")]["shadowed"] is False
    assert rows[("prod", "user")]["shadowed"] is True
    assert rows[("prod", "user")]["shadowed_by"]["tier"] == "project"


def test_config_profiles_mutators_reject_root_profile_flag(
    isolated_thoth_home: Path,
) -> None:
    """B7: --profile is not honored by mutator leaves."""
    runner = CliRunner()
    for op_args in (
        ["config", "profiles", "add", "bar"],
        ["config", "profiles", "set", "bar", "general.default_mode", "thinking"],
        ["config", "profiles", "set-default", "bar"],
        ["config", "profiles", "unset-default"],
        ["config", "profiles", "unset", "bar", "general.default_mode"],
        ["config", "profiles", "remove", "bar"],
    ):
        result = runner.invoke(cli, ["--profile", "foo", *op_args])
        assert result.exit_code != 0, f"{op_args} should reject --profile"
        assert "--profile" in result.output


def test_config_profiles_state_readers_honor_root_profile_flag(
    isolated_thoth_home: Path,
) -> None:
    """B7: --profile is honored by active-state readers."""
    runner = CliRunner()
    assert runner.invoke(cli, ["config", "profiles", "add", "fast"]).exit_code == 0
    for op_args in (
        ["config", "profiles", "list"],
        ["config", "profiles", "current"],
    ):
        result = runner.invoke(cli, ["--profile", "fast", *op_args])
        assert result.exit_code == 0, f"{op_args} should accept --profile: {result.output}"


def test_config_profiles_show_rejects_root_profile_flag(
    isolated_thoth_home: Path,
) -> None:
    """show NAME is a raw profile lookup; root --profile is a conflicting selector."""
    runner = CliRunner()
    assert runner.invoke(cli, ["config", "profiles", "add", "fast"]).exit_code == 0

    result = runner.invoke(cli, ["--profile", "fast", "config", "profiles", "show", "fast"])

    assert result.exit_code != 0
    assert "--profile" in result.output


def test_config_profiles_current_reports_flag_source(
    isolated_thoth_home: Path,
) -> None:
    """B12: profiles current reports the runtime source as 'flag' under --profile."""
    import json

    runner = CliRunner()
    assert runner.invoke(cli, ["config", "profiles", "add", "fast"]).exit_code == 0
    result = runner.invoke(cli, ["--profile", "fast", "config", "profiles", "current", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["data"]["active_profile"] == "fast"
    assert payload["data"]["selection_source"] == "flag"


@pytest.mark.parametrize(
    "op_args",
    (
        ["config", "profiles", "list"],
        ["config", "profiles", "current"],
    ),
)
def test_config_profiles_state_readers_non_json_profile_errors_are_human(
    isolated_thoth_home: Path,
    op_args: list[str],
) -> None:
    """BUG-002: non-JSON profile reader failures should not emit JSON envelopes."""
    result = CliRunner().invoke(cli, ["--profile", "missing", *op_args])

    assert result.exit_code == 1
    assert not result.output.lstrip().startswith("{")
    assert "Error: Profile 'missing' not found (from --profile flag)" in result.output
    assert "Suggestion: Run `thoth config profiles list`" in result.output


@pytest.mark.parametrize(
    "op_args",
    (
        ["config", "profiles", "list"],
        ["config", "profiles", "current"],
        ["config", "profiles", "show", "fast"],
    ),
)
def test_config_profiles_readers_non_json_config_errors_are_human(
    isolated_thoth_home: Path,
    tmp_path: Path,
    op_args: list[str],
) -> None:
    """BUG-002: reader ThothError handling is JSON-only when --json is present."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("thoth.config.toml").write_text('version = "2.0"\n')
        Path(".thoth.config.toml").write_text('version = "2.0"\n')

        result = runner.invoke(cli, op_args)

    assert result.exit_code == 1
    assert not result.output.lstrip().startswith("{")
    assert "Error: Two Thoth config files found in the project root:" in result.output
    assert "thoth.config.toml" in result.output
    assert ".thoth.config.toml" in result.output


@pytest.mark.parametrize(
    "op_args",
    (
        ["config", "profiles", "list", "--json"],
        ["config", "profiles", "current", "--json"],
        ["config", "profiles", "show", "fast", "--json"],
    ),
)
def test_config_profiles_readers_json_config_errors_remain_enveloped(
    isolated_thoth_home: Path,
    tmp_path: Path,
    op_args: list[str],
) -> None:
    """BUG-002: JSON profile reader failures keep the error envelope contract."""
    import json

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("thoth.config.toml").write_text('version = "2.0"\n')
        Path(".thoth.config.toml").write_text('version = "2.0"\n')

        result = runner.invoke(cli, op_args)

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "CONFIG_AMBIGUOUS"
    assert "Two Thoth config files found" in payload["error"]["message"]


def test_runtime_selection_does_not_mutate_persisted_pointer(
    isolated_thoth_home: Path,
) -> None:
    """B20 end-to-end: --profile/THOTH_PROFILE are read-only; persisted default_profile is unchanged.

    With persisted general.default_profile = "fast", running with --profile bar:
      - `config get general.default_profile` returns "fast" (the persisted file value).
      - `config profiles current` returns "bar" with source "flag".
    Only `config profiles set-default NAME` / `unset-default` mutate the persisted pointer.
    """
    import json

    runner = CliRunner()
    assert runner.invoke(cli, ["config", "profiles", "add", "fast"]).exit_code == 0
    assert runner.invoke(cli, ["config", "profiles", "add", "bar"]).exit_code == 0
    assert runner.invoke(cli, ["config", "profiles", "set-default", "fast"]).exit_code == 0

    # Persisted pointer is "fast"; runtime selection is "bar".
    get_result = runner.invoke(
        cli, ["--profile", "bar", "config", "get", "general.default_profile"]
    )
    assert get_result.exit_code == 0, get_result.output
    assert get_result.output.strip().splitlines()[-1] == "fast"

    current_result = runner.invoke(
        cli, ["--profile", "bar", "config", "profiles", "current", "--json"]
    )
    assert current_result.exit_code == 0, current_result.output
    payload = json.loads(current_result.output)
    assert payload["data"]["active_profile"] == "bar"
    assert payload["data"]["selection_source"] == "flag"

    # Confirm the file is unchanged: re-read without any flag.
    get_after = runner.invoke(cli, ["config", "get", "general.default_profile"])
    assert get_after.output.strip().splitlines()[-1] == "fast"


def test_config_profiles_appears_in_config_help(isolated_thoth_home: Path) -> None:
    result = CliRunner().invoke(cli, ["config", "--help"])
    assert result.exit_code == 0
    assert "profiles" in result.output
