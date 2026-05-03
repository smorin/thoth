"""Schema-driven configuration defaults for Thoth (P33).

Three-layer architecture:
  Layer 1 — ThothConfig (this module): Pydantic models that define the
             canonical schema with typed defaults.
  Layer 2 — Overlay / partial shapes (Task 3): Partial variants used for
             merging user/project config files and CLI overrides.
  Layer 3 — ConfigSchema.get_defaults() (src/thoth/config.py): Legacy dict-
             based defaults that will be derived from _ROOT_SCHEMA in Task 6.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, create_model

# ---------------------------------------------------------------------------
# Module-level loader metadata
# ---------------------------------------------------------------------------

# Set to True by the CLI --no-validate flag so the validation layer (Task 5)
# can skip strict checks when requested.
_no_validate: bool = False


# ---------------------------------------------------------------------------
# StarterField helper
# ---------------------------------------------------------------------------


def StarterField(default: Any = ..., *, default_factory: Any = None, **kwargs: Any) -> Any:  # noqa: N802
    """Return a Pydantic Field marked as a 'starter' field.

    Starter fields appear in the generated starter config file. Non-starter
    fields are advanced and omitted from starters by default.
    """
    extra = {"in_starter": True}
    if default_factory is not None:
        return Field(default_factory=default_factory, json_schema_extra=extra, **kwargs)
    return Field(default, json_schema_extra=extra, **kwargs)


# ---------------------------------------------------------------------------
# Per-section sub-models
# ---------------------------------------------------------------------------


class GeneralConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_project: str = StarterField("")
    default_mode: str = StarterField("default")


def _checkpoint_dir_default() -> str:
    from thoth.paths import user_checkpoints_dir  # lazy import avoids circular

    return str(user_checkpoints_dir())


class PathsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_output_dir: str = StarterField("./research-outputs")
    checkpoint_dir: str = StarterField(default_factory=_checkpoint_dir_default)


class ExecutionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    poll_interval: int = StarterField(30)
    max_wait: int = StarterField(30)
    parallel_providers: bool = StarterField(True)
    retry_attempts: int = StarterField(3)
    max_transient_errors: int = Field(5)  # advanced — NOT StarterField
    auto_input: bool = StarterField(True)
    prompt_max_bytes: int = Field(1024 * 1024)
    cancel_upstream_on_interrupt: bool = Field(True)


class OutputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    combine_reports: bool = StarterField(False)
    format: Literal["markdown", "json"] = StarterField("markdown")
    include_metadata: bool = StarterField(True)
    timestamp_format: str = StarterField("%Y-%m-%d_%H%M%S")


_CLARIFICATION_SYSTEM_PROMPT = (
    "I don't want you to follow the above question and instructions; "
    "I want you to tell me the ways this is unclear, point out any ambiguities "
    "or anything you don't understand. Follow that by asking questions to help "
    "clarify the ambiguous points. Once there are no more unclear, ambiguous or "
    "not understood portions, help me draft a clear version of the "
    "question/instruction."
)


class ClarificationCLIConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field("openai")
    model: str = Field("gpt-4o-mini")
    temperature: float = Field(0.7)
    max_tokens: int = Field(500)
    retry_attempts: int = Field(3)
    retry_delay: float = Field(2.0)
    system_prompt: str = Field(_CLARIFICATION_SYSTEM_PROMPT)


class ClarificationInteractiveConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field("openai")
    model: str = Field("gpt-4o-mini")
    temperature: float = Field(0.7)
    max_tokens: int = Field(800)
    retry_attempts: int = Field(3)
    retry_delay: float = Field(2.0)
    system_prompt: str = Field(_CLARIFICATION_SYSTEM_PROMPT)
    input_height: int = Field(6)
    max_input_height: int = Field(15)


class ClarificationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cli: ClarificationCLIConfig = Field(default_factory=ClarificationCLIConfig)
    interactive: ClarificationInteractiveConfig = Field(
        default_factory=ClarificationInteractiveConfig
    )


class ModeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str | None = None
    model: str | None = None
    kind: Literal["immediate", "background"] | None = None
    system_prompt: str | None = None
    prompt_prefix: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    providers: list[str] | None = None
    parallel: bool | None = None
    previous: str | None = None
    next: str | None = None
    auto_input: bool | None = None
    description: str | None = None


# ---------------------------------------------------------------------------
# Provider configs (filled in Task 4)
# ---------------------------------------------------------------------------

# Task 4 will replace `providers: dict[str, dict[str, Any]]` with a typed
# ProvidersConfig model. For now we use a plain dict placeholder.

# ---------------------------------------------------------------------------
# Top-level model
# ---------------------------------------------------------------------------


class ThothConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # TODO(P33): unify with CONFIG_VERSION from thoth.config (circular import
    # risk — left as literal until Task 6 refactors the import graph)
    version: str = "2.0"
    general: GeneralConfig = Field(default_factory=GeneralConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    # `providers` is filled in Task 4 — for now use a placeholder dict.
    providers: dict[str, dict[str, Any]] = Field(
        default_factory=lambda: {
            "openai": {"api_key": "${OPENAI_API_KEY}"},
            "perplexity": {"api_key": "${PERPLEXITY_API_KEY}"},
        }
    )
    clarification: ClarificationConfig = Field(default_factory=ClarificationConfig)
    modes: dict[str, ModeConfig] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Overlay/partial/user-file shapes (filled in Task 3)
# ---------------------------------------------------------------------------


def make_partial(model: type[BaseModel], *, suffix: str = "Partial") -> type[BaseModel]:
    """Return a new BaseModel subclass with every field made optional.

    Recursively partials nested BaseModel-typed fields. `dict[str, BaseModel]`
    fields are kept as-is — their value type is already optional-shaped (e.g.
    `ModeConfig` has every field optional).

    The returned model has `model_config = ConfigDict(extra="forbid")` so
    it still catches typos in keys it knows about.
    """
    new_fields: dict[str, Any] = {}
    for name, finfo in model.model_fields.items():
        annotation = finfo.annotation

        # If the field type is itself a BaseModel, recurse.
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            sub_partial = make_partial(annotation, suffix=suffix)
            new_fields[name] = (sub_partial | None, None)
            continue

        # Otherwise wrap whatever it was in Optional with None default.
        new_fields[name] = (annotation | None, None)

    return create_model(
        f"{model.__name__}{suffix}",
        __config__=ConfigDict(extra="forbid"),
        **new_fields,
    )


PartialThothConfig: type[BaseModel] = make_partial(ThothConfig)
"""Mechanically-derived runtime partial — used for CLI/profile-overlay
internals and as the alignment baseline for TS03."""

# Pre-computed partials used in ConfigOverlay field annotations.
_PartialPathsConfig: type[BaseModel] = make_partial(PathsConfig)
_PartialExecutionConfig: type[BaseModel] = make_partial(ExecutionConfig)
_PartialOutputConfig: type[BaseModel] = make_partial(OutputConfig)
_PartialClarificationConfig: type[BaseModel] = make_partial(ClarificationConfig)


class GeneralOverlay(BaseModel):
    """`[general]` table as it can appear in user/profile/cli overlays.

    Mirrors `GeneralConfig`'s fields (all optional) plus the P21 user-only
    fields that are NOT part of `get_defaults()`.
    """

    model_config = ConfigDict(extra="forbid")
    default_project: str | None = None
    default_mode: str | None = None
    default_profile: str | None = None
    prompt_prefix: str | None = None


class ConfigOverlay(BaseModel):
    """A user/profile/cli config layer.

    Every runtime-default field is optional (mirror of `make_partial(ThothConfig)`)
    and `general` is replaced by `GeneralOverlay` so P21 user-only fields are
    accepted.
    """

    model_config = ConfigDict(extra="forbid")
    version: str | None = None
    general: GeneralOverlay | None = None
    paths: _PartialPathsConfig | None = None  # type: ignore[valid-type]  # ty:ignore[invalid-type-form]
    execution: _PartialExecutionConfig | None = None  # type: ignore[valid-type]  # ty:ignore[invalid-type-form]
    output: _PartialOutputConfig | None = None  # type: ignore[valid-type]  # ty:ignore[invalid-type-form]
    providers: dict[str, dict[str, Any]] | None = None  # finalized in Task 4
    clarification: _PartialClarificationConfig | None = None  # type: ignore[valid-type]  # ty:ignore[invalid-type-form]
    modes: dict[str, ModeConfig] | None = None


class ProfileConfig(ConfigOverlay):
    """Profile overlay schema.

    Same as `ConfigOverlay` plus a profile-root `prompt_prefix` (P21).
    """

    prompt_prefix: str | None = None


class UserConfigFile(ConfigOverlay):
    """Top-level shape of an actual `thoth.config.toml` on disk.

    `ConfigOverlay` fields plus a `profiles` super-table (validated by
    `ProfileConfig`) and an `experimental` carve-out (the only field that
    permits arbitrary keys).
    """

    profiles: dict[str, ProfileConfig] = Field(default_factory=dict)
    experimental: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Validation report types (filled in Task 5)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Path resolution helper
# ---------------------------------------------------------------------------


def resolve_path(
    model: type[BaseModel],
    path: tuple[str, ...],
) -> tuple[type[BaseModel], str]:
    """Walk *path* through nested Pydantic BaseModel fields.

    Returns ``(model_class, field_name)`` for the leaf field.

    Raises ``KeyError`` when *path* does not correspond to a declared field.

    Handles:
    - Empty path → KeyError
    - ``head not in model.model_fields`` → KeyError with model name
    - Nested BaseModel → recurse into sub-model
    - ``dict[str, BaseModel]`` annotation → consume one extra path step (the
      dict key) as a wildcard, then recurse into the value type. If path stops
      at the dict-keyed level, accept as resolved.
    - Otherwise → KeyError saying path continues past leaf
    """
    import typing

    if not path:
        raise KeyError(f"Empty path passed to resolve_path for {model.__name__!r}")

    head, *rest = path

    if head not in model.model_fields:
        raise KeyError(
            f"Field {head!r} not found in {model.__name__!r}. "
            f"Available: {sorted(model.model_fields)}"
        )

    if not rest:
        # Leaf reached
        return (model, head)

    # Inspect the annotation to decide how to recurse
    annotation = model.model_fields[head].annotation

    # Unwrap Optional[X] / X | None → X  (handles both typing.Union and PEP 604 types.UnionType)
    import types

    origin = typing.get_origin(annotation)
    if origin is typing.Union or isinstance(annotation, types.UnionType):
        args = [a for a in typing.get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            annotation = args[0]
            origin = typing.get_origin(annotation)

    # Case 1: nested BaseModel
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return resolve_path(annotation, tuple(rest))

    # Case 2: dict[str, SomeType] — consume the next path step as a dict key
    if origin is dict:
        dict_args = typing.get_args(annotation)
        if len(dict_args) == 2:
            value_type = dict_args[1]
            # Consume the wildcard key step
            _key_step, *rest_after_key = rest
            if not rest_after_key:
                # Path stopped at dict key level — accepted as resolved
                return (model, head)
            # Recurse into value type if it's a BaseModel
            if isinstance(value_type, type) and issubclass(value_type, BaseModel):
                return resolve_path(value_type, tuple(rest_after_key))
            # dict[str, dict[...]] or other — if path still has steps we can't
            # validate further; treat as resolved to avoid false negatives
            return (model, head)

    raise KeyError(f"Path {rest!r} continues past leaf field {head!r} in {model.__name__!r}")


# ---------------------------------------------------------------------------
# Public façade (filled in Task 5)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Singleton root model
# ---------------------------------------------------------------------------

# Built once at import time. Tests assert this dump equals get_defaults().
_ROOT_SCHEMA = ThothConfig()
