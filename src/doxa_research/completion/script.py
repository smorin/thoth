"""Generate shell init scripts that wire Click's `_DOXA_COMPLETE` machinery.

Per spec §6.2: each shell's snippet evaluates the appropriate
`_DOXA_COMPLETE=<shell>_source doxa` form to enable TAB completion.
"""

from __future__ import annotations

from typing import Literal

Shell = Literal["bash", "zsh", "fish"]
_SUPPORTED: tuple[str, ...] = ("bash", "zsh", "fish")

_BASH_TEMPLATE = 'eval "$(_DOXA_COMPLETE=bash_source doxa)"'
_ZSH_TEMPLATE = 'eval "$(_DOXA_COMPLETE=zsh_source doxa)"'
_FISH_TEMPLATE = "_DOXA_COMPLETE=fish_source doxa | source"


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

    The fenced markers `# >>> doxa completion >>>` / `# <<< doxa
    completion <<<` make the block trivially removable via:

        sed -i '/# >>> doxa completion >>>/,/# <<< doxa completion <<</d' ~/.bashrc
    """
    if shell not in _SUPPORTED:
        raise ValueError(f"unsupported shell: {shell!r} (supported: {_SUPPORTED})")
    return f"# >>> doxa completion >>>\n{generate_script(shell)}\n# <<< doxa completion <<<\n"


__all__ = ["fenced_block", "generate_script"]
