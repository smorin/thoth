"""Category H — CI lint rule meta-tests (spec §7.2 + §6.5)."""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent


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
