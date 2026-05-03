"""P33 schema tests.

Covers TS01 (smoke), TS02 (coverage), TS03 (partial regression),
TS07 (provider fields), TS08 (mode/profile prompt surface).

Strict-mode validation uses ConfigSchema.validate(..., strict=True).
"""

from __future__ import annotations

from typing import Any

import pytest


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
    from thoth.config_schema import _ROOT_DEFAULTS_DICT

    assert ConfigSchema.get_defaults() == _ROOT_DEFAULTS_DICT


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


def test_resolve_path_recurses_into_dict_of_basemodel() -> None:
    """`modes: dict[str, ModeConfig]` — paths past the dict key recurse into ModeConfig."""
    from thoth.config_schema import ModeConfig, ThothConfig, resolve_path

    model, name = resolve_path(ThothConfig, ("modes", "thinking", "provider"))
    assert model is ModeConfig
    assert name == "provider"


def test_resolve_path_providers_recurses_into_openai_config() -> None:
    """`providers: ProvidersConfig` — value type is a BaseModel (Task 4),
    so resolve_path recurses into OpenAIConfig and resolves the leaf field.
    """
    from thoth.config_schema import OpenAIConfig, ThothConfig, resolve_path

    model, name = resolve_path(ThothConfig, ("providers", "openai", "api_key"))
    assert model is OpenAIConfig
    assert name == "api_key"


def test_resolve_path_raises_on_unknown_leaf() -> None:
    """Typos like `general.prompy_prefix` must raise KeyError — this is the
    very behavior P33 exists to guarantee."""
    from thoth.config_schema import ThothConfig, resolve_path

    with pytest.raises(KeyError):
        resolve_path(ThothConfig, ("general", "prompy_prefix"))


# ---------- TS03: make_partial regression ----------


def test_make_partial_keeps_field_set() -> None:
    """make_partial(ThothConfig) must produce a model with the same field
    set as ThothConfig, all marked optional with `None` defaults."""
    from thoth.config_schema import PartialThothConfig, ThothConfig

    src_fields = set(ThothConfig.model_fields.keys())
    partial_fields = set(PartialThothConfig.model_fields.keys())
    assert src_fields == partial_fields, (
        f"PartialThothConfig field set drifted from ThothConfig: "
        f"missing {src_fields - partial_fields}, extra {partial_fields - src_fields}"
    )

    for name, finfo in PartialThothConfig.model_fields.items():
        # Each field must have a `None` default, signalling "unset = ok"
        assert finfo.default is None and finfo.default_factory is None, (
            f"PartialThothConfig.{name} should default to None with no factory; "
            f"got default={finfo.default!r}, factory={finfo.default_factory!r}"
        )


def test_make_partial_constructs_empty() -> None:
    from thoth.config_schema import PartialThothConfig

    PartialThothConfig()  # must not raise


# ---------- TS02: overlay-path coverage ----------


def test_user_only_overlay_paths_resolve() -> None:
    """Valid P21 user-only fields must resolve through ConfigOverlay /
    ProfileConfig, even though they are NOT part of get_defaults()."""
    from thoth.config_schema import ConfigOverlay, ProfileConfig, resolve_path

    resolve_path(ConfigOverlay, ("general", "default_profile"))
    resolve_path(ConfigOverlay, ("general", "prompt_prefix"))
    resolve_path(ConfigOverlay, ("modes", "thinking", "system_prompt"))
    resolve_path(ConfigOverlay, ("modes", "thinking", "prompt_prefix"))
    resolve_path(ProfileConfig, ("prompt_prefix",))


# ---------- TS08: mode/profile prompt surface validates ----------


def test_mode_table_with_prompts_validates() -> None:
    from thoth.config_schema import ModeConfig

    ModeConfig(system_prompt="Be precise", prompt_prefix="Cite sources")


def test_profile_with_root_and_nested_prompts_validates() -> None:
    from thoth.config_schema import ModeConfig, ProfileConfig

    profile = ProfileConfig(
        prompt_prefix="Be thorough",
        modes={"thinking": ModeConfig(system_prompt="Step by step")},
    )
    assert profile.prompt_prefix == "Be thorough"
    assert profile.modes is not None and "thinking" in profile.modes


def test_user_file_with_full_p21_shape_validates() -> None:
    from thoth.config_schema import UserConfigFile

    doc = {
        "general": {
            "default_project": "daily-notes",
            "default_profile": "fast",
            "prompt_prefix": "Cite sources",
        },
        "modes": {"thinking": {"system_prompt": "Be careful"}},
        "profiles": {
            "fast": {
                "prompt_prefix": "Be quick",
                "modes": {"thinking": {"system_prompt": "Profile prompt"}},
            }
        },
    }
    UserConfigFile.model_validate(doc)


def test_typo_at_each_overlay_level_raises() -> None:
    from pydantic import ValidationError

    from thoth.config_schema import ProfileConfig, UserConfigFile

    with pytest.raises(ValidationError):
        UserConfigFile.model_validate({"general": {"prompy_prefix": "x"}})

    with pytest.raises(ValidationError):
        ProfileConfig.model_validate({"prompy_prefix": "x"})

    with pytest.raises(ValidationError):
        UserConfigFile.model_validate(
            {"profiles": {"fast": {"modes": {"thinking": {"system_prompy": "x"}}}}}
        )


def test_general_overlay_mirrors_general_config_fields() -> None:
    from thoth.config_schema import GeneralConfig, GeneralOverlay

    runtime = set(GeneralConfig.model_fields.keys())
    overlay = set(GeneralOverlay.model_fields.keys())
    missing = runtime - overlay
    assert not missing, (
        f"GeneralOverlay is missing fields present in GeneralConfig: {missing}. "
        f"Add them as `<name>: T | None = None` to GeneralOverlay."
    )
    overlay_only = overlay - runtime
    assert overlay_only == {"default_profile", "prompt_prefix"}, (
        f"Unexpected overlay-only fields: {overlay_only}. "
        f"Update this test if you intentionally added a new P21-style field."
    )


# ---------- TS07: provider-specific schema fields ----------


def test_openai_provider_temperature_validates() -> None:
    from thoth.config_schema import OpenAIConfig

    OpenAIConfig(api_key="${OPENAI_API_KEY}", temperature=0.7)


def test_perplexity_provider_search_context_size_validates() -> None:
    from thoth.config_schema import PerplexityConfig

    PerplexityConfig(api_key="${PERPLEXITY_API_KEY}", search_context_size="high")


def test_unknown_openai_field_rejected() -> None:
    from pydantic import ValidationError

    from thoth.config_schema import OpenAIConfig

    with pytest.raises(ValidationError) as exc:
        OpenAIConfig(api_key="${OPENAI_API_KEY}", bogus=1)  # type: ignore[call-arg]  # ty: ignore[unknown-argument]
    assert "bogus" in str(exc.value)


def test_perplexity_rejects_openai_specific_fields() -> None:
    from pydantic import ValidationError

    from thoth.config_schema import PerplexityConfig

    # `organization` is OpenAI-specific; Perplexity must reject it.
    with pytest.raises(ValidationError) as exc:
        PerplexityConfig(api_key="${PERPLEXITY_API_KEY}", organization="acme")  # type: ignore[call-arg]  # ty: ignore[unknown-argument]
    assert "organization" in str(exc.value)


def test_providers_config_holds_typed_subsections() -> None:
    from thoth.config_schema import ProvidersConfig

    p = ProvidersConfig()
    assert p.openai.api_key == "${OPENAI_API_KEY}"
    assert p.perplexity.api_key == "${PERPLEXITY_API_KEY}"
