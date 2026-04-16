"""Shared VCR configuration for cassette replay tests."""

from __future__ import annotations

from pathlib import Path

import vcr

CASSETTE_DIR = Path(__file__).resolve().parent.parent / "thoth_test_cassettes"

# Shared VCR instance:
# - record_mode="none": never make real HTTP requests
# - match_on=["uri", "method"]: ignore body differences between SDK-generated
#   requests (structured input_messages) and cassette bodies (plain strings)
thoth_vcr = vcr.VCR(
    record_mode="none",
    match_on=["uri", "method"],
)
