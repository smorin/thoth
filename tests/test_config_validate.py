"""P33 validation behavior tests.

TS05: typos produce warnings (one per typo) but never raise.
TS06: `[experimental]` super-table accepts arbitrary keys.
"""

from __future__ import annotations

import pytest

# ---------- TS05: warn-only behavior ----------


def test_prompy_prefix_typo_produces_one_warning_no_raise() -> None:
    from thoth.config_schema import ConfigSchema

    data = {"general": {"prompy_prefix": "x"}}
    report = ConfigSchema.validate(data, layer="user")
    assert len(report.warnings) == 1
    w = report.warnings[0]
    assert w.path == "general.prompy_prefix"
    assert "extra" in w.message.lower() or "unknown" in w.message.lower()


def test_validate_does_not_raise_on_unknown_field() -> None:
    from thoth.config_schema import ConfigSchema

    ConfigSchema.validate({"general": {"prompy_prefix": "x"}}, layer="user")


def test_no_validate_global_suppresses_warnings() -> None:
    from thoth import config_schema as cs

    cs._no_validate = True
    try:
        report = cs.ConfigSchema.validate({"general": {"prompy_prefix": "x"}}, layer="user")
        assert report.warnings == []
    finally:
        cs._no_validate = False


def test_strict_mode_raises_on_unknown_field() -> None:
    from pydantic import ValidationError

    from thoth.config_schema import ConfigSchema

    with pytest.raises(ValidationError):
        ConfigSchema.validate({"general": {"prompy_prefix": "x"}}, layer="user", strict=True)


# ---------- TS06: [experimental] carve-out ----------


def test_experimental_table_accepts_arbitrary_keys() -> None:
    from thoth.config_schema import ConfigSchema

    data = {
        "experimental": {
            "anything": True,
            "nested": {"deep": {"keys": [1, 2, 3]}},
            "weird_thing": {"plugin_name": "foo"},
        }
    }
    report = ConfigSchema.validate(data, layer="user")
    assert report.warnings == []


def test_experimental_in_strict_mode_also_accepts() -> None:
    from thoth.config_schema import ConfigSchema

    ConfigSchema.validate({"experimental": {"plugin_name": "foo"}}, layer="user", strict=True)


# ---------- --no-validate CLI integration ----------


def test_no_validate_flag_suppresses_runtime_warnings(tmp_path) -> None:
    """`thoth --no-validate ...` must not surface warnings for config typos."""
    import subprocess

    cfg = tmp_path / "thoth.config.toml"
    cfg.write_text(
        "\n".join(
            [
                'version = "2.0"',
                "[general]",
                'prompy_prefix = "x"  # typo',
            ]
        )
    )

    result = subprocess.run(
        ["uv", "run", "thoth", "--no-validate", "--config", str(cfg), "status"],
        capture_output=True,
        text=True,
    )
    combined = result.stdout + result.stderr
    assert "prompy_prefix" not in combined, (
        f"--no-validate should suppress validation warnings; saw: {combined}"
    )


def test_validate_flag_omitted_surfaces_warning(tmp_path) -> None:
    """Without --no-validate, the same typo should warn on stdout."""
    import subprocess

    cfg = tmp_path / "thoth.config.toml"
    cfg.write_text(
        "\n".join(
            [
                'version = "2.0"',
                "[general]",
                'prompy_prefix = "x"',
            ]
        )
    )

    result = subprocess.run(
        ["uv", "run", "thoth", "--config", str(cfg), "status"],
        capture_output=True,
        text=True,
    )
    pytest.xfail("runtime hookup not yet wired — Task 8 (P33-T07) gates this")
    combined = result.stdout + result.stderr
    assert "prompy_prefix" in combined
