"""P33: seed data for `thoth init` starter content.

Frozen verbatim from pre-P33 `_build_starter_profiles()`. Reviewing the
*selection* of profiles is deferred to P37; this module owns the *content*.

Each entry is a `StarterProfile(name, body)` where `body` is a nested mapping
that matches `ProfileConfig`. The order of entries in `STARTER_PROFILES` is
the order they appear under `[profiles.*]` in the rendered TOML.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StarterProfile:
    name: str
    body: dict[str, Any]


STARTER_PROFILES: list[StarterProfile] = [
    StarterProfile(
        name="daily",
        body={
            "general": {
                "default_mode": "thinking",
                "default_project": "daily-notes",
            },
        },
    ),
    StarterProfile(
        name="quick",
        body={"general": {"default_mode": "thinking"}},
    ),
    StarterProfile(
        name="openai_deep",
        body={
            "general": {"default_mode": "deep_research"},
            "modes": {"deep_research": {"providers": ["openai"], "parallel": False}},
        },
    ),
    StarterProfile(
        name="all_deep",
        body={
            "general": {"default_mode": "deep_research"},
            "modes": {
                "deep_research": {"providers": ["openai", "perplexity"], "parallel": True},
            },
        },
    ),
    StarterProfile(
        name="interactive",
        body={"general": {"default_mode": "interactive"}},
    ),
    StarterProfile(
        name="deep_research",
        body={
            "general": {
                "default_mode": "deep_research",
                "prompt_prefix": "Be thorough. Cite primary sources where possible.",
            },
            "modes": {
                "deep_research": {
                    "providers": ["openai", "perplexity"],
                    "parallel": True,
                    "prompt_prefix": (
                        "Be thorough. Cite primary sources. Include counter-arguments."
                    ),
                },
            },
        },
    ),
]
