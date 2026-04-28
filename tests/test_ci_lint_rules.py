"""Category H — CI lint rule meta-tests (spec §7.2 + §6.5)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CLI_SUBCOMMANDS_DIR = _REPO_ROOT / "src" / "thoth" / "cli_subcommands"


@pytest.mark.parametrize(
    "handler_path",
    [
        "src/thoth/commands.py",
        "src/thoth/config_cmd.py",
        "src/thoth/modes_cmd.py",
    ],
)
def test_handler_modules_do_not_reference_as_json(handler_path):
    """spec §7.2 critical invariant — `as_json` MUST NOT appear in handler modules.

    The JSON-vs-Rich choice lives ONLY at the cli_subcommands/ wrapper
    layer. Handler modules expose pure data functions (`get_*_data`) that
    wrappers either render via Rich or wrap in `emit_json`.

    NOTE: This rule applies to NEW handler-layer code. The legacy
    `_op_get`/`_op_list`/`_op_*` functions in config_cmd.py + modes_cmd.py
    have inline `as_json` parsing kept for backward compatibility with
    the passthrough wrapper path. The lint rule grandfathers this by
    matching only `as_json:` in function signatures (not `as_json` as a
    local variable name).
    """
    content = (_REPO_ROOT / handler_path).read_text()
    # Forbid `as_json` as a function-signature parameter (preceded by `,` or `(`,
    # followed by `:` or `=` or `,`).
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Exclude legacy local-variable assignments inside _op_* functions.
        if "as_json = " in line and "def " not in line:
            continue
        # The forbidden pattern: a function param named as_json.
        # Examples that should fail:
        #   def get_status_data(operation_id, as_json: bool = False) -> dict:
        #   def show_status(operation_id, *, as_json):
        if "as_json:" in line and "def " in line:
            pytest.fail(f"{handler_path}: handler signature contains as_json:\n  {line!r}")
        if "as_json=" in line and "def " in line and ")" not in line.split("def ")[0]:
            pytest.fail(f"{handler_path}: handler signature contains as_json=:\n  {line!r}")


def _discover_json_commands() -> set[str]:
    """Walk every cli_subcommands/*.py and return the set of registered command
    names that declare a `--json` Click option.

    Detection rule: any `@click.command(name="X")` or
    `@<group>.command(name="X")` decorator whose function body or sibling
    decorator stack contains a `@click.option("--json", ...)` declaration.
    """
    discovered: set[str] = set()
    for py_file in _CLI_SUBCOMMANDS_DIR.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        tree = ast.parse(py_file.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            cmd_name: str | None = None
            has_json = False
            for deco in node.decorator_list:
                if not isinstance(deco, ast.Call):
                    continue
                func = deco.func
                # Match `click.command(name="X")` or `<group>.command(name="X")`.
                is_command_deco = isinstance(func, ast.Attribute) and func.attr == "command"
                if is_command_deco:
                    for kw in deco.keywords:
                        if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                            cmd_name = str(kw.value.value)
                # Match `click.option("--json", ...)`.
                is_option_deco = isinstance(func, ast.Attribute) and func.attr == "option"
                if is_option_deco and deco.args:
                    first = deco.args[0]
                    if isinstance(first, ast.Constant) and first.value == "--json":
                        has_json = True
                        break
                    if (
                        isinstance(first, ast.Constant)
                        and isinstance(first.value, str)
                        and first.value.startswith("--json")
                    ):
                        has_json = True
                        break
            if cmd_name and has_json:
                discovered.add(cmd_name)
    return discovered


def test_JSON_COMMANDS_list_covers_every_subcommand_with_json_option():
    """Spec §6.5 + §9.1 H — every subcommand that has `@click.option("--json", ...)`
    MUST appear in at least one JSON-envelope test row.

    Coverage rows live primarily in `tests/test_json_envelopes.py::JSON_COMMANDS`
    (smoke contract assertions), with timing-sensitive `ask` rows in
    `tests/test_json_non_blocking.py`. The walker scans both.

    If this test fails, a recent PR added `--json` to a subcommand without
    a covering row — add a row in the appropriate test file.
    """
    from tests.test_json_envelopes import JSON_COMMANDS

    discovered = _discover_json_commands()
    # Collect every positional token from JSON_COMMANDS and from any argv
    # literal in test_json_non_blocking.py. Discovered names are subcommand
    # leaves; any row whose argv mentions the name covers it.
    listed: set[str] = set()
    for _label, argv, _exit in JSON_COMMANDS:
        for token in argv:
            if not token.startswith("-"):
                listed.add(token)

    # Also harvest argv tokens from test_json_non_blocking.py — that file
    # owns the timing-sensitive `ask --json` rows by design.
    non_blocking_path = _REPO_ROOT / "tests" / "test_json_non_blocking.py"
    if non_blocking_path.exists():
        nb_tree = ast.parse(non_blocking_path.read_text())
        for node in ast.walk(nb_tree):
            if not isinstance(node, ast.List):
                continue
            elts = node.elts
            # An argv list mentions "--json" somewhere among string constants.
            has_json_flag = any(
                isinstance(e, ast.Constant) and isinstance(e.value, str) and e.value == "--json"
                for e in elts
            )
            if not has_json_flag:
                continue
            for e in elts:
                if (
                    isinstance(e, ast.Constant)
                    and isinstance(e.value, str)
                    and not e.value.startswith("-")
                ):
                    listed.add(e.value)

    missing = discovered - listed
    assert not missing, (
        f"Subcommands with --json option not covered: {missing}. "
        f"Add a parametrize row in tests/test_json_envelopes.py "
        f"(or tests/test_json_non_blocking.py for timing-sensitive cases)."
    )


def test_AST_walker_finds_at_least_completion_init_status_list():
    """Sanity check on the walker — if it returns nothing, the patterns are wrong."""
    discovered = _discover_json_commands()
    # T04 + T06-T08 ensure these four are present at minimum.
    assert "completion" in discovered
    assert "init" in discovered
    assert "status" in discovered
    assert "list" in discovered
