"""Shared `_research_options` decorator stack.

Per Q3-PR2-C of the P16 PR2 design, the 21-flag research-options surface is
applied identically to (a) the top-level `cli` group and (b) the `ask`
subcommand. This module is the single source of truth.

Order of decorators matters for `--help` rendering: `_RESEARCH_OPTIONS` is
applied in reverse so the resulting `--help` order matches list order.

Note: `--resume` and `--version` (kept inline on `cli` for now; `--resume`
removed in Task 5) now render AFTER the research-options stack rather than
at their historical positions 5/12 in PR1.5. Parity is preserved via the
line-set equality assertions in `tests/test_p16_dispatch_parity.py`, not
byte-equality. Strict help-layout parity is not a regression target.
"""

from __future__ import annotations

from collections.abc import Callable

import click

# Each entry is a (args, kwargs) pair for click.option(*args, **kwargs).
# Applied in REVERSE so the resulting --help order matches list order.
_RESEARCH_OPTIONS: list[tuple[tuple, dict]] = [
    (("--mode", "-m", "mode_opt"), {"help": "Research mode"}),
    (("--prompt", "-q", "prompt_opt"), {"help": "Research prompt"}),
    (("--prompt-file", "-F"), {"help": "Read prompt from file (use - for stdin)"}),
    (("--async", "-A", "async_mode"), {"is_flag": True, "help": "Submit and exit"}),
    (("--project", "-p"), {"help": "Project name"}),
    (("--output-dir", "-o"), {"help": "Override output directory"}),
    (
        ("--provider", "-P"),
        {
            "type": click.Choice(["openai", "perplexity", "mock"]),
            "help": "Single provider",
        },
    ),
    (
        ("--input-file",),
        {
            "help": (
                "Use the file at PATH as input for this mode. Use when feeding a "
                "non-thoth document, an older run, or a file from a different project."
            ),
        },
    ),
    (
        ("--auto",),
        {
            "is_flag": True,
            "help": (
                "Pick up the latest output from the previous mode in the same "
                "--project directory. The happy path for chaining modes."
            ),
        },
    ),
    (("--verbose", "-v"), {"is_flag": True, "help": "Enable debug output"}),
    (
        ("--api-key-openai",),
        {"help": "API key for OpenAI provider (not recommended; prefer env vars)"},
    ),
    (
        ("--api-key-perplexity",),
        {"help": "API key for Perplexity provider (not recommended; prefer env vars)"},
    ),
    (
        ("--api-key-mock",),
        {"help": "API key for Mock provider (not recommended; prefer env vars)"},
    ),
    (("--config", "-c", "config_path"), {"help": "Path to custom config file"}),
    (("--profile", "profile"), {"help": "Configuration profile to apply"}),
    (
        ("--combined",),
        {"is_flag": True, "help": "Generate combined report from multiple providers"},
    ),
    (("--quiet", "-Q"), {"is_flag": True, "help": "Minimal output during execution"}),
    (
        ("--no-metadata",),
        {
            "is_flag": True,
            "help": "Disable metadata headers and prompt section in output files",
        },
    ),
    (("--timeout", "-T"), {"type": float, "help": "Override request timeout in seconds"}),
    (
        ("--out",),
        {
            "multiple": True,
            "help": (
                "P18: output sink for immediate-mode runs. '-' for stdout (default), "
                "PATH for file. Repeatable; comma-list also accepted. "
                "Background modes still use --output-dir / --project."
            ),
        },
    ),
    (
        ("--append",),
        {
            "is_flag": True,
            "help": "P18: open --out file in append mode instead of truncating",
        },
    ),
    (("--interactive", "-i"), {"is_flag": True, "help": "Enter interactive prompt mode"}),
    (
        ("--clarify",),
        {"is_flag": True, "help": "Start interactive mode in Clarification Mode"},
    ),
    (
        ("--pick-model", "-M", "pick_model"),
        {
            "is_flag": True,
            "help": "Interactively pick a model (only for modes with kind='immediate')",
        },
    ),
    (
        ("--cancel-on-interrupt/--no-cancel-on-interrupt", "cancel_on_interrupt"),
        {
            "default": None,
            "help": (
                "On Ctrl-C during a sync background or resume run, also cancel the "
                "upstream provider job (default: per [execution]."
                "cancel_upstream_on_interrupt config, default true). Pass "
                "--no-cancel-on-interrupt to skip the upstream cancel for this run."
            ),
        },
    ),
    (
        ("--no-validate",),
        {
            "is_flag": True,
            "default": False,
            "help": "Suppress config schema validation warnings (debug/CI use only)",
        },
    ),
]


def _research_options(f: Callable) -> Callable:
    """Apply the full 21-flag research-options stack to a Click callback."""
    for args, kwargs in reversed(_RESEARCH_OPTIONS):
        f = click.option(*args, **kwargs)(f)
    return f


__all__ = ["_research_options"]
