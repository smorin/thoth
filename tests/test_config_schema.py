"""P33 schema tests.

Covers TS01 (smoke), TS02 (coverage), TS03 (partial regression),
TS07 (provider fields), TS08 (mode/profile prompt surface).

Strict-mode validation uses ConfigSchema.validate(..., strict=True).
"""

from __future__ import annotations

from typing import Any


def _walk_leaves(d: dict[str, Any], prefix: tuple[str, ...] = ()) -> list[tuple[str, ...]]:
    """Yield every leaf path through a nested dict.

    A "leaf" is a path whose value is NOT a dict. Empty dicts (e.g.
    `modes = {}`) are considered leaves themselves.
    """
    out: list[tuple[str, ...]] = []
    for key, value in d.items():
        path = prefix + (key,)
        if isinstance(value, dict) and value:
            out.extend(_walk_leaves(value, path))
        else:
            out.append(path)
    return out


# ---------- TS01: smoke ----------


def test_thoth_config_constructs_with_no_overrides() -> None:
    from thoth.config_schema import ThothConfig

    cfg = ThothConfig()
    assert cfg.version == "2.0"


def test_get_defaults_equals_root_schema_dump() -> None:
    from thoth.config import ConfigSchema
    from thoth.config_schema import _ROOT_SCHEMA

    assert ConfigSchema.get_defaults() == _ROOT_SCHEMA.model_dump(mode="python")


# ---------- TS02: coverage (default paths only at this stage) ----------


def test_every_default_path_resolves_to_a_field() -> None:
    """Every leaf path in get_defaults() must resolve to a ThothConfig field.

    This is the test that catches the `prompy_prefix` typo class.
    """
    from thoth.config import ConfigSchema
    from thoth.config_schema import ThothConfig, resolve_path

    defaults = ConfigSchema.get_defaults()
    for path in _walk_leaves(defaults):
        # `resolve_path` returns a (model, field_name) tuple or raises
        # KeyError if the path doesn't reach a declared field.
        resolve_path(ThothConfig, path)
