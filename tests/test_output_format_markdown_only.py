"""Standardization #7: `output.format` is markdown-only.

The previous schema allowed `output.format = "markdown" | "json"`, but
the "json" branch was only half-implemented — it changed the file
extension from `.md` to `.json` and skipped the YAML frontmatter, but
the file content was still raw markdown text from the LLM. A `.json`
file containing markdown is worse than nothing.

Users who want JSON output for scripting should use the `--json` flag
on individual commands, which emits operation metadata as a JSON
envelope (see docs/json-output.md). That's a different feature with a
real schema.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from doxa_research.config_schema import OutputConfig


def test_output_config_accepts_markdown() -> None:
    """The supported value still validates cleanly."""
    cfg = OutputConfig(format="markdown")
    assert cfg.format == "markdown"


def test_output_config_rejects_json_with_clear_error() -> None:
    """`output.format = "json"` must raise — the feature was broken and
    is removed in favor of the per-command --json envelope flag.
    """
    # Use dynamic kwargs so the static type checker doesn't flag the
    # intentionally-invalid literal before pydantic gets to validate it.
    bad_config: dict[str, Any] = {"format": "json"}
    with pytest.raises(ValidationError) as exc_info:
        OutputConfig(**bad_config)
    msg = str(exc_info.value).lower()
    assert "format" in msg
    assert "json" in msg


def test_output_config_rejects_other_arbitrary_values() -> None:
    """Schema is locked to a single literal."""
    bad_config: dict[str, Any] = {"format": "xml"}
    with pytest.raises(ValidationError):
        OutputConfig(**bad_config)


def test_output_manager_only_produces_md_files(tmp_path) -> None:
    """End-to-end: file extension is always `.md`. No more silent `.json`
    files containing markdown content.
    """
    from doxa_research.config import ConfigManager
    from doxa_research.output import OutputManager
    from tests.conftest import make_operation

    cm = ConfigManager()
    cm.load_all_layers({})
    cm.data["paths"]["base_output_dir"] = str(tmp_path)
    om = OutputManager(cm)
    operation = make_operation("research-md-only")

    path = om.get_output_path(operation, "mock")
    assert path.suffix == ".md", f"Expected .md extension, got {path.suffix}"
