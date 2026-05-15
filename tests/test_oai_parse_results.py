"""OpenAI result-parsing tests — migrated from doxa_test OAI-PARSE-01…08."""

from __future__ import annotations

import asyncio
import logging
import types
from pathlib import Path
from typing import Any

import pytest

from doxa_research.providers.openai import OpenAIProvider
from tests._fixture_helpers import make_mock_openai_result_response


@pytest.fixture(autouse=True)
def _isolate_config(isolated_doxa_home: Path) -> Path:
    return isolated_doxa_home


def test_sources_section_present_when_annotations_exist() -> None:
    """OAI-PARSE-01: ## Sources section present when annotations exist."""
    provider = OpenAIProvider(api_key="dummy")
    response = make_mock_openai_result_response(
        text="Research content.",
        annotations=[{"url": "https://example.com", "title": "Example Source"}],
    )
    provider.jobs["job-1"] = {"background": False, "response": response}
    result = asyncio.run(provider.get_result("job-1"))
    assert "## Sources" in result, f"expected ## Sources section, got: {result!r}"


def test_citation_url_and_title_preserved() -> None:
    """OAI-PARSE-02: citation url and title preserved verbatim in Sources section."""
    provider = OpenAIProvider(api_key="dummy")
    response = make_mock_openai_result_response(
        text="Report body.",
        annotations=[{"url": "https://papers.org/123", "title": "Key Paper"}],
    )
    provider.jobs["job-1"] = {"background": False, "response": response}
    result = asyncio.run(provider.get_result("job-1"))
    assert "https://papers.org/123" in result, f"citation url missing: {result!r}"
    assert "Key Paper" in result, f"citation title missing: {result!r}"


def test_reasoning_summary_extracts_text_not_repr() -> None:
    """OAI-PARSE-03: reasoning summary extracts .text from summary objects (not str(obj))."""
    provider = OpenAIProvider(api_key="dummy")
    response = make_mock_openai_result_response(
        text="Report body.",
        reasoning_summary=["Planning research approach", "Evaluating sources"],
    )
    provider.jobs["job-1"] = {"background": False, "response": response}
    result = asyncio.run(provider.get_result("job-1"))
    assert "Planning research approach" in result, f"reasoning text missing: {result!r}"
    assert "namespace(text=" not in result.lower(), f"object repr leaked into result: {result!r}"


def test_duplicate_citations_are_deduplicated() -> None:
    """OAI-PARSE-04: duplicate citation URLs are deduplicated in Sources section."""
    provider = OpenAIProvider(api_key="dummy")
    response = make_mock_openai_result_response(
        text="Report with repeated references.",
        annotations=[
            {"url": "https://dup.com", "title": "Dup Source"},
            {"url": "https://dup.com", "title": "Dup Source"},
            {"url": "https://other.com", "title": "Other Source"},
        ],
    )
    provider.jobs["job-1"] = {"background": False, "response": response}
    result = asyncio.run(provider.get_result("job-1"))
    assert result.count("https://dup.com") == 1, (
        f"duplicate url should appear once, got: {result!r}"
    )


def test_empty_response_has_clean_output() -> None:
    """OAI-PARSE-05: response with no content returns clean string, no [Debug] prefix."""
    provider = OpenAIProvider(api_key="dummy")
    provider.jobs["job-1"] = {"background": False, "response": types.SimpleNamespace()}
    result = asyncio.run(provider.get_result("job-1"))
    assert not result.startswith("[Debug]"), f"debug dump leaked into result: {result!r}"
    assert "No content" in result, f"unexpected result: {result!r}"


def test_no_annotations_means_no_sources_section() -> None:
    """OAI-PARSE-06: no annotations means no ## Sources section in output."""
    provider = OpenAIProvider(api_key="dummy")
    response = make_mock_openai_result_response(text="Clean report, no sources.")
    provider.jobs["job-1"] = {"background": False, "response": response}
    result = asyncio.run(provider.get_result("job-1"))
    assert "## Sources" not in result, f"unexpected Sources section: {result!r}"


def test_verbose_empty_response_is_clean() -> None:
    """OAI-PARSE-07: verbose=True with no content response — result string is clean."""
    provider = OpenAIProvider(api_key="dummy")
    provider.jobs["job-1"] = {"background": False, "response": types.SimpleNamespace()}
    result = asyncio.run(provider.get_result("job-1", verbose=True))
    assert not result.startswith("[Debug]"), f"debug dump in result with verbose: {result!r}"


def test_commentary_excluded_when_final_answer_present() -> None:
    """OAI-PARSE-08: commentary message is excluded when final_answer phase exists."""
    from openai.types.responses.response import Response

    provider = OpenAIProvider(api_key="dummy")
    response = Response.model_validate(
        {
            "id": "resp_456",
            "object": "response",
            "created_at": 1,
            "model": "o3-deep-research",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "id": "msg_commentary",
                    "status": "completed",
                    "role": "assistant",
                    "phase": "commentary",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "Thinking aloud",
                            "annotations": [
                                {
                                    "type": "url_citation",
                                    "url": "https://commentary.example",
                                    "title": "Commentary Source",
                                    "start_index": 0,
                                    "end_index": 8,
                                }
                            ],
                        }
                    ],
                },
                {
                    "type": "message",
                    "id": "msg_final",
                    "status": "completed",
                    "role": "assistant",
                    "phase": "final_answer",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "Actual final answer",
                            "annotations": [
                                {
                                    "type": "url_citation",
                                    "url": "https://final.example",
                                    "title": "Final Source",
                                    "start_index": 0,
                                    "end_index": 6,
                                }
                            ],
                        }
                    ],
                },
            ],
            "tools": [],
            "tool_choice": "auto",
            "parallel_tool_calls": False,
        }
    )
    provider.jobs["job-1"] = {"background": False, "response": response}
    result = asyncio.run(provider.get_result("job-1"))
    assert "Actual final answer" in result, f"final answer missing: {result!r}"
    assert "Thinking aloud" not in result, f"commentary leaked into result: {result!r}"
    assert "https://final.example" in result, f"final citation missing: {result!r}"
    assert "https://commentary.example" not in result, (
        f"commentary citation leaked into result: {result!r}"
    )


def _response_with_annotations(annotations: list[Any]) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        output=[
            types.SimpleNamespace(
                type="message",
                status="completed",
                phase="final_answer",
                content=[
                    types.SimpleNamespace(
                        type="output_text",
                        text="Report body.",
                        annotations=annotations,
                    )
                ],
            )
        ]
    )


def test_get_result_skips_typed_non_url_annotation_even_with_url(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Known non-url annotation types are skipped and logged."""
    caplog.set_level(logging.WARNING, logger="doxa_research.providers.openai")
    provider = OpenAIProvider(api_key="dummy")
    response = _response_with_annotations(
        [
            {
                "type": "file_citation",
                "url": "https://should-not-render.example",
                "title": "File citation",
            }
        ]
    )
    provider.jobs["job-1"] = {"background": False, "response": response}

    result = asyncio.run(provider.get_result("job-1"))

    assert "Report body." in result
    assert "## Sources" not in result
    assert "https://should-not-render.example" not in result
    assert "file_citation" in caplog.text
    assert "https://should-not-render.example" in caplog.text


def test_get_result_accepts_missing_type_url_annotation_with_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Legacy annotations with url/title but no type still render and warn."""
    caplog.set_level(logging.WARNING, logger="doxa_research.providers.openai")
    provider = OpenAIProvider(api_key="dummy")
    response = _response_with_annotations(
        [{"url": "https://legacy.example", "title": "Legacy Source"}]
    )
    provider.jobs["job-1"] = {"background": False, "response": response}

    result = asyncio.run(provider.get_result("job-1"))

    assert "## Sources" in result
    assert "https://legacy.example" in result
    assert "Legacy Source" in result
    assert "missing" in caplog.text.lower()
    assert "https://legacy.example" in caplog.text
