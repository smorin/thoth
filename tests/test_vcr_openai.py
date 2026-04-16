"""VCR cassette replay tests for OpenAI provider."""

from __future__ import annotations

import asyncio

from tests.conftest import CASSETTE_DIR, thoth_vcr

OPENAI_CASSETTE = str(CASSETTE_DIR / "openai" / "happy-path.yaml")

# The prompt recorded in the cassette — must match for submit() to work,
# though VCR matching ignores bodies (match_on=["uri", "method"]).
CASSETTE_PROMPT = (
    "What are the three most significant recent breakthroughs"
    " in solid-state battery technology? Provide specific company"
    " names, dates, and technical details with citations."
)

# The response ID baked into the cassette.
CASSETTE_RESPONSE_ID = "resp_0c13a25ee1a48f780069df079e0a58819cbde29d8a2906c590"


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


def _make_provider():
    """Create an OpenAIProvider configured for deep-research cassette replay."""
    from thoth.__main__ import OpenAIProvider

    return OpenAIProvider(
        api_key="sk-replay-dummy",
        config={"model": "o4-mini-deep-research", "background": True},
    )


class TestOpenAISubmit:
    """Replay the happy-path cassette through OpenAIProvider.submit()."""

    @thoth_vcr.use_cassette(OPENAI_CASSETTE)
    def test_submit_returns_response_id(self):
        """submit() should return a response ID starting with 'resp_'."""
        provider = _make_provider()
        job_id = _run(provider.submit(prompt=CASSETTE_PROMPT, mode="deep-research"))
        assert job_id.startswith("resp_"), f"unexpected job_id: {job_id}"

    @thoth_vcr.use_cassette(OPENAI_CASSETTE)
    def test_submit_returns_expected_id(self):
        """submit() should return the exact ID from the cassette."""
        provider = _make_provider()
        job_id = _run(provider.submit(prompt=CASSETTE_PROMPT, mode="deep-research"))
        assert job_id == CASSETTE_RESPONSE_ID

    @thoth_vcr.use_cassette(OPENAI_CASSETTE)
    def test_submit_stores_job_info(self):
        """submit() should populate self.jobs with the job ID."""
        provider = _make_provider()
        job_id = _run(provider.submit(prompt=CASSETTE_PROMPT, mode="deep-research"))
        assert job_id in provider.jobs
        assert provider.jobs[job_id]["background"] is True


class TestOpenAIPolling:
    """Replay the full polling sequence to completion."""

    @thoth_vcr.use_cassette(OPENAI_CASSETTE)
    def test_first_status_is_in_progress_or_queued(self):
        """First check_status() after submit should be queued or in_progress."""
        provider = _make_provider()
        job_id = _run(provider.submit(prompt=CASSETTE_PROMPT, mode="deep-research"))
        status = _run(provider.check_status(job_id))
        assert status["status"] in ("queued", "running"), f"unexpected: {status}"

    @thoth_vcr.use_cassette(OPENAI_CASSETTE)
    def test_poll_to_completed(self):
        """Polling check_status() through the cassette should reach 'completed'."""
        provider = _make_provider()
        job_id = _run(provider.submit(prompt=CASSETTE_PROMPT, mode="deep-research"))

        final_status = None
        for _ in range(60):
            info = _run(provider.check_status(job_id))
            if info["status"] == "completed":
                final_status = info
                break
        assert final_status is not None, "never reached 'completed'"
        assert final_status["status"] == "completed"
        assert final_status["progress"] == 1.0


class TestOpenAIResult:
    """Verify get_result() returns substantial research output."""

    @thoth_vcr.use_cassette(OPENAI_CASSETTE)
    def test_get_result_returns_text(self):
        """After polling to completed, get_result() should return research text."""
        provider = _make_provider()
        job_id = _run(provider.submit(prompt=CASSETTE_PROMPT, mode="deep-research"))

        # Poll through all in_progress interactions to reach completed
        for _ in range(60):
            info = _run(provider.check_status(job_id))
            if info["status"] == "completed":
                break

        # get_result() will try another retrieve call; VCR raises CannotSendRequest
        # since the cassette is exhausted, but get_result() catches the exception
        # and falls back to the cached response from the last check_status() call.
        result = _run(provider.get_result(job_id))
        assert len(result) > 100, f"expected substantial output, got {len(result)} chars"

    @thoth_vcr.use_cassette(OPENAI_CASSETTE)
    def test_get_result_contains_research_content(self):
        """Result text should contain domain-relevant content from the cassette."""
        provider = _make_provider()
        job_id = _run(provider.submit(prompt=CASSETTE_PROMPT, mode="deep-research"))

        for _ in range(60):
            info = _run(provider.check_status(job_id))
            if info["status"] == "completed":
                break

        result = _run(provider.get_result(job_id))
        # The cassette output discusses solid-state batteries
        assert "solid" in result.lower() or "battery" in result.lower(), (
            "expected research content about batteries"
        )
