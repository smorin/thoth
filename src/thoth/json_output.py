"""Single source of truth for the `--json` envelope contract.

Per spec §6.1 of docs/superpowers/specs/2026-04-26-p16-pr3-design.md, every
`--json` command emits one of two envelope shapes and exits:

  Success:  {"status": "ok",    "data":  {...}}
  Error:    {"status": "error", "error": {"code": "...", "message": "...",
                                          "details": {...}?}}

This module is framework-free (stdlib only) so handlers can import it
without touching Click. The CI lint rule in tests/test_ci_lint_rules.py
enforces that the wrapper layer (cli_subcommands/) is the ONLY place that
calls emit_json/emit_error — handler modules (commands.py, config_cmd.py,
modes_cmd.py) MUST stay JSON-agnostic via the B-deferred get_*_data()
extraction pattern.
"""

from __future__ import annotations

import json
import sys
from typing import Any, NoReturn


def emit_json(data: dict[str, Any], *, exit_code: int = 0) -> NoReturn:
    """Emit a success envelope and exit.

    Args:
        data: The dict to wrap as `data` inside the envelope.
        exit_code: Process exit code. Defaults to 0; use 130 for SIGINT
            recovery paths.
    """
    sys.stdout.write(json.dumps({"status": "ok", "data": data}))
    sys.stdout.write("\n")
    sys.stdout.flush()
    sys.exit(exit_code)


def emit_error(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    *,
    exit_code: int = 1,
) -> NoReturn:
    """Emit an error envelope and exit.

    Args:
        code: Stable machine-readable error code (e.g. ``OPERATION_NOT_FOUND``).
            See spec §8.1 for the catalog.
        message: Human-readable description.
        details: Optional dict for code-specific context.
        exit_code: Process exit code. Defaults to 1; common overrides are
            2 (usage), 6 (operation not found), 7 (operation failed
            permanently), 130 (SIGINT).
    """
    err: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        err["details"] = details
    sys.stdout.write(json.dumps({"status": "error", "error": err}))
    sys.stdout.write("\n")
    sys.stdout.flush()
    sys.exit(exit_code)


__all__ = ["emit_error", "emit_json"]
