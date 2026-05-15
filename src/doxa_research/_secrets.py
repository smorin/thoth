"""Shared secret-masking helpers used by config_cmd and modes_cmd.

Rule: any dict key whose final dotted-path segment is `api_key` is masked —
the value is replaced with `****<last-four-chars>`. Env-template placeholders
like `${OPENAI_API_KEY}` pass through unchanged.
"""

from __future__ import annotations

from typing import Any

_SECRET_KEY_SUFFIX = "api_key"


def _is_secret_key(key: str) -> bool:
    return key.split(".")[-1] == _SECRET_KEY_SUFFIX


def _mask_secret(value: Any) -> Any:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        return value
    if value.startswith("${") and value.endswith("}"):
        return value
    tail = value[-4:] if len(value) >= 4 else value
    return f"****{tail}"


def _mask_tree(data: Any, prefix: str = "") -> Any:
    if isinstance(data, dict):
        return {k: _mask_tree(v, f"{prefix}.{k}" if prefix else k) for k, v in data.items()}
    if isinstance(data, list):
        return [_mask_tree(v, prefix) for v in data]
    if prefix and _is_secret_key(prefix):
        return _mask_secret(data)
    return data


__all__ = ["_is_secret_key", "_mask_secret", "_mask_tree"]
