"""P18 Phase A: KNOWN_MODELS is derived from BUILTIN_MODES.

The registry is the single source of truth for "what models does thoth ship
with, and what kind is each". Cross-mode kind conflicts (same (provider,
model) declared with two different kinds across builtins) raise at import.

See spec §5.3 / §4 Q2.
"""

from __future__ import annotations

import pytest

from thoth.config import BUILTIN_MODES
from thoth.errors import ThothError
from thoth.models import KNOWN_MODELS, ModelSpec, derive_known_models


def test_modelspec_shape() -> None:
    spec = ModelSpec(id="o3", provider="openai", kind="immediate")
    assert spec.id == "o3"
    assert spec.provider == "openai"
    assert spec.kind == "immediate"


def test_known_models_is_a_list_of_modelspec() -> None:
    assert isinstance(KNOWN_MODELS, list)
    assert all(isinstance(m, ModelSpec) for m in KNOWN_MODELS)


def test_known_models_unique_provider_model_pairs() -> None:
    """Each (provider, model) appears at most once."""
    keys = [(m.provider, m.id) for m in KNOWN_MODELS]
    assert len(keys) == len(set(keys)), f"Duplicate (provider, model) pairs in KNOWN_MODELS: {keys}"


def test_every_builtin_appears_in_known_models() -> None:
    """Every (provider, model, kind) triple from a non-alias builtin is in the registry."""
    triples = {(m.provider, m.id, m.kind) for m in KNOWN_MODELS}
    for name, cfg in BUILTIN_MODES.items():
        if "_deprecated_alias_for" in cfg:
            continue
        triple = (cfg["provider"], cfg["model"], cfg["kind"])
        assert triple in triples, f"Builtin {name!r} triple {triple} missing from KNOWN_MODELS"


def test_derive_rejects_cross_mode_kind_conflict() -> None:
    """Two modes claiming the same (provider, model) with different kinds must raise."""
    bogus_modes = {
        "real_immediate": {"provider": "openai", "model": "o3", "kind": "immediate"},
        "fake_background": {"provider": "openai", "model": "o3", "kind": "background"},
    }
    with pytest.raises(ThothError, match="Inconsistent kind"):
        derive_known_models(bogus_modes)


def test_derive_skips_alias_stubs() -> None:
    """`_deprecated_alias_for` stubs don't carry provider/model/kind and must be skipped."""
    modes_with_alias = {
        "real": {"provider": "openai", "model": "o3", "kind": "immediate"},
        "alias_to_real": {"_deprecated_alias_for": "real"},
    }
    specs = derive_known_models(modes_with_alias)
    assert len(specs) == 1
    assert specs[0].id == "o3"


def test_derive_raises_on_missing_required_fields() -> None:
    """Builtin missing provider/model/kind is a thoth bug; raise loudly."""
    broken = {"oops": {"provider": "openai", "model": "o3"}}  # no kind
    with pytest.raises(ThothError, match="missing"):
        derive_known_models(broken)
