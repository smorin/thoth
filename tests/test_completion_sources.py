"""Category D — completion data-source unit tests (spec §9.1)."""

from __future__ import annotations

import json

from tests.conftest import make_operation


def _make_ctx_param():
    """Click passes (ctx, param, incomplete) to shell_complete callbacks.

    For unit tests we don't need real Context/Parameter objects; the source
    functions ignore ctx/param and only filter on `incomplete`.
    """
    return None, None


def test_operation_ids_returns_stems_of_checkpoint_files(checkpoint_dir):
    from thoth.completion.sources import operation_ids

    op1 = make_operation("research-20260427-000000-aaaaaaaaaaaaaaaa")
    op2 = make_operation("research-20260427-000001-bbbbbbbbbbbbbbbb")
    for op in (op1, op2):
        (checkpoint_dir / f"{op.id}.json").write_text(
            json.dumps(
                {
                    "id": op.id,
                    "prompt": op.prompt,
                    "mode": op.mode,
                    "status": op.status,
                    "created_at": op.created_at.isoformat(),
                    "updated_at": op.updated_at.isoformat(),
                    "output_paths": {},
                    "input_files": [],
                    "providers": {},
                    "project": None,
                    "output_dir": None,
                    "error": None,
                    "failure_type": None,
                }
            )
        )

    ctx, param = _make_ctx_param()
    out = operation_ids(ctx, param, "")
    assert op1.id in out
    assert op2.id in out


def test_operation_ids_filters_by_incomplete_prefix(checkpoint_dir):
    from thoth.completion.sources import operation_ids

    target = make_operation("research-20260427-000000-aaaaaaaaaaaaaaaa")
    other = make_operation("research-20260428-000000-bbbbbbbbbbbbbbbb")
    for op in (target, other):
        (checkpoint_dir / f"{op.id}.json").write_text(
            json.dumps(
                {
                    "id": op.id,
                    "prompt": op.prompt,
                    "mode": op.mode,
                    "status": op.status,
                    "created_at": op.created_at.isoformat(),
                    "updated_at": op.updated_at.isoformat(),
                    "output_paths": {},
                    "input_files": [],
                    "providers": {},
                    "project": None,
                    "output_dir": None,
                    "error": None,
                    "failure_type": None,
                }
            )
        )

    ctx, param = _make_ctx_param()
    out = operation_ids(ctx, param, "research-20260427")
    assert target.id in out
    assert other.id not in out


def test_operation_ids_returns_empty_when_no_checkpoints(isolated_thoth_home):
    from thoth.completion.sources import operation_ids

    ctx, param = _make_ctx_param()
    assert operation_ids(ctx, param, "") == []


def test_mode_names_includes_default_and_other_builtins():
    from thoth.completion.sources import mode_names

    ctx, param = _make_ctx_param()
    out = mode_names(ctx, param, "")
    assert "default" in out


def test_mode_names_filters_by_incomplete_prefix():
    from thoth.completion.sources import mode_names

    ctx, param = _make_ctx_param()
    out = mode_names(ctx, param, "deep")
    assert all(name.startswith("deep") for name in out)


def test_config_keys_returns_dotted_keys_from_defaults(isolated_thoth_home):
    from thoth.completion.sources import config_keys

    ctx, param = _make_ctx_param()
    out = config_keys(ctx, param, "")
    assert any("." in key for key in out)


def test_config_keys_filters_by_incomplete_prefix(isolated_thoth_home):
    from thoth.completion.sources import config_keys

    ctx, param = _make_ctx_param()
    out = config_keys(ctx, param, "providers.")
    assert all(key.startswith("providers.") for key in out)


def test_provider_names_returns_known_providers():
    from thoth.completion.sources import provider_names

    ctx, param = _make_ctx_param()
    out = provider_names(ctx, param, "")
    assert set(out) >= {"openai", "perplexity", "mock"}


def test_provider_names_filters_by_incomplete_prefix():
    from thoth.completion.sources import provider_names

    ctx, param = _make_ctx_param()
    out = provider_names(ctx, param, "open")
    assert "openai" in out
    assert "perplexity" not in out


def test_mode_kind_returns_immediate_and_background_choices():
    """P18 forward-compat — currently dead code per spec §6.4."""
    from thoth.completion.sources import mode_kind

    ctx, param = _make_ctx_param()
    out = mode_kind(ctx, param, "")
    assert set(out) >= {"immediate", "background"}
