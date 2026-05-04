"""Regression coverage for inherited root-option policy.

These tests guard against root options being accepted before a subcommand and
then silently ignored by that subcommand.
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from thoth.cli import cli


def _stub_run_research(monkeypatch):
    captured: dict[str, object] = {}

    def fake(**kwargs):
        captured.update(kwargs)
        return None

    monkeypatch.setattr("thoth.run.run_research", fake)
    return captured


def test_ask_honors_inherited_prompt_flag(monkeypatch):
    captured = _stub_run_research(monkeypatch)

    result = CliRunner().invoke(cli, ["--prompt", "from root", "ask"])

    assert result.exit_code == 0, result.output
    assert captured["prompt"] == "from root"


def test_resume_rejects_inherited_research_only_prompt(monkeypatch):
    captured: dict[str, object] = {}

    async def fake_resume(*args, **kwargs):
        captured["called"] = True

    monkeypatch.setattr("thoth.run.resume_operation", fake_resume)

    result = CliRunner().invoke(cli, ["--prompt", "ignored", "resume", "op_x"])

    assert result.exit_code == 2
    assert "--prompt" in result.output
    assert "resume" in result.output
    assert "called" not in captured


def test_admin_read_only_rejects_inherited_quiet():
    result = CliRunner().invoke(cli, ["--quiet", "providers", "list"])

    assert result.exit_code == 2
    assert "--quiet" in result.output
    assert "providers list" in result.output


def test_providers_list_honors_inherited_provider(monkeypatch):
    captured: dict[str, object] = {}

    async def fake_providers_command(**kwargs):
        captured.update(kwargs)
        return 0

    monkeypatch.setattr("thoth.commands.providers_command", fake_providers_command)

    result = CliRunner().invoke(cli, ["--provider", "mock", "providers", "list"])

    assert result.exit_code == 0, result.output
    assert captured["filter_provider"] == "mock"


def test_providers_models_honors_inherited_api_key_and_timeout(monkeypatch):
    captured: dict[str, object] = {}

    async def fake_providers_command(**kwargs):
        captured.update(kwargs)
        return 0

    monkeypatch.setattr("thoth.commands.providers_command", fake_providers_command)

    result = CliRunner().invoke(
        cli,
        [
            "--provider",
            "openai",
            "--api-key-openai",
            "sk-root",
            "--timeout",
            "12.5",
            "providers",
            "models",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["filter_provider"] == "openai"
    assert captured["cli_api_keys"] == {
        "openai": "sk-root",
        "perplexity": None,
        "gemini": None,
        "mock": None,
    }
    assert captured["timeout_override"] == 12.5


def test_providers_check_filters_and_validates_inherited_mock_key(isolated_thoth_home: Path):
    result = CliRunner().invoke(
        cli,
        ["--provider", "mock", "--api-key-mock", "mock-root", "providers", "check"],
    )

    assert result.exit_code == 0, result.output
    assert "mock" in result.output.lower()
    assert "openai" not in result.output.lower()
    assert "set" in result.output.lower()


def test_providers_check_returns_2_for_missing_filtered_key(isolated_thoth_home: Path):
    result = CliRunner().invoke(cli, ["--provider", "mock", "providers", "check"])

    assert result.exit_code == 2
    assert "mock" in result.output.lower()
    assert "missing" in result.output.lower()


def test_config_get_honors_inherited_config_path(tmp_path: Path):
    cfg = tmp_path / "custom.toml"
    cfg.write_text('version = "2.0"\n[general]\ndefault_mode = "custom_mode"\n')

    result = CliRunner().invoke(
        cli,
        ["--config", str(cfg), "config", "get", "general.default_mode"],
    )

    assert result.exit_code == 0, result.output
    assert result.output.strip() == "custom_mode"


def test_config_project_target_rejects_inherited_config_path(tmp_path: Path):
    cfg = tmp_path / "custom.toml"
    cfg.write_text('version = "2.0"\n')

    result = CliRunner().invoke(cli, ["--config", str(cfg), "config", "path", "--project"])

    assert result.exit_code == 2
    assert "--config" in result.output
    assert "--project" in result.output


def test_config_path_rejects_unknown_passthrough_arg():
    result = CliRunner().invoke(cli, ["config", "path", "--bogus"])

    assert result.exit_code == 2
    assert "--bogus" in result.output


def test_config_help_rejects_inherited_config_path(tmp_path: Path):
    cfg = tmp_path / "custom.toml"
    cfg.write_text('version = "2.0"\n')

    result = CliRunner().invoke(cli, ["--config", str(cfg), "config", "help"])

    assert result.exit_code == 2
    assert "--config" in result.output
    assert "config help" in result.output


def test_modes_list_honors_inherited_config_path(tmp_path: Path):
    cfg = tmp_path / "custom.toml"
    cfg.write_text(
        'version = "2.0"\n[modes.custom_quick]\nprovider = "mock"\nmodel = "mock-model-v1"\n'
    )

    result = CliRunner().invoke(cli, ["--config", str(cfg), "modes", "list", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    # P16 PR3 T12: payload now uses canonical envelope shape
    # ({"status": "ok", "data": {schema_version, modes}}).
    assert any(mode["name"] == "custom_quick" for mode in payload["data"]["modes"])


def test_help_rejects_inherited_config_path(tmp_path: Path):
    cfg = tmp_path / "custom.toml"
    cfg.write_text('version = "2.0"\n')

    result = CliRunner().invoke(cli, ["--config", str(cfg), "help"])

    assert result.exit_code == 2
    assert "--config" in result.output
    assert "help" in result.output


def test_bare_admin_groups_reject_inherited_config_path(tmp_path: Path):
    cfg = tmp_path / "custom.toml"
    cfg.write_text('version = "2.0"\n')

    for command in ("config", "modes", "providers"):
        result = CliRunner().invoke(cli, ["--config", str(cfg), command])
        assert result.exit_code == 2
        assert "--config" in result.output
        assert command in result.output


# ---------------------------------------------------------------------------
# P23-TS01 — failing CLI tests for the new `--model` flag.
# `--model X` does not yet exist; these tests pin its expected wiring:
# threads through to run_research's `model_override` kwarg without local
# compatibility validation, and is mutually exclusive with `--pick-model`.
# ---------------------------------------------------------------------------


def test_ask_threads_model_flag_into_run_research(monkeypatch):
    """P23-TS01: `--model X` populates run_research's model_override kwarg."""
    captured = _stub_run_research(monkeypatch)

    result = CliRunner().invoke(
        cli,
        [
            "--prompt",
            "test prompt",
            "ask",
            "--provider",
            "perplexity",
            "--model",
            "sonar-pro",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["model_override"] == "sonar-pro"
    assert captured["provider"] == "perplexity"


def test_ask_model_flag_passes_arbitrary_string_without_validation(monkeypatch):
    """P23-TS01: --model accepts any string; validation is delegated to provider/API."""
    captured = _stub_run_research(monkeypatch)

    result = CliRunner().invoke(
        cli,
        [
            "--prompt",
            "test prompt",
            "ask",
            "--provider",
            "perplexity",
            "--model",
            "future-sonar-2027-preview",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["model_override"] == "future-sonar-2027-preview"


def test_ask_model_and_pick_model_are_mutually_exclusive():
    """P23-TS01 (design choice C): --model and --pick-model conflict → UsageError.

    Asserts on the literal phrase "mutually exclusive" so the test stays red
    after T01 adds the --model flag, until T01 also wires the explicit
    mutual-exclusion rule. Without this phrase check, the test would pass
    by accident on Click's "no such option" path (also exit code 2).
    """
    result = CliRunner().invoke(
        cli,
        [
            "--prompt",
            "test prompt",
            "ask",
            "--provider",
            "perplexity",
            "--model",
            "sonar",
            "--pick-model",
        ],
    )

    assert result.exit_code == 2, result.output
    assert "mutually exclusive" in result.output.lower()
    assert "--model" in result.output
    assert "--pick-model" in result.output


def test_ask_honors_inherited_model_flag(monkeypatch):
    """P23-RS02: root --model is honored by research subcommands."""
    captured = _stub_run_research(monkeypatch)

    result = CliRunner().invoke(
        cli,
        [
            "--model",
            "sonar",
            "--prompt",
            "test prompt",
            "ask",
            "--provider",
            "perplexity",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["model_override"] == "sonar"
    assert captured["provider"] == "perplexity"


def test_admin_command_rejects_inherited_model_flag(monkeypatch):
    """P23-RS02: root --model is rejected by non-research subcommands."""
    captured: dict[str, object] = {}

    async def fake_providers_command(**kwargs):
        captured.update(kwargs)
        return 0

    monkeypatch.setattr("thoth.commands.providers_command", fake_providers_command)

    result = CliRunner().invoke(cli, ["--model", "sonar", "providers", "list"])

    assert result.exit_code == 2
    assert "--model" in result.output
    assert "providers list" in result.output
    assert captured == {}


def test_bare_prompt_trailing_model_and_pick_model_are_mutually_exclusive(monkeypatch):
    """P23-RS03: fallback parser rejects trailing --model plus --pick-model."""
    captured = _stub_run_research(monkeypatch)
    pick_called = False

    def fake_pick_model_override(mode, config):
        nonlocal pick_called
        pick_called = True
        return "picked-model"

    monkeypatch.setattr("thoth.cli._pick_model_override", fake_pick_model_override)

    result = CliRunner().invoke(cli, ["test prompt", "--model", "sonar", "--pick-model"])

    assert result.exit_code == 2
    assert "mutually exclusive" in result.output.lower()
    assert "--model" in result.output
    assert "--pick-model" in result.output
    assert pick_called is False
    assert captured == {}


def test_bare_prompt_trailing_pick_model_and_model_are_mutually_exclusive(monkeypatch):
    """P23-RS03: fallback parser rejects either trailing option order."""
    captured = _stub_run_research(monkeypatch)
    pick_called = False

    def fake_pick_model_override(mode, config):
        nonlocal pick_called
        pick_called = True
        return "picked-model"

    monkeypatch.setattr("thoth.cli._pick_model_override", fake_pick_model_override)

    result = CliRunner().invoke(cli, ["test prompt", "--pick-model", "--model", "sonar"])

    assert result.exit_code == 2
    assert "mutually exclusive" in result.output.lower()
    assert "--model" in result.output
    assert "--pick-model" in result.output
    assert pick_called is False
    assert captured == {}


# ---------------------------------------------------------------------------
# P24 Task 5.1 — --api-key-gemini surface tests.
# Mirrors --api-key-perplexity precedent.
# ---------------------------------------------------------------------------


def test_root_option_labels_includes_api_key_gemini() -> None:
    """P24-T07: ROOT_OPTION_LABELS maps api_key_gemini to --api-key-gemini."""
    from thoth.cli_subcommands._option_policy import ROOT_OPTION_LABELS

    assert ROOT_OPTION_LABELS.get("api_key_gemini") == "--api-key-gemini"


def test_inherited_api_keys_includes_gemini() -> None:
    """P24-T07: inherited_api_keys() returns a 'gemini' entry."""
    from unittest.mock import MagicMock

    from thoth.cli_subcommands._option_policy import inherited_api_keys

    fake_ctx = MagicMock()
    fake_ctx.obj = {
        "api_key_openai": None,
        "api_key_perplexity": None,
        "api_key_gemini": "AIza-root",
        "api_key_mock": None,
    }

    keys = inherited_api_keys(fake_ctx)
    assert "gemini" in keys
    assert keys["gemini"] == "AIza-root"


def test_ask_threads_inherited_api_key_gemini_into_run_research(monkeypatch):
    """P24-T07: --api-key-gemini at root is threaded into run_research's cli_api_keys."""
    captured = _stub_run_research(monkeypatch)

    result = CliRunner().invoke(
        cli,
        [
            "--api-key-gemini",
            "AIza-root",
            "--prompt",
            "test prompt",
            "ask",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["cli_api_keys"]["gemini"] == "AIza-root"


def test_ask_subcommand_local_api_key_gemini(monkeypatch):
    """P24-T07: --api-key-gemini after `ask` is honored too (subcommand-local)."""
    captured = _stub_run_research(monkeypatch)

    result = CliRunner().invoke(
        cli,
        [
            "--prompt",
            "test prompt",
            "ask",
            "--api-key-gemini",
            "AIza-local",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["cli_api_keys"]["gemini"] == "AIza-local"
