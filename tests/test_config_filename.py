"""P21c: failing test scenario matrix for canonical config filename.

This file is written in the RED phase of TDD. The symbols it imports
(`detect_legacy_paths`, `ConfigAmbiguousError`, `ConfigNotFoundError`,
`_format_config_not_found`) do not yet exist; the renamed `user_config_file()`
still returns the legacy path; and `thoth init` lacks `--user`/`--hidden`/
`--force` flags. All tests in this file are expected to fail at import time
or at assertion time until Tasks 2-4 of P21c land.

Coverage:
- A1-A5  user-tier loading
- B1-B8  project-tier loading
- C1-C3  legacy detection helper contract
- D1-D11 `thoth init` flag combinations
- E1-E3  source-tree string-sweep regression guards
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from thoth.cli_subcommands.init import init as init_cmd
from thoth.config import (
    ConfigManager,
    _format_config_not_found,
    detect_legacy_paths,
)
from thoth.errors import (
    ConfigAmbiguousError,
    ConfigNotFoundError,
)
from thoth.paths import user_config_dir, user_config_file

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


def _xdg_thoth_dir(isolated_xdg_root: Path) -> Path:
    """`$XDG_CONFIG_HOME/thoth/` for the test."""
    d = isolated_xdg_root / "xdg" / "thoth"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _project_dir(isolated_xdg_root: Path) -> Path:
    return isolated_xdg_root / "project"


_MIN_CONFIG_TOML = 'version = "2.0"\n'


# ---------------------------------------------------------------------------
# A. User-tier loading
# ---------------------------------------------------------------------------


def test_a1_user_canonical_loads(isolated_xdg: Path) -> None:
    """A1: canonical user file at $XDG_CONFIG_HOME/thoth/thoth.config.toml loads."""
    user_dir = _xdg_thoth_dir(isolated_xdg)
    canonical = user_dir / "thoth.config.toml"
    canonical.write_text(_MIN_CONFIG_TOML + '[general]\ndefault_mode = "thinking"\n')

    cm = ConfigManager()
    cm.load_all_layers({})

    assert cm.user_config_path == canonical
    assert cm.get("general.default_mode") == "thinking"


def test_a2_only_legacy_user_file_treated_as_missing(isolated_xdg: Path) -> None:
    """A2: legacy `config.toml` is not loaded; user_config_path points at canonical."""
    user_dir = _xdg_thoth_dir(isolated_xdg)
    legacy = user_dir / "config.toml"
    legacy.write_text(_MIN_CONFIG_TOML + '[general]\ndefault_mode = "thinking"\n')

    cm = ConfigManager()
    cm.load_all_layers({})

    canonical = user_dir / "thoth.config.toml"
    assert cm.user_config_path == canonical
    assert not canonical.exists()
    # Legacy must not have been loaded — value should fall back to default.
    assert cm.get("general.default_mode") == "default"


def test_a3_canonical_wins_silently_over_legacy(isolated_xdg: Path) -> None:
    """A3: both canonical and legacy user files exist — canonical loads, legacy ignored."""
    user_dir = _xdg_thoth_dir(isolated_xdg)
    canonical = user_dir / "thoth.config.toml"
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
    assert "./thoth.config.toml" in msg
    assert "./.thoth.config.toml" in msg


def test_a5_legacy_user_present_message_names_legacy_and_rename_target(
    isolated_xdg: Path,
) -> None:
    """A5: legacy `config.toml` on disk → message names it and the rename target."""
    user_dir = _xdg_thoth_dir(isolated_xdg)
    legacy = user_dir / "config.toml"
    legacy.write_text(_MIN_CONFIG_TOML)

    err = _format_config_not_found()
    msg = str(err)
    assert str(legacy) in msg
    # Rename guidance should mention the canonical filename target.
    assert "thoth.config.toml" in msg


# ---------------------------------------------------------------------------
# B. Project-tier loading
# ---------------------------------------------------------------------------


def test_b1_only_visible_project_file_loads(isolated_xdg: Path) -> None:
    """B1: only `./thoth.config.toml` exists → loads it."""
    project = _project_dir(isolated_xdg)
    canonical = project / "thoth.config.toml"
    canonical.write_text(_MIN_CONFIG_TOML + '[general]\ndefault_mode = "thinking"\n')

    cm = ConfigManager()
    cm.load_all_layers({})

    assert cm.project_config_path is not None
    assert Path(cm.project_config_path).resolve() == canonical.resolve()
    assert cm.get("general.default_mode") == "thinking"


def test_b2_only_hidden_project_file_loads(isolated_xdg: Path) -> None:
    """B2: only `./.thoth.config.toml` exists → loads it."""
    project = _project_dir(isolated_xdg)
    hidden = project / ".thoth.config.toml"
    hidden.write_text(_MIN_CONFIG_TOML + '[general]\ndefault_mode = "exploration"\n')

    cm = ConfigManager()
    cm.load_all_layers({})

    assert cm.project_config_path is not None
    assert Path(cm.project_config_path).resolve() == hidden.resolve()
    assert cm.get("general.default_mode") == "exploration"


def test_b3_both_project_files_raises_ambiguity(isolated_xdg: Path) -> None:
    """B3: both project files present → ConfigAmbiguousError naming both, no precedence."""
    project = _project_dir(isolated_xdg)
    visible = project / "thoth.config.toml"
    hidden = project / ".thoth.config.toml"
    visible.write_text(_MIN_CONFIG_TOML)
    hidden.write_text(_MIN_CONFIG_TOML)

    cm = ConfigManager()
    with pytest.raises(ConfigAmbiguousError) as excinfo:
        cm.load_all_layers({})

    msg = str(excinfo.value)
    assert "thoth.config.toml" in msg
    assert ".thoth.config.toml" in msg
    # Direct user to delete one — no precedence.
    assert "delete" in msg.lower()


def test_b4_neither_project_file_optional(isolated_xdg: Path) -> None:
    """B4: no project files → empty project layer, no error from project loading."""
    cm = ConfigManager()
    cm.load_all_layers({})
    assert cm.project_config_path is None


def test_b5_only_legacy_thoth_toml_treated_as_missing(isolated_xdg: Path) -> None:
    """B5: legacy `./thoth.toml` is NOT loaded as project config."""
    project = _project_dir(isolated_xdg)
    legacy = project / "thoth.toml"
    legacy.write_text(_MIN_CONFIG_TOML + '[general]\ndefault_mode = "thinking"\n')

    cm = ConfigManager()
    cm.load_all_layers({})

    assert cm.project_config_path is None
    assert cm.get("general.default_mode") == "default"


def test_b6_only_legacy_dot_thoth_dir_treated_as_missing(isolated_xdg: Path) -> None:
    """B6: legacy `./.thoth/config.toml` is NOT loaded."""
    project = _project_dir(isolated_xdg)
    legacy_dir = project / ".thoth"
    legacy_dir.mkdir()
    legacy = legacy_dir / "config.toml"
    legacy.write_text(_MIN_CONFIG_TOML + '[general]\ndefault_mode = "thinking"\n')

    cm = ConfigManager()
    cm.load_all_layers({})

    assert cm.project_config_path is None
    assert cm.get("general.default_mode") == "default"


def test_b7_legacy_thoth_toml_named_in_not_found_message(isolated_xdg: Path) -> None:
    """B7: ConfigNotFoundError suggestion names legacy `./thoth.toml` + rename target."""
    project = _project_dir(isolated_xdg)
    legacy = project / "thoth.toml"
    legacy.write_text(_MIN_CONFIG_TOML)

    err = _format_config_not_found()
    msg = str(err)
    # Legacy file must appear (path may be absolute or relative).
    assert "thoth.toml" in msg
    # Rename target should be referenced.
    assert "thoth.config.toml" in msg


def test_b8_legacy_dot_thoth_config_named_in_not_found_message(
    isolated_xdg: Path,
) -> None:
    """B8: ConfigNotFoundError suggestion names legacy `./.thoth/config.toml`."""
    project = _project_dir(isolated_xdg)
    legacy_dir = project / ".thoth"
    legacy_dir.mkdir()
    legacy = legacy_dir / "config.toml"
    legacy.write_text(_MIN_CONFIG_TOML)

    err = _format_config_not_found()
    msg = str(err)
    assert ".thoth/config.toml" in msg or str(legacy) in msg
    assert "thoth.config.toml" in msg


# ---------------------------------------------------------------------------
# C. Legacy detection helper
# ---------------------------------------------------------------------------


def test_c1_detect_legacy_paths_returns_only_existing(isolated_xdg: Path) -> None:
    """C1: detect_legacy_paths() returns only files that actually exist; no side effects."""
    # No legacy files yet.
    assert detect_legacy_paths() == []

    user_dir = _xdg_thoth_dir(isolated_xdg)
    project = _project_dir(isolated_xdg)

    legacy_user = user_dir / "config.toml"
    legacy_user.write_text(_MIN_CONFIG_TOML)

    legacy_project = project / "thoth.toml"
    legacy_project.write_text(_MIN_CONFIG_TOML)

    legacy_dot_dir = project / ".thoth"
    legacy_dot_dir.mkdir()
    legacy_dot = legacy_dot_dir / "config.toml"
    legacy_dot.write_text(_MIN_CONFIG_TOML)

    found = detect_legacy_paths()
    found_resolved = {Path(p).resolve() for p in found}
    assert legacy_user.resolve() in found_resolved
    assert legacy_project.resolve() in found_resolved
    assert legacy_dot.resolve() in found_resolved
    # Pure function: no canonical files were created as a side effect.
    assert not (user_dir / "thoth.config.toml").exists()
    assert not (project / "thoth.config.toml").exists()
    assert not (project / ".thoth.config.toml").exists()


def test_c2_successful_load_does_not_call_legacy_detector(
    isolated_xdg: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C2: regression guard — happy-path load must not invoke detect_legacy_paths."""
    user_dir = _xdg_thoth_dir(isolated_xdg)
    canonical = user_dir / "thoth.config.toml"
    canonical.write_text(_MIN_CONFIG_TOML + '[general]\ndefault_mode = "thinking"\n')

    calls = {"n": 0}

    def spy() -> list[Path]:
        calls["n"] += 1
        return []

    import thoth.config as cfg_mod

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

    import thoth.config as cfg_mod

    monkeypatch.setattr(cfg_mod, "detect_legacy_paths", spy, raising=True)

    err = cfg_mod._format_config_not_found()
    assert isinstance(err, ConfigNotFoundError)
    assert calls["n"] == 1


# ---------------------------------------------------------------------------
# D. `thoth init` flag combinations
# ---------------------------------------------------------------------------


def _xdg_env(tmp: Path) -> dict[str, str]:
    """Env vars to feed CliRunner.invoke so XDG_CONFIG_HOME points into tmp."""
    return {"XDG_CONFIG_HOME": str(tmp / "xdg")}


def test_d1_default_writes_visible_project_file(tmp_path: Path) -> None:
    """D1: `thoth init` with no flags writes ./thoth.config.toml."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(init_cmd, [], env=_xdg_env(tmp_path))
        assert result.exit_code == 0, result.output
        assert Path("thoth.config.toml").exists()
        assert not Path(".thoth.config.toml").exists()


def test_d2_hidden_writes_dotfile_project(tmp_path: Path) -> None:
    """D2: `thoth init --hidden` writes ./.thoth.config.toml."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(init_cmd, ["--hidden"], env=_xdg_env(tmp_path))
        assert result.exit_code == 0, result.output
        assert Path(".thoth.config.toml").exists()
        assert not Path("thoth.config.toml").exists()


def test_d3_user_writes_xdg_canonical(tmp_path: Path) -> None:
    """D3: `thoth init --user` writes $XDG_CONFIG_HOME/thoth/thoth.config.toml."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(init_cmd, ["--user"], env=_xdg_env(tmp_path))
        assert result.exit_code == 0, result.output
        target = tmp_path / "xdg" / "thoth" / "thoth.config.toml"
        assert target.exists(), f"expected {target} to exist; output:\n{result.output}"


def test_d4_user_and_hidden_mutually_exclusive(tmp_path: Path) -> None:
    """D4: `thoth init --user --hidden` is rejected at the Click layer."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(init_cmd, ["--user", "--hidden"], env=_xdg_env(tmp_path))
        assert result.exit_code != 0
        assert "mutually exclusive" in (result.output or "") + (
            (result.stderr if hasattr(result, "stderr") else "") or ""
        )


def test_d5_no_force_refuses_overwrite(tmp_path: Path) -> None:
    """D5: `thoth init` refuses to overwrite an existing ./thoth.config.toml."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("thoth.config.toml").write_text(_MIN_CONFIG_TOML + "# preexisting\n")
        result = runner.invoke(init_cmd, [], env=_xdg_env(tmp_path))
        assert result.exit_code != 0
        # Original content preserved.
        assert "preexisting" in Path("thoth.config.toml").read_text()


def test_d6_force_overwrites_visible_project_file(tmp_path: Path) -> None:
    """D6: `thoth init --force` overwrites an existing ./thoth.config.toml."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("thoth.config.toml").write_text(_MIN_CONFIG_TOML + "# preexisting\n")
        result = runner.invoke(init_cmd, ["--force"], env=_xdg_env(tmp_path))
        assert result.exit_code == 0, result.output
        # Pre-existing content was replaced.
        assert "preexisting" not in Path("thoth.config.toml").read_text()


def test_d7_user_no_force_refuses_overwrite(tmp_path: Path) -> None:
    """D7: `thoth init --user` refuses to overwrite the existing user file."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        target = tmp_path / "xdg" / "thoth" / "thoth.config.toml"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_MIN_CONFIG_TOML + "# preexisting\n")

        result = runner.invoke(init_cmd, ["--user"], env=_xdg_env(tmp_path))
        assert result.exit_code != 0
        assert "preexisting" in target.read_text()


def test_d8_user_force_overwrites(tmp_path: Path) -> None:
    """D8: `thoth init --user --force` overwrites the existing user file."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        target = tmp_path / "xdg" / "thoth" / "thoth.config.toml"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_MIN_CONFIG_TOML + "# preexisting\n")

        result = runner.invoke(init_cmd, ["--user", "--force"], env=_xdg_env(tmp_path))
        assert result.exit_code == 0, result.output
        assert "preexisting" not in target.read_text()


def test_d9_hidden_writes_alongside_existing_visible(tmp_path: Path) -> None:
    """D9: `thoth init --hidden` writes the dotfile even if visible exists.

    `init` does not pre-detect the resulting B3 ambiguity; the next load surfaces it.
    """
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("thoth.config.toml").write_text(_MIN_CONFIG_TOML + "# preexisting\n")
        result = runner.invoke(init_cmd, ["--hidden"], env=_xdg_env(tmp_path))
        assert result.exit_code == 0, result.output
        assert Path(".thoth.config.toml").exists()
        # Visible file untouched.
        assert "preexisting" in Path("thoth.config.toml").read_text()


def test_d10_hidden_force_overwrites_existing_dotfile(tmp_path: Path) -> None:
    """D10: `thoth init --hidden --force` overwrites ./.thoth.config.toml."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path(".thoth.config.toml").write_text(_MIN_CONFIG_TOML + "# preexisting\n")
        result = runner.invoke(init_cmd, ["--hidden", "--force"], env=_xdg_env(tmp_path))
        assert result.exit_code == 0, result.output
        assert "preexisting" not in Path(".thoth.config.toml").read_text()


def test_d11_json_envelope_reflects_target(tmp_path: Path) -> None:
    """D11: `thoth init --json --non-interactive --user` reports the user-tier path."""
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
        target = tmp_path / "xdg" / "thoth" / "thoth.config.toml"
        assert Path(payload["config_path"]).resolve() == target.resolve()


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
    # Match `config.toml` not preceded by `thoth.` (so `thoth.config.toml` is OK).
    pattern = re.compile(r"(?<!thoth\.)(?<!\.)config\.toml")
    hits = _scan_for(pattern)
    assert not hits, (
        "Bare 'config.toml' references found outside the legacy detector / allowlist:\n"
        + _format_hits(hits)
    )


def test_e2_no_legacy_thoth_toml_in_src_or_tests() -> None:
    """E2: legacy `thoth.toml` literal must not appear outside the legacy detector."""
    # Match `thoth.toml` NOT immediately preceded by `.config` (so `thoth.config.toml` is OK).
    pattern = re.compile(r"(?<!\.config\.)thoth\.toml")
    hits = _scan_for(pattern)
    assert not hits, (
        "Legacy 'thoth.toml' references found outside the legacy detector / allowlist:\n"
        + _format_hits(hits)
    )


def test_e3_no_dot_thoth_config_dir_in_src_or_tests() -> None:
    """E3: legacy `.thoth/config` directory form must not appear outside the legacy detector."""
    pattern = re.compile(r"\.thoth/config")
    hits = _scan_for(pattern)
    assert not hits, (
        "Legacy '.thoth/config' references found outside the legacy detector / allowlist:\n"
        + _format_hits(hits)
    )


# Silence "imported but unused" complaints from linters: keep references live.
_ = (user_config_dir,)
