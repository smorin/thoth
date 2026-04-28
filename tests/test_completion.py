"""Category B — completion script generation tests (spec §9.1)."""

from __future__ import annotations

import pytest


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
def test_generate_script_includes_THOTH_COMPLETE_marker(shell):
    from thoth.completion.script import generate_script

    out = generate_script(shell)
    assert "_THOTH_COMPLETE" in out
    assert shell in out


def test_generate_script_rejects_unknown_shell():
    from thoth.completion.script import generate_script

    with pytest.raises(ValueError, match="unsupported shell"):
        generate_script("powershell")


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
def test_fenced_block_brackets_with_thoth_completion_markers(shell):
    from thoth.completion.script import fenced_block

    out = fenced_block(shell)
    assert "# >>> thoth completion >>>" in out
    assert "# <<< thoth completion <<<" in out
    assert "_THOTH_COMPLETE" in out
