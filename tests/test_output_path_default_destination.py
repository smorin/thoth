"""Standardization #3: background ad-hoc default destination is base_output_dir.

Before this change, `OutputManager.get_output_path` fell through to
`Path.cwd()` for ad-hoc background runs — meaning files landed in
whatever directory the user happened to be in when they ran the command.
This was the README's silent-footgun: the README claims "lands in
./research-outputs/" but ad-hoc background runs landed in cwd.

After this change: ad-hoc background defaults to `base_output_dir` (from
config; default `./research-outputs/`). Users who want cwd can opt in
via `--output-dir .`.
"""

from __future__ import annotations

from pathlib import Path

from doxa_research.config import ConfigManager
from doxa_research.output import OutputManager
from tests.conftest import make_operation


def _output_manager(tmp_path: Path) -> OutputManager:
    """Build an OutputManager with base_output_dir under tmp_path."""
    cm = ConfigManager()
    cm.load_all_layers({})
    cm.data["paths"]["base_output_dir"] = str(tmp_path / "research-outputs")
    return OutputManager(cm)


def test_adhoc_default_destination_is_base_output_dir(tmp_path: Path) -> None:
    """No --project, no --output-dir → write under base_output_dir, not cwd."""
    om = _output_manager(tmp_path)
    operation = make_operation("research-adhoc")
    operation.project = None

    path = om.get_output_path(operation, "mock")

    expected_base = tmp_path / "research-outputs"
    assert expected_base in path.parents, (
        f"Expected ad-hoc default to land under {expected_base}, got {path}"
    )
    # Must NOT silently fall through to cwd.
    assert Path.cwd() not in path.parents, (
        f"Ad-hoc default leaked back to cwd ({Path.cwd()}); got {path}"
    )


def test_project_subdirectory_still_works(tmp_path: Path) -> None:
    """Regression: --project NAME still nests under base_output_dir/<NAME>/."""
    om = _output_manager(tmp_path)
    operation = make_operation("research-projected")
    operation.project = "myproject"

    path = om.get_output_path(operation, "mock")

    expected_dir = tmp_path / "research-outputs" / "myproject"
    assert expected_dir in path.parents, (
        f"Expected --project to nest under {expected_dir}, got {path}"
    )


def test_explicit_output_dir_still_wins(tmp_path: Path) -> None:
    """Regression: --output-dir DIR overrides everything."""
    om = _output_manager(tmp_path)
    operation = make_operation("research-outdir")
    operation.project = None
    custom = tmp_path / "custom_dir"

    path = om.get_output_path(operation, "mock", output_dir=str(custom))

    assert custom in path.parents, f"Expected --output-dir to win, got {path}"


def test_output_dir_overrides_project(tmp_path: Path) -> None:
    """Regression: --output-dir wins over --project (current contract)."""
    om = _output_manager(tmp_path)
    operation = make_operation("research-both")
    operation.project = "myproject"
    custom = tmp_path / "custom_dir"

    path = om.get_output_path(operation, "mock", output_dir=str(custom))

    assert custom in path.parents, f"--output-dir should win over --project; got {path}"
