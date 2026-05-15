"""Unit tests for doxa_research.providers._helpers."""

from __future__ import annotations

from types import SimpleNamespace


def test_invalid_key_doxaerror_shape() -> None:
    """The shared helper produces a DoxaError with exit_code=2 and a settings hint."""
    from doxa_research.errors import DoxaError
    from doxa_research.providers._helpers import _invalid_key_doxaerror

    err = _invalid_key_doxaerror("Perplexity", "https://www.perplexity.ai/settings/api")
    assert isinstance(err, DoxaError)
    assert err.exit_code == 2
    assert "Perplexity API key is invalid" in err.message
    assert err.suggestion is not None
    assert "Your Perplexity API key" in err.suggestion
    assert "https://www.perplexity.ai/settings/api" in err.suggestion


def test_invalid_key_doxaerror_openai_url() -> None:
    """The helper composes correctly for the OpenAI call site too."""
    from doxa_research.errors import DoxaError
    from doxa_research.providers._helpers import _invalid_key_doxaerror

    err = _invalid_key_doxaerror("OpenAI", "https://platform.openai.com/account/api-keys")
    assert isinstance(err, DoxaError)
    assert err.exit_code == 2
    assert "OpenAI API key is invalid" in err.message
    assert err.suggestion is not None
    assert "Your OpenAI API key" in err.suggestion
    assert "https://platform.openai.com/account/api-keys" in err.suggestion


def test_extract_unsupported_param_finds_parameter_name() -> None:
    """The helper pulls the quoted parameter name from a BadRequestError message."""
    from doxa_research.providers._helpers import _extract_unsupported_param

    assert (
        _extract_unsupported_param("Unsupported parameter 'frequency_penalty' for sonar-pro.")
        == "frequency_penalty"
    )


def test_extract_unsupported_param_returns_none_when_marker_missing() -> None:
    """No 'unsupported parameter' marker -> None (don't false-match)."""
    from doxa_research.providers._helpers import _extract_unsupported_param

    assert _extract_unsupported_param("Some other 400 error") is None


def test_extract_unsupported_param_case_insensitive_marker() -> None:
    """Marker check is case-insensitive (upstream wording varies)."""
    from doxa_research.providers._helpers import _extract_unsupported_param

    assert _extract_unsupported_param("UNSUPPORTED PARAMETER 'temperature'") == "temperature"


def test_extract_unsupported_param_handles_colon_form() -> None:
    """OpenAI's wording uses 'Unsupported parameter:' — also recognized."""
    from doxa_research.providers._helpers import _extract_unsupported_param

    assert (
        _extract_unsupported_param("Unsupported parameter: 'temperature' for o3-deep-research")
        == "temperature"
    )


def test_render_sources_block_empty_input_returns_empty_string() -> None:
    """Shared sources renderer returns cleanly empty output for no citations."""
    from doxa_research.providers._helpers import render_sources_block

    assert render_sources_block([]) == ""


def test_render_sources_block_dedupes_by_url_first_title_wins() -> None:
    """Duplicate source URLs render once; the first title is preserved."""
    from doxa_research.providers._helpers import render_sources_block
    from doxa_research.providers.base import Citation

    rendered = render_sources_block(
        [
            Citation(title="First title", url="https://example.com/a"),
            Citation(title="Second title", url="https://example.com/a"),
            Citation(title="Other title", url="https://example.com/b"),
        ]
    )

    assert rendered.startswith("## Sources")
    assert rendered.count("https://example.com/a") == 1
    assert "First title" in rendered
    assert "Second title" not in rendered
    assert "Other title" in rendered


def test_render_sources_block_sanitizes_title_and_url() -> None:
    """Shared sources renderer applies the markdown link safety helpers."""
    from doxa_research.providers._helpers import render_sources_block
    from doxa_research.providers.base import Citation

    rendered = render_sources_block(
        [Citation(title="<script>alert(1)</script>", url="javascript:alert(1)")]
    )

    assert "<script>" not in rendered
    assert "javascript:" not in rendered


def test_debug_print_empty_response_labels_provider_and_truncates(capsys) -> None:
    """Shared debug helper labels the provider and caps large response dumps."""
    from doxa_research.providers._helpers import debug_print_empty_response

    response = SimpleNamespace(payload="x" * 5000)
    debug_print_empty_response(response, provider_label="Gemini")

    captured = capsys.readouterr()
    assert "Gemini" in captured.err
    assert "no content" in captured.err.lower()
    assert len(captured.err) < 1400
