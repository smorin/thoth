"""Shared CLI next-step hint printing.

Used by `thoth run` and `thoth status` to render `command    description`
hint lines with a single formatting convention.
"""

from __future__ import annotations

from rich.console import Console

console = Console()


def print_hint(cmd: str, desc: str) -> None:
    console.print(f"  [bold]{cmd}[/bold]    {desc}")


def print_saved_not_submitted(op_id: str) -> None:
    console.print(f"\nOperation ID: [bold]{op_id}[/bold] (saved; not submitted)")
    print_hint(f"thoth status {op_id}", "See saved state")
