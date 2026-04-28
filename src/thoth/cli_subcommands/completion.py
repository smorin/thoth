"""`thoth completion <shell>` Click subcommand.

Per spec §6.5: `shell` is intentionally NOT a `click.Choice`, because
invalid-shell errors must be emit-able as `UNSUPPORTED_SHELL` JSON
envelopes, which Click's choice validation can't do. The body validates
against `{"bash", "zsh", "fish"}`.

Behavior:
  - `thoth completion <shell>` (no flags) — emit eval-able script to stdout.
  - `thoth completion <shell> --install` (TTY) — write fenced block; prompt on overwrite.
  - `thoth completion <shell> --install --force` — write/overwrite silently.
  - `thoth completion <shell> --install --manual` — print block + instructions; never write.
  - Any of the above with `--json` — wrap result/error in JSON envelope.
"""

from __future__ import annotations

import sys

import click

from thoth.completion.install import install as do_install
from thoth.completion.script import generate_script
from thoth.json_output import emit_error, emit_json

_SUPPORTED_SHELLS = ("bash", "zsh", "fish")


@click.command(name="completion")
@click.argument("shell")
@click.option("--install", "do_install_flag", is_flag=True, help="Install completion to rc file")
@click.option("--force", is_flag=True, help="Overwrite existing block silently (CI-friendly)")
@click.option("--manual", is_flag=True, help="Print fenced block + instructions; never write")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def completion(
    ctx: click.Context,
    shell: str,
    do_install_flag: bool,
    force: bool,
    manual: bool,
    as_json: bool,
) -> None:
    """Generate or install shell-completion scripts."""
    if shell not in _SUPPORTED_SHELLS:
        msg = f"unsupported shell: {shell!r} (supported: {', '.join(_SUPPORTED_SHELLS)})"
        if as_json:
            emit_error(
                "UNSUPPORTED_SHELL",
                msg,
                {"shell": shell, "supported": list(_SUPPORTED_SHELLS)},
                exit_code=2,
            )
        click.echo(f"Error: {msg}", err=True)
        ctx.exit(2)

    if do_install_flag:
        # Mutex: --manual vs --force is enforced inside completion.install.install().
        if not (force or manual) and not sys.stdin.isatty():
            if as_json:
                emit_error(
                    "INSTALL_REQUIRES_TTY",
                    "non-TTY install requires --force or --manual",
                    {"shell": shell},
                    exit_code=2,
                )
            click.echo(
                "Error: INSTALL_REQUIRES_TTY — non-TTY install requires --force or --manual",
                err=True,
            )
            ctx.exit(2)

        try:
            result = do_install(shell, force=force, manual=manual)
        except click.BadParameter:
            raise  # Click renders + exits 2.
        except PermissionError as exc:
            if as_json:
                emit_error(
                    "INSTALL_FILE_PERMISSION",
                    str(exc),
                    {"shell": shell},
                    exit_code=1,
                )
            click.echo(f"Error: INSTALL_FILE_PERMISSION — {exc}", err=True)
            ctx.exit(1)

        if as_json:
            emit_json(
                {
                    "shell": shell,
                    "action": result.action,
                    "path": str(result.path),
                    "message": result.message,
                }
            )
        click.echo(result.message)
        return

    # No --install: emit eval-able script to stdout (raw — not wrapped in JSON
    # even if --json is passed; per spec §3 + acceptance criteria, the script
    # stays raw for `eval "$(thoth completion zsh)"` use).
    click.echo(generate_script(shell))


__all__ = ["completion"]
