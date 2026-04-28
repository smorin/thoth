"""Generate shell init scripts that wire Click's `_THOTH_COMPLETE` machinery.

Per spec §6.2: each shell's snippet evaluates the appropriate
`_THOTH_COMPLETE=<shell>_source thoth` form to enable TAB completion.
"""

from __future__ import annotations

from typing import Literal

Shell = Literal["bash", "zsh", "fish"]
_SUPPORTED: tuple[str, ...] = ("bash", "zsh", "fish")

_BASH_TEMPLATE = 'eval "$(_THOTH_COMPLETE=bash_source thoth)"'
_ZSH_TEMPLATE = 'eval "$(_THOTH_COMPLETE=zsh_source thoth)"'
_FISH_TEMPLATE = "_THOTH_COMPLETE=fish_source thoth | source"


def generate_script(shell: str) -> str:
    """Return the eval-able shell init script for `shell`.

    Raises:
        ValueError: if `shell` is not one of bash/zsh/fish.
    """
    if shell not in _SUPPORTED:
        raise ValueError(f"unsupported shell: {shell!r} (supported: {_SUPPORTED})")
    if shell == "bash":
        return _BASH_TEMPLATE
    if shell == "zsh":
        return _ZSH_TEMPLATE
    return _FISH_TEMPLATE  # fish


def fenced_block(shell: str) -> str:
    """Return a fenced block (markers + script) for safe rc-file insertion.

    The fenced markers `# >>> thoth completion >>>` / `# <<< thoth
    completion <<<` make the block trivially removable via:

        sed -i '/# >>> thoth completion >>>/,/# <<< thoth completion <<</d' ~/.bashrc
    """
    if shell not in _SUPPORTED:
        raise ValueError(f"unsupported shell: {shell!r} (supported: {_SUPPORTED})")
    return f"# >>> thoth completion >>>\n{generate_script(shell)}\n# <<< thoth completion <<<\n"


__all__ = ["fenced_block", "generate_script"]
