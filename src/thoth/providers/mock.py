"""Mock research provider for testing and development."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from thoth.providers.base import ResearchProvider
from thoth.utils import generate_operation_id


class MockProvider(ResearchProvider):
    """Mock provider for testing and development.

    Behavior is controlled by the THOTH_MOCK_BEHAVIOR env var:
      - unset / "default": normal completion after ``delay`` seconds
      - "flake:N": return ``transient_error`` N times, then complete
      - "permanent": return ``permanent_error`` on first poll
    """

    def __init__(self, name: str = "mock", delay: float = 0.1, api_key: str = ""):
        self.name = name
        self.delay = delay
        self.api_key = api_key
        self.model = "None"  # Mock provider has no model
        self.jobs: dict[str, dict[str, Any]] = {}
        self._behavior = os.getenv("THOTH_MOCK_BEHAVIOR", "default")

    async def submit(
        self, prompt: str, mode: str, system_prompt: str | None = None, verbose: bool = False
    ) -> str:
        """Submit mock research and return job ID"""
        job_id = f"mock-{generate_operation_id()}"
        self.jobs[job_id] = {
            "prompt": prompt,
            "mode": mode,
            "status": "running",
            "progress": 0.0,
            "start_time": asyncio.get_event_loop().time(),
            "transient_count": 0,
        }
        return job_id

    async def reconnect(self, job_id: str) -> None:
        """Re-attach to an existing mock job (for resume tests)."""
        # Honor updated THOTH_MOCK_BEHAVIOR from the resume process environment.
        self._behavior = os.getenv("THOTH_MOCK_BEHAVIOR", "default")
        self.jobs[job_id] = {
            "prompt": "",
            "mode": "",
            "status": "running",
            "progress": 0.0,
            "start_time": asyncio.get_event_loop().time(),
            "transient_count": 0,
        }

    async def check_status(self, job_id: str) -> dict[str, Any]:
        """Check mock job status"""
        if job_id not in self.jobs:
            return {"status": "not_found", "error": "Job not found"}

        job = self.jobs[job_id]

        if self._behavior == "permanent":
            return {
                "status": "permanent_error",
                "error": "Mock permanent failure",
                "error_class": "MockPermanentError",
            }
        if self._behavior.startswith("flake:"):
            try:
                limit = int(self._behavior.split(":", 1)[1])
            except ValueError:
                limit = 0
            if job["transient_count"] < limit:
                job["transient_count"] += 1
                return {
                    "status": "transient_error",
                    "error": f"Mock transient failure #{job['transient_count']}",
                    "error_class": "MockTransientError",
                }

        elapsed = asyncio.get_event_loop().time() - job["start_time"]

        if elapsed >= self.delay:
            job["status"] = "completed"
            job["progress"] = 1.0
        else:
            job["progress"] = min(elapsed / self.delay, 0.99)

        return {
            "status": job["status"],
            "progress": job["progress"],
            "elapsed": elapsed,
        }

    async def get_result(self, job_id: str, verbose: bool = False) -> str:
        """Get mock result"""
        if job_id not in self.jobs:
            raise ValueError("Job not found")

        job = self.jobs[job_id]
        return f"""# {self.name.title()} Research Results

## Prompt: {job["prompt"]}
## Mode: {job["mode"]}

This is a mock research result from the {self.name} provider.

### Key Findings
1. This is a simulated finding
2. Another mock insight
3. Test data point

### Conclusion
This mock provider successfully completed the research task.
"""

    def supports_progress(self) -> bool:
        return True

    async def list_models(self) -> list[dict[str, Any]]:
        """Return mock models for testing"""
        return [
            {"id": "mock-model-v1", "created": 1680000000, "owned_by": "mock"},
            {"id": "mock-model-v2", "created": 1690000000, "owned_by": "mock"},
        ]
