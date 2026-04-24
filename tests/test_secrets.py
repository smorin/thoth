"""Tests for the shared secret-masking helpers."""

from __future__ import annotations

from thoth._secrets import _is_secret_key, _mask_secret, _mask_tree


def test_mask_secret_preserves_last_four() -> None:
    assert _mask_secret("sk-verysecretverysecret1234") == "****1234"


def test_mask_secret_short_value() -> None:
    # Less than 4 chars — fall back to showing the whole tail (which equals
    # the whole value); this is the pre-P11 behaviour, preserved verbatim.
    assert _mask_secret("abc") == "****abc"


def test_mask_secret_empty_string_passes_through() -> None:
    assert _mask_secret("") == ""


def test_mask_secret_none_passes_through() -> None:
    assert _mask_secret(None) is None


def test_mask_secret_env_template_passes_through() -> None:
    assert _mask_secret("${OPENAI_API_KEY}") == "${OPENAI_API_KEY}"


def test_is_secret_key_matches_bare_api_key() -> None:
    assert _is_secret_key("api_key") is True


def test_is_secret_key_matches_dotted_path_ending_in_api_key() -> None:
    assert _is_secret_key("providers.openai.api_key") is True


def test_is_secret_key_rejects_unrelated_key() -> None:
    assert _is_secret_key("providers.openai.timeout") is False


def test_is_secret_key_only_matches_final_segment() -> None:
    # Middle-of-path "api_key" does not match — only the final segment counts.
    assert _is_secret_key("api_key.something") is False


def test_mask_tree_masks_nested_api_key() -> None:
    data = {"providers": {"openai": {"api_key": "sk-secret-value-1234", "timeout": 30}}}
    masked = _mask_tree(data)
    assert masked["providers"]["openai"]["api_key"] == "****1234"
    assert masked["providers"]["openai"]["timeout"] == 30


def test_mask_tree_leaves_non_secret_fields() -> None:
    data = {"name": "default", "description": "a mode"}
    assert _mask_tree(data) == data


def test_mask_tree_recurses_into_lists() -> None:
    data = {"items": [{"api_key": "sk-secret-xxxx1234"}, {"timeout": 30}]}
    masked = _mask_tree(data)
    assert masked["items"][0]["api_key"] == "****1234"
    assert masked["items"][1]["timeout"] == 30


def test_mask_tree_preserves_env_template() -> None:
    data = {"api_key": "${OPENAI_API_KEY}"}
    assert _mask_tree(data) == {"api_key": "${OPENAI_API_KEY}"}
