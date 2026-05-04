"""Unit tests for thoth.providers._helpers."""

from __future__ import annotations


def test_invalid_key_thotherror_shape() -> None:
    """The shared helper produces a ThothError with exit_code=2 and a settings hint."""
    from thoth.errors import ThothError
    from thoth.providers._helpers import _invalid_key_thotherror

    err = _invalid_key_thotherror("Perplexity", "https://www.perplexity.ai/settings/api")
    assert isinstance(err, ThothError)
    assert err.exit_code == 2
    assert "Perplexity API key is invalid" in err.message
    assert err.suggestion is not None
    assert "Your Perplexity API key" in err.suggestion
    assert "https://www.perplexity.ai/settings/api" in err.suggestion


def test_invalid_key_thotherror_openai_url() -> None:
    """The helper composes correctly for the OpenAI call site too."""
    from thoth.errors import ThothError
    from thoth.providers._helpers import _invalid_key_thotherror

    err = _invalid_key_thotherror("OpenAI", "https://platform.openai.com/account/api-keys")
    assert isinstance(err, ThothError)
    assert err.exit_code == 2
    assert "OpenAI API key is invalid" in err.message
    assert err.suggestion is not None
    assert "Your OpenAI API key" in err.suggestion
    assert "https://platform.openai.com/account/api-keys" in err.suggestion


def test_extract_unsupported_param_finds_parameter_name() -> None:
    """The helper pulls the quoted parameter name from a BadRequestError message."""
    from thoth.providers._helpers import _extract_unsupported_param

    assert (
        _extract_unsupported_param("Unsupported parameter 'frequency_penalty' for sonar-pro.")
        == "frequency_penalty"
    )


def test_extract_unsupported_param_returns_none_when_marker_missing() -> None:
    """No 'unsupported parameter' marker -> None (don't false-match)."""
    from thoth.providers._helpers import _extract_unsupported_param

    assert _extract_unsupported_param("Some other 400 error") is None


def test_extract_unsupported_param_case_insensitive_marker() -> None:
    """Marker check is case-insensitive (upstream wording varies)."""
    from thoth.providers._helpers import _extract_unsupported_param

    assert _extract_unsupported_param("UNSUPPORTED PARAMETER 'temperature'") == "temperature"


def test_extract_unsupported_param_handles_colon_form() -> None:
    """OpenAI's wording uses 'Unsupported parameter:' — also recognized."""
    from thoth.providers._helpers import _extract_unsupported_param

    assert (
        _extract_unsupported_param("Unsupported parameter: 'temperature' for o3-deep-research")
        == "temperature"
    )
