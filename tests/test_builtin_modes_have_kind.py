"""P18 Phase A: every builtin mode must declare an explicit `kind`.

Substring sniffing (via `is_background_model`) is deprecated as a *resolution*
path. This test prevents regressions where a new builtin lands without the
field. See `docs/superpowers/specs/2026-04-26-p18-immediate-vs-background-design.md`
§4 Q12 and §5.3.
"""

from __future__ import annotations

import pytest

from thoth.config import BUILTIN_MODES

VALID_KINDS = {"immediate", "background"}


def _resolved_modes() -> list[tuple[str, dict]]:
    """Skip alias stubs — they delegate to a real mode and don't carry kind themselves."""
    return [
        (name, cfg) for name, cfg in BUILTIN_MODES.items() if "_deprecated_alias_for" not in cfg
    ]


@pytest.mark.parametrize("name,cfg", sorted(_resolved_modes()))
def test_builtin_declares_kind(name: str, cfg: dict) -> None:
    assert "kind" in cfg, f"Builtin mode '{name}' missing required 'kind' field"
    assert cfg["kind"] in VALID_KINDS, (
        f"Builtin mode '{name}' has kind={cfg['kind']!r}; must be one of {sorted(VALID_KINDS)}"
    )


def test_at_least_one_immediate_and_one_background() -> None:
    """Sanity: the 12-mode catalog has both kinds represented."""
    kinds = {
        cfg["kind"]
        for cfg in BUILTIN_MODES.values()
        if "kind" in cfg and "_deprecated_alias_for" not in cfg
    }
    assert kinds >= VALID_KINDS, f"Expected both kinds in builtins, got {kinds}"
