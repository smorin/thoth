"""P18 Phase H: warn-once when a user-defined mode is missing `kind`.

User TOMLs should declare `kind` explicitly (canonical) or pre-existing
modes get a deprecation-style warning at config load. The error form is
deferred to v4.0.0 (future P19); for now, the substring fallback in
`mode_kind` keeps things working but the warning nudges migration.

Spec §4 Q3 + Phase H in the plan.
"""

from __future__ import annotations

import warnings
from pathlib import Path

from thoth.config import ConfigManager


def _write_user_toml(tmp: Path, content: str) -> Path:
    p = tmp / "thoth.toml"
    p.write_text(content)
    return p


def test_user_mode_missing_kind_warns(tmp_path: Path) -> None:
    cfg_path = _write_user_toml(
        tmp_path,
        """\
version = "2.0"

[modes.my_custom]
provider = "openai"
model = "o3"
description = "user mode without kind"
""",
    )
    cm = ConfigManager(config_path=cfg_path)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        cm.load_all_layers({})
    msgs = [str(w.message) for w in caught]
    assert any("my_custom" in m and "kind" in m for m in msgs), (
        f"Expected warn-once on user mode missing kind; got: {msgs}"
    )


def test_user_mode_with_kind_does_not_warn(tmp_path: Path) -> None:
    cfg_path = _write_user_toml(
        tmp_path,
        """\
version = "2.0"

[modes.my_custom]
provider = "openai"
model = "o3"
kind = "immediate"
description = "user mode with kind"
""",
    )
    cm = ConfigManager(config_path=cfg_path)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        cm.load_all_layers({})
    msgs = [str(w.message) for w in caught]
    # No P18-kind warning for this user mode
    assert not any("my_custom" in m and "kind" in m for m in msgs), (
        f"Unexpected warning for fully-declared user mode: {msgs}"
    )


def test_builtin_modes_do_not_trigger_user_kind_warning(tmp_path: Path) -> None:
    """Builtins always declare kind — they must NOT trigger the user-mode warning."""
    cfg_path = _write_user_toml(
        tmp_path,
        """\
version = "2.0"
""",
    )
    cm = ConfigManager(config_path=cfg_path)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        cm.load_all_layers({})
    msgs = [str(w.message) for w in caught]
    # No "missing kind" warnings should fire — builtins all declare it
    assert not any("missing" in m and "kind" in m for m in msgs), (
        f"Builtin should not trigger missing-kind warning; got: {msgs}"
    )
