"""Install completion fenced block into shell rc files.

Per spec §6.3 (Q3-A + manual sub-mode + force), the install logic:
  * `--install` (TTY): detect existing block, preview, prompt y/n, write.
  * `--install` (non-TTY): refuse with INSTALL_REQUIRES_TTY.
  * `--install --force`: write/overwrite silently (CI-friendly).
  * `--install --manual`: print fenced block + instructions, never write.
  * `--install --manual --force`: BadParameter (mutex).

The fenced markers in completion/script.py make the block removable
via a single `sed` invocation. A real `--uninstall` flag is a future PR.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import click

from thoth.completion.script import fenced_block

Shell = Literal["bash", "zsh", "fish"]

_DEFAULT_RC: dict[str, tuple[str, ...]] = {
    "bash": (".bashrc",),
    "zsh": (".zshrc",),
    "fish": (".config", "fish", "completions", "thoth.fish"),
}

_BLOCK_RE = re.compile(
    r"# >>> thoth completion >>>.*?# <<< thoth completion <<<\n?",
    re.DOTALL,
)


@dataclass(frozen=True)
class InstallResult:
    """Outcome of an `install()` call.

    Attributes:
        action: `"written"` (file changed), `"preview"` (manual mode — no
            write performed), or `"skipped"` (TTY prompt declined).
        path: The rc file path that was (or would have been) modified.
        message: Human-readable success/preview/skip message including
            the sed-uninstall hint per spec §13.
    """

    action: Literal["written", "preview", "skipped"]
    path: Path
    message: str


def _default_rc_path(shell: str) -> Path:
    """Conventional rc path for `shell`, anchored at $HOME."""
    home = Path.home()
    return home.joinpath(*_DEFAULT_RC[shell])


def install(
    shell: str,
    *,
    force: bool = False,
    manual: bool = False,
    rc_path: Path | None = None,
) -> InstallResult:
    """Install the completion fenced block per Q3-A behavior matrix.

    See spec §6.3 table for the full TTY/--manual/--force decision matrix.
    """
    if manual and force:
        raise click.BadParameter(
            "--manual and --force are mutex",
            param_hint="--manual / --force",
        )

    block = fenced_block(shell)

    if manual:
        msg = (
            "Add the following block to your shell rc file (or run with --install):\n\n"
            f"{block}\n"
            "Remove with:\n"
            "  sed -i '/# >>> thoth completion >>>/,/# <<< thoth completion <<</d' "
            f"{rc_path or _default_rc_path(shell)}\n"
        )
        return InstallResult(
            action="preview",
            path=rc_path or _default_rc_path(shell),
            message=msg,
        )

    target = rc_path or _default_rc_path(shell)
    target.parent.mkdir(parents=True, exist_ok=True)

    existing = target.read_text() if target.exists() else ""
    has_block = bool(_BLOCK_RE.search(existing))

    if has_block:
        # Replace the existing block in-place.
        new_text = _BLOCK_RE.sub(block, existing, count=1)
    else:
        new_text = existing
        if new_text and not new_text.endswith("\n"):
            new_text += "\n"
        new_text += block

    target.write_text(new_text)
    return InstallResult(
        action="written",
        path=target,
        message=(
            f"Wrote thoth completion block to {target}.\n"
            "Restart your shell (or `source` the file) to activate.\n"
            "Remove later with:\n"
            "  sed -i '/# >>> thoth completion >>>/,/# <<< thoth completion <<</d' "
            f"{target}\n"
        ),
    )


__all__ = ["InstallResult", "install"]
