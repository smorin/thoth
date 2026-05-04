"""Unit tests for thoth.providers._helpers."""

from __future__ import annotations


def test_invalid_key_thotherror_shape() -> None:
    """The shared helper produces a ThothError with exit_code=2 and a settings hint."""
    from thoth.errors import ThothError
    from thoth.providers._helpers import _invalid_key_thotherror

    err = _invalid_key_thotherror("perplexity", "https://www.perplexity.ai/settings/api")
    assert isinstance(err, ThothError)
    assert err.exit_code == 2
    assert "perplexity" in err.message.lower()
    assert err.suggestion is not None
    assert "https://www.perplexity.ai/settings/api" in err.suggestion


def test_invalid_key_thotherror_openai_url() -> None:
    """The helper composes correctly for the OpenAI call site too."""
    from thoth.errors import ThothError
    from thoth.providers._helpers import _invalid_key_thotherror

    err = _invalid_key_thotherror("openai", "https://platform.openai.com/account/api-keys")
    assert isinstance(err, ThothError)
    assert err.exit_code == 2
    assert "openai" in err.message.lower()
    assert err.suggestion is not None
    assert "https://platform.openai.com/account/api-keys" in err.suggestion
