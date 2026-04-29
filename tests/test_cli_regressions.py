"""Regression tests for P16 Click dispatch bugs."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from thoth.cli import cli


def _mock_stream(prompt: str, mode: str = "default") -> str:
    return f"# Mock streaming response (mode={mode})\n\nEcho: {prompt}\n\nDone."


def _stub_run_research(monkeypatch):
    captured = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return 0

    monkeypatch.setattr("thoth.run.run_research", fake_run)
    return captured


def test_bug_cli_001_research_fallback_forwards_global_options(
    tmp_path: Path,
    monkeypatch,
) -> None:
    captured = _stub_run_research(monkeypatch)
    monkeypatch.setattr("thoth.config._config_path", None)
    cfg = tmp_path / "thoth.config.toml"
    cfg.write_text('version = "2.0"\n')

    result = CliRunner().invoke(
        cli,
        [
            "--config",
            str(cfg),
            "--provider",
            "mock",
            "--project",
            "regression",
            "--async",
            "default",
            "hello",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["mode"] == "default"
    assert captured["prompt"] == "hello"
    assert captured["provider"] == "mock"
    assert captured["project"] == "regression"
    assert captured["async_mode"] is True


def test_bare_prompt_forwards_leading_out_and_append(monkeypatch, tmp_path: Path) -> None:
    captured = _stub_run_research(monkeypatch)
    target = tmp_path / "answer.md"

    result = CliRunner().invoke(
        cli,
        ["--out", str(target), "--append", "--provider", "mock", "topic"],
    )

    assert result.exit_code == 0, result.output
    assert captured["prompt"] == "topic"
    assert captured["provider"] == "mock"
    assert captured["out_specs"] == (str(target),)
    assert captured["append"] is True


def test_bare_prompt_forwards_trailing_out_and_append(monkeypatch, tmp_path: Path) -> None:
    captured = _stub_run_research(monkeypatch)
    target = tmp_path / "answer.md"

    result = CliRunner().invoke(
        cli,
        ["topic", "--provider", "mock", "--out", str(target), "--append"],
    )

    assert result.exit_code == 0, result.output
    assert captured["prompt"] == "topic"
    assert captured["provider"] == "mock"
    assert captured["out_specs"] == (str(target),)
    assert captured["append"] is True


def test_bare_prompt_leading_out_writes_stream_file(
    isolated_thoth_home: Path, monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("MOCK_API_KEY", "test")
    target = tmp_path / "leading.md"

    result = CliRunner().invoke(
        cli,
        ["--out", str(target), "--provider", "mock", "leading prompt"],
    )

    assert result.exit_code == 0, result.output
    assert result.output == ""
    assert target.read_text() == _mock_stream("leading prompt")


def test_bare_prompt_trailing_out_writes_stream_file(
    isolated_thoth_home: Path, monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("MOCK_API_KEY", "test")
    target = tmp_path / "trailing.md"

    result = CliRunner().invoke(
        cli,
        ["trailing prompt", "--provider", "mock", "--out", str(target)],
    )

    assert result.exit_code == 0, result.output
    assert result.output == ""
    assert target.read_text() == _mock_stream("trailing prompt")


def test_background_forwards_openai_cli_api_key(monkeypatch) -> None:
    captured = _stub_run_research(monkeypatch)

    result = CliRunner().invoke(
        cli,
        [
            "deep_research",
            "openai key",
            "--provider",
            "openai",
            "--api-key-openai",
            "sk-test",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["provider"] == "openai"
    assert captured["cli_api_keys"] == {
        "openai": "sk-test",
        "perplexity": None,
        "mock": None,
    }


def test_background_forwards_perplexity_cli_api_key(monkeypatch) -> None:
    captured = _stub_run_research(monkeypatch)

    result = CliRunner().invoke(
        cli,
        [
            "deep_research",
            "perplexity key",
            "--provider",
            "perplexity",
            "--api-key-perplexity",
            "pplx-test",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["provider"] == "perplexity"
    assert captured["cli_api_keys"] == {
        "openai": None,
        "perplexity": "pplx-test",
        "mock": None,
    }


def test_bug_cli_002_option_only_prompt_runs_research(monkeypatch) -> None:
    captured = _stub_run_research(monkeypatch)

    result = CliRunner().invoke(cli, ["-m", "thinking", "-q", "option prompt"])

    assert result.exit_code == 0, result.output
    assert captured["mode"] == "thinking"
    assert captured["prompt"] == "option prompt"


def test_bug_cli_002_resume_option_invokes_resume(monkeypatch) -> None:
    captured = {}

    def fake_resume(operation_id, verbose=False, ctx=None, **kwargs):
        captured["operation_id"] = operation_id
        captured["verbose"] = verbose
        captured["ctx"] = ctx
        return 0

    monkeypatch.setattr("thoth.run.resume_operation", fake_resume)

    result = CliRunner().invoke(cli, ["resume", "op_regression"])

    assert result.exit_code == 0, result.output
    assert captured["operation_id"] == "op_regression"
    assert captured["verbose"] is False


def test_bug_cli_003_prompt_file_is_read_before_research(
    tmp_path: Path,
    monkeypatch,
) -> None:
    captured = _stub_run_research(monkeypatch)
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("prompt from file")

    result = CliRunner().invoke(cli, ["--prompt-file", str(prompt_file), "default"])

    assert result.exit_code == 0, result.output
    assert captured["mode"] == "default"
    assert captured["prompt"] == "prompt from file"


def test_bug_cli_004_config_passthrough_flags_and_help(
    isolated_thoth_home: Path,
) -> None:
    get_result = CliRunner().invoke(cli, ["config", "get", "general.default_mode", "--raw"])
    assert get_result.exit_code == 0, get_result.output
    assert get_result.output.strip() == "default"

    help_result = CliRunner().invoke(cli, ["config", "help"])
    assert help_result.exit_code == 0, help_result.output
    assert "thoth config" in help_result.output


def test_bug_cli_006_modes_list_leaf_matches_default(
    isolated_thoth_home: Path,
) -> None:
    result = CliRunner().invoke(cli, ["modes", "list", "--json"])

    assert result.exit_code == 0, result.output
    assert '"schema_version": "1"' in result.output


def test_bug_01_auth_help_interception_is_root_only() -> None:
    result = CliRunner().invoke(cli, ["init", "--help", "auth"])

    assert result.exit_code == 0, result.output
    assert "Authentication" not in result.output
    assert "Initialize thoth configuration" in result.output


def test_bug_04_show_general_help_dead_export_removed() -> None:
    import thoth.__main__ as thoth_main
    import thoth.help as thoth_help

    assert not hasattr(thoth_help, "show_general_help")
    assert not hasattr(thoth_main, "show_general_help")


def test_bug_05_version_after_prompt_is_prompt_text(monkeypatch) -> None:
    captured = _stub_run_research(monkeypatch)

    result = CliRunner().invoke(cli, ["foo", "--version"])

    assert result.exit_code == 0, result.output
    assert "Thoth v" not in result.output
    assert captured["mode"] == "default"
    assert captured["prompt"] == "foo --version"


def test_bug_08_extract_fallback_options_is_parse_only(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import thoth.config as thoth_config
    from thoth.cli import _extract_fallback_options

    cfg = tmp_path / "thoth.config.toml"
    monkeypatch.setattr(thoth_config, "_config_path", None)

    positional, parsed = _extract_fallback_options(["foo", "--config", str(cfg)], {})

    assert positional == ["foo"]
    assert parsed["config_path"] == str(cfg)
    assert thoth_config._config_path is None


def test_bug_10_version_must_be_used_alone() -> None:
    result = CliRunner().invoke(cli, ["--version", "--async"])

    assert result.exit_code != 0
    assert "--version must be used alone" in result.output


def test_bug_10_version_help_documents_alone() -> None:
    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0, result.output
    assert "--version" in result.output
    assert "must be used alone" in result.output


def test_bug_11_providers_list_supports_provider_filter(
    isolated_thoth_home: Path,
) -> None:
    result = CliRunner().invoke(cli, ["providers", "list", "--provider", "openai"])

    assert result.exit_code == 0, result.output
    assert "openai" in result.output.lower()
    assert "perplexity" not in result.output.lower()


def test_root_no_args_shows_help() -> None:
    result = CliRunner().invoke(cli, [])

    assert result.exit_code == 0, result.output
    assert "Usage:" in result.output
    assert "Run research:" in result.output
    assert "Manage thoth:" in result.output


def test_command_error_shows_command_help_before_error() -> None:
    result = CliRunner().invoke(cli, ["modes", "--kind", "immediate"])

    assert result.exit_code == 2
    assert "Usage:" in result.output
    assert "List research modes with provider/model/kind." in result.output
    assert "Commands:" in result.output
    assert "list" in result.output
    assert "Error: No such command '--kind'." in result.output
    assert result.output.index("Usage:") < result.output.index("Error:")


def test_leaf_command_error_shows_leaf_help_before_error() -> None:
    result = CliRunner().invoke(cli, ["modes", "list", "--kind", "fast"])

    assert result.exit_code == 2
    assert "Usage:" in result.output
    assert "List research modes." in result.output
    assert "--kind [immediate|background]" in result.output
    assert "Error: Invalid value for '--kind'" in result.output
    assert result.output.index("Usage:") < result.output.index("Error:")
