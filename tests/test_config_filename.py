"""P21c: failing test scenario matrix for canonical config filename.

This file is written in the RED phase of TDD. The symbols it imports
(`detect_legacy_paths`, `ConfigAmbiguousError`, `ConfigNotFoundError`,
`_format_config_not_found`) do not yet exist; the renamed `user_config_file()`
still returns the legacy path; and `doxa init` lacks `--user`/`--hidden`/
`--force` flags. All tests in this file are expected to fail at import time
or at assertion time until Tasks 2-4 of P21c land.

Coverage:
- A1-A5  user-tier loading
- B1-B8  project-tier loading
- C1-C3  legacy detection helper contract
- D1-D14 `doxa init` flag combinations
- E1-E3  source-tree string-sweep regression guards
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from doxa_research.cli import cli
from doxa_research.cli_subcommands.init import init as init_cmd
from doxa_research.config import (
    ConfigManager,
    _format_config_not_found,
    detect_legacy_paths,
)
from doxa_research.errors import (
    ConfigAmbiguousError,
    ConfigNotFoundError,
)
from doxa_research.paths import user_config_dir, user_config_file

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
TESTS_DIR = REPO_ROOT / "tests"
THIS_FILE = Path(__file__).resolve()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_xdg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate XDG_CONFIG_HOME and CWD into tmp_path/{xdg, project}."""
    xdg = tmp_path / "xdg"
    project = tmp_path / "project"
    xdg.mkdir()
    project.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    monkeypatch.chdir(project)
    return tmp_path


def _xdg_doxa_dir(isolated_xdg_root: Path) -> Path:
    """`$XDG_CONFIG_HOME/doxa_research/` for the test."""
    d = isolated_xdg_root / "xdg" / "doxa"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _project_dir(isolated_xdg_root: Path) -> Path:
    return isolated_xdg_root / "project"


_MIN_CONFIG_TOML = 'version = "2.0"\n'


# ---------------------------------------------------------------------------
# A. User-tier loading
# ---------------------------------------------------------------------------


def test_a1_user_canonical_loads(isolated_xdg: Path) -> None:
    """A1: canonical user file at $XDG_CONFIG_HOME/doxa_research/doxa.config.toml loads."""
    user_dir = _xdg_doxa_dir(isolated_xdg)
    canonical = user_dir / "doxa.config.toml"
    canonical.write_text(_MIN_CONFIG_TOML + '[general]\ndefault_mode = "thinking"\n')

    cm = ConfigManager()
    cm.load_all_layers({})

    assert cm.user_config_path == canonical
    assert cm.get("general.default_mode") == "thinking"


def test_a2_only_legacy_user_file_treated_as_missing(isolated_xdg: Path) -> None:
    """A2: legacy `config.toml` is not loaded; user_config_path points at canonical."""
    user_dir = _xdg_doxa_dir(isolated_xdg)
    legacy = user_dir / "config.toml"
    legacy.write_text(_MIN_CONFIG_TOML + '[general]\ndefault_mode = "thinking"\n')

    cm = ConfigManager()
    cm.load_all_layers({})

    canonical = user_dir / "doxa.config.toml"
    assert cm.user_config_path == canonical
    assert not canonical.exists()
    # Legacy must not have been loaded — value should fall back to default.
    assert cm.get("general.default_mode") == "default"


def test_a3_canonical_wins_silently_over_legacy(isolated_xdg: Path) -> None:
    """A3: both canonical and legacy user files exist — canonical loads, legacy ignored."""
    user_dir = _xdg_doxa_dir(isolated_xdg)
    canonical = user_dir / "doxa.config.toml"
    canonical.write_text(_MIN_CONFIG_TOML + '[general]\ndefault_mode = "thinking"\n')
    legacy = user_dir / "config.toml"
    legacy.write_text(_MIN_CONFIG_TOML + '[general]\ndefault_mode = "exploration"\n')

    cm = ConfigManager()
    cm.load_all_layers({})

    assert cm.user_config_path == canonical
    assert cm.get("general.default_mode") == "thinking"


def test_a4_no_config_anywhere_formatter_lists_canonical_paths(
    isolated_xdg: Path,
) -> None:
    """A4: ConfigNotFoundError formatter lists all three canonical paths."""
    err = _format_config_not_found()
    assert isinstance(err, ConfigNotFoundError)
    msg = str(err)
    assert str(user_config_file()) in msg
    assert "./doxa.config.toml" in msg
    assert "./.doxa.config.toml" in msg


def test_a5_legacy_user_present_message_names_legacy_and_rename_target(
    isolated_xdg: Path,
) -> None:
    """A5: legacy `config.toml` on disk → message names it and the rename target."""
    user_dir = _xdg_doxa_dir(isolated_xdg)
    legacy = user_dir / "config.toml"
    legacy.write_text(_MIN_CONFIG_TOML)

    err = _format_config_not_found()
    msg = str(err)
    assert str(legacy) in msg
    # Rename guidance should mention the canonical filename target.
    assert "doxa.config.toml" in msg


# ---------------------------------------------------------------------------
# B. Project-tier loading
# ---------------------------------------------------------------------------


def test_b1_only_visible_project_file_loads(isolated_xdg: Path) -> None:
    """B1: only `./doxa.config.toml` exists → loads it."""
    project = _project_dir(isolated_xdg)
    canonical = project / "doxa.config.toml"
    canonical.write_text(_MIN_CONFIG_TOML + '[general]\ndefault_mode = "thinking"\n')

    cm = ConfigManager()
    cm.load_all_layers({})

    assert cm.project_config_path is not None
    assert Path(cm.project_config_path).resolve() == canonical.resolve()
    assert cm.get("general.default_mode") == "thinking"


def test_b2_only_hidden_project_file_loads(isolated_xdg: Path) -> None:
    """B2: only `./.doxa.config.toml` exists → loads it."""
    project = _project_dir(isolated_xdg)
    hidden = project / ".doxa.config.toml"
    hidden.write_text(_MIN_CONFIG_TOML + '[general]\ndefault_mode = "exploration"\n')

    cm = ConfigManager()
    cm.load_all_layers({})

    assert cm.project_config_path is not None
    assert Path(cm.project_config_path).resolve() == hidden.resolve()
    assert cm.get("general.default_mode") == "exploration"


def test_b3_both_project_files_raises_ambiguity(isolated_xdg: Path) -> None:
    """B3: both project files present → ConfigAmbiguousError naming both, no precedence."""
    project = _project_dir(isolated_xdg)
    visible = project / "doxa.config.toml"
    hidden = project / ".doxa.config.toml"
    visible.write_text(_MIN_CONFIG_TOML)
    hidden.write_text(_MIN_CONFIG_TOML)

    cm = ConfigManager()
    with pytest.raises(ConfigAmbiguousError) as excinfo:
        cm.load_all_layers({})

    msg = str(excinfo.value)
    assert "doxa.config.toml" in msg
    assert ".doxa.config.toml" in msg
    # Direct user to delete one — no precedence.
    assert "delete" in msg.lower()


@pytest.mark.parametrize(
    "argv",
    [
        ["config", "get", "general.default_mode", "--json"],
        ["config", "list", "--json"],
    ],
)
def test_b9_config_json_ambiguous_project_config_emits_error_envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    argv: list[str],
) -> None:
    """B9: JSON config commands wrap project config ambiguity in JSON."""
    from doxa_research import config as doxa_config

    monkeypatch.setattr(doxa_config, "_config_path", None)
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("doxa.config.toml").write_text(_MIN_CONFIG_TOML + "# visible\n")
        Path(".doxa.config.toml").write_text(_MIN_CONFIG_TOML + "# hidden\n")

        result = runner.invoke(cli, argv, env=_xdg_env(tmp_path))

    assert result.exit_code == 1
    assert result.output.startswith("{"), result.output or repr(result.exception)
    payload = json.loads(result.output)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "CONFIG_AMBIGUOUS"
    assert "doxa.config.toml" in payload["error"]["message"]
    assert ".doxa.config.toml" in payload["error"]["message"]
    assert "Delete one" in payload["error"]["message"]


def test_b10_runtime_api_key_error_mentions_legacy_project_config(
    isolated_xdg: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B10: runtime missing-key guidance names ignored legacy project config."""
    from doxa_research import config as doxa_config

    monkeypatch.setattr(doxa_config, "_config_path", None)
    monkeypatch.setenv("XDG_STATE_HOME", str(isolated_xdg / "state"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    project = _project_dir(isolated_xdg)
    legacy = project / "doxa_research.toml"
    legacy.write_text('version = "2.0"\n[providers.openai]\napi_key = "sk-legacy"\n')

    result = CliRunner().invoke(cli, ["test", "legacy", "prompt"])

    assert result.exit_code == 1
    assert "openai API key not found" in result.output
    assert "Detected legacy file: doxa_research.toml" in result.output
    assert "These filenames are no longer read" in result.output
    assert "Rename to doxa.config.toml" in result.output


def test_b4_neither_project_file_optional(isolated_xdg: Path) -> None:
    """B4: no project files → empty project layer, no error from project loading."""
    cm = ConfigManager()
    cm.load_all_layers({})
    assert cm.project_config_path is None


def test_b5_only_legacy_doxa_toml_treated_as_missing(isolated_xdg: Path) -> None:
    """B5: legacy `./doxa_research.toml` is NOT loaded as project config."""
    project = _project_dir(isolated_xdg)
    legacy = project / "doxa_research.toml"
    legacy.write_text(_MIN_CONFIG_TOML + '[general]\ndefault_mode = "thinking"\n')

    cm = ConfigManager()
    cm.load_all_layers({})

    assert cm.project_config_path is None
    assert cm.get("general.default_mode") == "default"


def test_b6_only_legacy_dot_doxa_dir_treated_as_missing(isolated_xdg: Path) -> None:
    """B6: legacy `./.doxa_research/config.toml` is NOT loaded."""
    project = _project_dir(isolated_xdg)
    legacy_dir = project / ".doxa_research"
    legacy_dir.mkdir()
    legacy = legacy_dir / "config.toml"
    legacy.write_text(_MIN_CONFIG_TOML + '[general]\ndefault_mode = "thinking"\n')

    cm = ConfigManager()
    cm.load_all_layers({})

    assert cm.project_config_path is None
    assert cm.get("general.default_mode") == "default"


def test_b7_legacy_doxa_toml_named_in_not_found_message(isolated_xdg: Path) -> None:
    """B7: ConfigNotFoundError suggestion names legacy `./doxa_research.toml` + rename target."""
    project = _project_dir(isolated_xdg)
    legacy = project / "doxa_research.toml"
    legacy.write_text(_MIN_CONFIG_TOML)

    err = _format_config_not_found()
    msg = str(err)
    # Legacy file must appear (path may be absolute or relative).
    assert "doxa_research.toml" in msg
    # Rename target should be referenced.
    assert "doxa.config.toml" in msg


def test_b8_legacy_dot_doxa_config_named_in_not_found_message(
    isolated_xdg: Path,
) -> None:
    """B8: ConfigNotFoundError suggestion names legacy `./.doxa_research/config.toml`."""
    project = _project_dir(isolated_xdg)
    legacy_dir = project / ".doxa_research"
    legacy_dir.mkdir()
    legacy = legacy_dir / "config.toml"
    legacy.write_text(_MIN_CONFIG_TOML)

    err = _format_config_not_found()
    msg = str(err)
    assert ".doxa_research/config.toml" in msg or str(legacy) in msg
    assert "doxa.config.toml" in msg


# ---------------------------------------------------------------------------
# C. Legacy detection helper
# ---------------------------------------------------------------------------


def test_c1_detect_legacy_paths_returns_only_existing(isolated_xdg: Path) -> None:
    """C1: detect_legacy_paths() returns only files that actually exist; no side effects."""
    # No legacy files yet.
    assert detect_legacy_paths() == []

    user_dir = _xdg_doxa_dir(isolated_xdg)
    project = _project_dir(isolated_xdg)

    legacy_user = user_dir / "config.toml"
    legacy_user.write_text(_MIN_CONFIG_TOML)

    legacy_project = project / "doxa_research.toml"
    legacy_project.write_text(_MIN_CONFIG_TOML)

    legacy_dot_dir = project / ".doxa_research"
    legacy_dot_dir.mkdir()
    legacy_dot = legacy_dot_dir / "config.toml"
    legacy_dot.write_text(_MIN_CONFIG_TOML)

    found = detect_legacy_paths()
    found_resolved = {Path(p).resolve() for p in found}
    assert legacy_user.resolve() in found_resolved
    assert legacy_project.resolve() in found_resolved
    assert legacy_dot.resolve() in found_resolved
    # Pure function: no canonical files were created as a side effect.
    assert not (user_dir / "doxa.config.toml").exists()
    assert not (project / "doxa.config.toml").exists()
    assert not (project / ".doxa.config.toml").exists()


def test_c2_successful_load_does_not_call_legacy_detector(
    isolated_xdg: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C2: regression guard — happy-path load must not invoke detect_legacy_paths."""
    user_dir = _xdg_doxa_dir(isolated_xdg)
    canonical = user_dir / "doxa.config.toml"
    canonical.write_text(_MIN_CONFIG_TOML + '[general]\ndefault_mode = "thinking"\n')

    calls = {"n": 0}

    def spy() -> list[Path]:
        calls["n"] += 1
        return []

    import doxa_research.config as cfg_mod

    monkeypatch.setattr(cfg_mod, "detect_legacy_paths", spy, raising=True)

    cm = ConfigManager()
    cm.load_all_layers({})

    assert calls["n"] == 0, (
        "detect_legacy_paths must not be called during a successful load; "
        "it is reserved for the ConfigNotFoundError formatter."
    )


def test_c3_not_found_formatter_calls_detector_exactly_once(
    isolated_xdg: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C3: _format_config_not_found() invokes detect_legacy_paths exactly once."""
    calls = {"n": 0}

    def spy() -> list[Path]:
        calls["n"] += 1
        return []

    import doxa_research.config as cfg_mod

    monkeypatch.setattr(cfg_mod, "detect_legacy_paths", spy, raising=True)

    err = cfg_mod._format_config_not_found()
    assert isinstance(err, ConfigNotFoundError)
    assert calls["n"] == 1


# ---------------------------------------------------------------------------
# D. `doxa init` flag combinations
# ---------------------------------------------------------------------------


def _xdg_env(tmp: Path) -> dict[str, str]:
    """Env vars to feed CliRunner.invoke so XDG_CONFIG_HOME points into tmp."""
    return {"XDG_CONFIG_HOME": str(tmp / "xdg")}


def test_d1_default_writes_visible_project_file(tmp_path: Path) -> None:
    """D1: `doxa init` with no flags writes ./doxa.config.toml."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(init_cmd, ["--non-interactive"], env=_xdg_env(tmp_path))
        assert result.exit_code == 0, result.output
        assert Path("doxa.config.toml").exists()
        assert not Path(".doxa.config.toml").exists()


def test_d2_hidden_writes_dotfile_project(tmp_path: Path) -> None:
    """D2: `doxa init --hidden` writes ./.doxa.config.toml."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(init_cmd, ["--hidden", "--non-interactive"], env=_xdg_env(tmp_path))
        assert result.exit_code == 0, result.output
        assert Path(".doxa.config.toml").exists()
        assert not Path("doxa.config.toml").exists()


def test_d3_user_writes_xdg_canonical(tmp_path: Path) -> None:
    """D3: `doxa init --user` writes $XDG_CONFIG_HOME/doxa_research/doxa.config.toml."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(init_cmd, ["--user", "--non-interactive"], env=_xdg_env(tmp_path))
        assert result.exit_code == 0, result.output
        target = tmp_path / "xdg" / "doxa" / "doxa.config.toml"
        assert target.exists(), f"expected {target} to exist; output:\n{result.output}"


def test_d12_user_init_ignores_project_config_ambiguity(tmp_path: Path) -> None:
    """D12: `doxa init --user` writes XDG config even if project configs conflict."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("doxa.config.toml").write_text(_MIN_CONFIG_TOML + "# visible\n")
        Path(".doxa.config.toml").write_text(_MIN_CONFIG_TOML + "# hidden\n")

        result = runner.invoke(init_cmd, ["--user", "--non-interactive"], env=_xdg_env(tmp_path))

        assert result.exit_code == 0, result.output
        target = tmp_path / "xdg" / "doxa" / "doxa.config.toml"
        assert target.exists(), f"expected {target} to exist; output:\n{result.output}"
        assert "visible" in Path("doxa.config.toml").read_text()
        assert "hidden" in Path(".doxa.config.toml").read_text()


def test_d4_user_and_hidden_mutually_exclusive(tmp_path: Path) -> None:
    """D4: `doxa init --user --hidden` is rejected at the Click layer."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(init_cmd, ["--user", "--hidden"], env=_xdg_env(tmp_path))
        assert result.exit_code != 0
        assert "mutually exclusive" in (result.output or "") + (
            (result.stderr if hasattr(result, "stderr") else "") or ""
        )


def test_d5_no_force_refuses_overwrite(tmp_path: Path) -> None:
    """D5: `doxa init` refuses to overwrite an existing ./doxa.config.toml."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("doxa.config.toml").write_text(_MIN_CONFIG_TOML + "# preexisting\n")
        result = runner.invoke(init_cmd, [], env=_xdg_env(tmp_path))
        assert result.exit_code != 0
        # Original content preserved.
        assert "preexisting" in Path("doxa.config.toml").read_text()


def test_d6_force_overwrites_visible_project_file(tmp_path: Path) -> None:
    """D6: `doxa init --force` overwrites an existing ./doxa.config.toml."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("doxa.config.toml").write_text(_MIN_CONFIG_TOML + "# preexisting\n")
        result = runner.invoke(init_cmd, ["--force", "--non-interactive"], env=_xdg_env(tmp_path))
        assert result.exit_code == 0, result.output
        # Pre-existing content was replaced.
        assert "preexisting" not in Path("doxa.config.toml").read_text()


def test_d7_user_no_force_refuses_overwrite(tmp_path: Path) -> None:
    """D7: `doxa init --user` refuses to overwrite the existing user file."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        target = tmp_path / "xdg" / "doxa" / "doxa.config.toml"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_MIN_CONFIG_TOML + "# preexisting\n")

        result = runner.invoke(init_cmd, ["--user"], env=_xdg_env(tmp_path))
        assert result.exit_code != 0
        assert "preexisting" in target.read_text()


def test_d8_user_force_overwrites(tmp_path: Path) -> None:
    """D8: `doxa init --user --force` overwrites the existing user file."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        target = tmp_path / "xdg" / "doxa" / "doxa.config.toml"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_MIN_CONFIG_TOML + "# preexisting\n")

        result = runner.invoke(
            init_cmd, ["--user", "--force", "--non-interactive"], env=_xdg_env(tmp_path)
        )
        assert result.exit_code == 0, result.output
        assert "preexisting" not in target.read_text()


def test_d9_hidden_writes_alongside_existing_visible(tmp_path: Path) -> None:
    """D9: `doxa init --hidden` writes the dotfile even if visible exists.

    `init` does not pre-detect the resulting B3 ambiguity; the next load surfaces it.
    """
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("doxa.config.toml").write_text(_MIN_CONFIG_TOML + "# preexisting\n")
        result = runner.invoke(init_cmd, ["--hidden", "--non-interactive"], env=_xdg_env(tmp_path))
        assert result.exit_code == 0, result.output
        assert Path(".doxa.config.toml").exists()
        # Visible file untouched.
        assert "preexisting" in Path("doxa.config.toml").read_text()


def test_d10_hidden_force_overwrites_existing_dotfile(tmp_path: Path) -> None:
    """D10: `doxa init --hidden --force` overwrites ./.doxa.config.toml."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path(".doxa.config.toml").write_text(_MIN_CONFIG_TOML + "# preexisting\n")
        result = runner.invoke(
            init_cmd, ["--hidden", "--force", "--non-interactive"], env=_xdg_env(tmp_path)
        )
        assert result.exit_code == 0, result.output
        assert "preexisting" not in Path(".doxa.config.toml").read_text()


def test_d11_json_envelope_reflects_target(tmp_path: Path) -> None:
    """D11: `doxa init --json --non-interactive --user` reports the user-tier path."""
    import json as _json

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            init_cmd,
            ["--json", "--non-interactive", "--user"],
            env=_xdg_env(tmp_path),
        )
        assert result.exit_code == 0, result.output
        payload = _json.loads(result.output)
        target = tmp_path / "xdg" / "doxa" / "doxa.config.toml"
        assert Path(payload["data"]["config_path"]).resolve() == target.resolve()


def test_d13_json_no_force_refuses_overwrite_with_error_envelope(
    tmp_path: Path,
) -> None:
    """D13: JSON init preserves no-force overwrite semantics in an error envelope."""
    import json as _json

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("doxa.config.toml").write_text(_MIN_CONFIG_TOML + "# preexisting\n")

        result = runner.invoke(
            init_cmd,
            ["--json", "--non-interactive"],
            env=_xdg_env(tmp_path),
        )

        assert result.exit_code == 1
        assert result.exception is not None
        payload = _json.loads(result.output)
        assert payload["status"] == "error"
        assert payload["error"]["code"] == "DOXA_ERROR"
        assert "refusing to overwrite existing" in payload["error"]["message"]
        assert "Pass --force" in payload["error"]["message"]
        assert "preexisting" in Path("doxa.config.toml").read_text()


def test_d14_json_force_overwrites_existing_project_file(tmp_path: Path) -> None:
    """D14: JSON init --force still reaches the intended project-file target."""
    import json as _json

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("doxa.config.toml").write_text(_MIN_CONFIG_TOML + "# preexisting\n")

        result = runner.invoke(
            init_cmd,
            ["--json", "--non-interactive", "--force"],
            env=_xdg_env(tmp_path),
        )

        assert result.exit_code == 0, result.output
        payload = _json.loads(result.output)
        assert payload["status"] == "ok"
        assert payload["data"]["created"] is False
        assert Path(payload["data"]["config_path"]).resolve() == Path("doxa.config.toml").resolve()
        assert "preexisting" not in Path("doxa.config.toml").read_text()


# ---------------------------------------------------------------------------
# E. String-sweep regression guards
# ---------------------------------------------------------------------------


_ALLOWLIST_TOKENS = (
    "LEGACY_USER_FILENAME",
    "LEGACY_PROJECT_PATHS",
    "LEGACY_USER_PATH",
    "detect_legacy_paths",
)


def _iter_py_files() -> list[Path]:
    files: list[Path] = []
    for root in (SRC_DIR, TESTS_DIR):
        files.extend(p for p in root.rglob("*.py") if p.resolve() != THIS_FILE)
    return files


def _line_is_allowlisted(line: str) -> bool:
    return any(token in line for token in _ALLOWLIST_TOKENS)


def _scan_for(pattern: re.Pattern[str]) -> list[tuple[Path, int, str]]:
    """Return (path, lineno, line) tuples where pattern matches and line is not allowlisted."""
    hits: list[tuple[Path, int, str]] = []
    for path in _iter_py_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line) and not _line_is_allowlisted(line):
                hits.append((path, lineno, line))
    return hits


def _format_hits(hits: list[tuple[Path, int, str]]) -> str:
    return "\n".join(f"  {p}:{n}: {line.rstrip()}" for p, n, line in hits)


def test_e1_no_bare_config_toml_in_src_or_tests() -> None:
    """E1: bare `config.toml` literal must not appear outside the legacy detector."""
    # Match `config.toml` not preceded by `doxa_research.` (so `doxa.config.toml` is OK).
    pattern = re.compile(r"(?<!doxa_research\.)(?<!\.)config\.toml")
    hits = _scan_for(pattern)
    assert not hits, (
        "Bare 'config.toml' references found outside the legacy detector / allowlist:\n"
        + _format_hits(hits)
    )


def test_e2_no_legacy_doxa_toml_in_src_or_tests() -> None:
    """E2: legacy `doxa_research.toml` literal must not appear outside the legacy detector."""
    # Match `doxa_research.toml` NOT immediately preceded by `.config` (so `doxa.config.toml` is OK).
    pattern = re.compile(r"(?<!\.config\.)doxa_research\.toml")
    hits = _scan_for(pattern)
    assert not hits, (
        "Legacy 'doxa_research.toml' references found outside the legacy detector / allowlist:\n"
        + _format_hits(hits)
    )


def test_e3_no_dot_doxa_config_dir_in_src_or_tests() -> None:
    """E3: legacy `.doxa_research/config` directory form must not appear outside the legacy detector."""
    pattern = re.compile(r"\.doxa_research/config")
    hits = _scan_for(pattern)
    assert not hits, (
        "Legacy '.doxa_research/config' references found outside the legacy detector / allowlist:\n"
        + _format_hits(hits)
    )


# Silence "imported but unused" complaints from linters: keep references live.
_ = (user_config_dir,)
