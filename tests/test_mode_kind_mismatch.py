"""P18 Phase B: runtime mismatch detection at provider.submit().

A mode declared `kind = "immediate"` cannot use a deep-research model — those
models REQUIRE OpenAI's background submission flow. The check fires at the
top of `OpenAIProvider.submit()`, BEFORE any HTTP call, so users see a
config-edit suggestion instead of a confusing API error.

The reverse case (declared `background` + non-deep-research model) is LEGAL —
OpenAI lets you force-background any model via `background=True`. Not checked.

See spec §5.6 + §4 Q1.
"""

from __future__ import annotations

import asyncio

import pytest

from thoth.errors import ModeKindMismatchError, ThothError
from thoth.providers.openai import OpenAIProvider


@pytest.fixture
def fake_openai_key(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake-not-real")
    return "sk-test-fake-not-real"


def _provider(*, model: str, kind: str | None) -> OpenAIProvider:
    """Construct an OpenAIProvider with the given (model, kind) combo.

    No HTTP client is exercised — we never call the real submit network path,
    only the validation gate which fires before any HTTP work.
    """
    config: dict = {"model": model}
    if kind is not None:
        config["kind"] = kind
    return OpenAIProvider(api_key="sk-test-fake-not-real", config=config)


def test_immediate_with_o3_deep_research_raises(fake_openai_key: str) -> None:
    p = _provider(model="o3-deep-research", kind="immediate")
    with pytest.raises(ModeKindMismatchError) as exc:
        asyncio.run(p.submit("hello", mode="thinking"))
    assert exc.value.declared_kind == "immediate"
    assert exc.value.required_kind == "background"
    assert exc.value.model == "o3-deep-research"
    assert exc.value.mode_name == "thinking"


def test_immediate_with_o4_mini_deep_research_raises(fake_openai_key: str) -> None:
    p = _provider(model="o4-mini-deep-research", kind="immediate")
    with pytest.raises(ModeKindMismatchError):
        asyncio.run(p.submit("hello", mode="thinking"))


def test_background_with_regular_model_does_not_raise(
    fake_openai_key: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Force-background on a non-deep-research model is legal — must not raise."""
    p = _provider(model="o3", kind="background")

    # Make sure the validation gate accepts this combo. We replace the inner
    # retry method so submit() doesn't actually hit OpenAI; the validation
    # check runs first and we just need to confirm it doesn't raise.
    async def fake_submit(*args, **kwargs):  # type: ignore[no-untyped-def]
        return "fake-job-id"

    monkeypatch.setattr(p, "_submit_with_retry", fake_submit)
    job_id = asyncio.run(p.submit("hello", mode="deep_research"))
    assert job_id == "fake-job-id"


def test_immediate_with_regular_model_does_not_raise(
    fake_openai_key: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The happy case — immediate mode with a regular model."""
    p = _provider(model="o3", kind="immediate")

    async def fake_submit(*args, **kwargs):  # type: ignore[no-untyped-def]
        return "fake-job-id"

    monkeypatch.setattr(p, "_submit_with_retry", fake_submit)
    job_id = asyncio.run(p.submit("hello", mode="thinking"))
    assert job_id == "fake-job-id"


def test_no_kind_declared_does_not_raise(
    fake_openai_key: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pre-P18 callers (no `kind` threaded through) must keep working — backwards compat."""
    p = _provider(model="o3", kind=None)

    async def fake_submit(*args, **kwargs):  # type: ignore[no-untyped-def]
        return "fake-job-id"

    monkeypatch.setattr(p, "_submit_with_retry", fake_submit)
    job_id = asyncio.run(p.submit("hello", mode="default"))
    assert job_id == "fake-job-id"


def test_error_carries_user_facing_suggestion(fake_openai_key: str) -> None:
    p = _provider(model="o3-deep-research", kind="immediate")
    with pytest.raises(ModeKindMismatchError) as exc:
        asyncio.run(p.submit("hello", mode="thinking"))
    err = exc.value
    assert "thinking" in err.message
    assert "o3-deep-research" in err.message
    assert err.suggestion is not None
    assert "[modes.thinking]" in err.suggestion
    assert "kind" in err.suggestion


def test_error_subclasses_thotherror(fake_openai_key: str) -> None:
    p = _provider(model="o3-deep-research", kind="immediate")
    with pytest.raises(ThothError):
        asyncio.run(p.submit("hello", mode="thinking"))
