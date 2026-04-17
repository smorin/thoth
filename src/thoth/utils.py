"""General-purpose utility functions used throughout Thoth."""

from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4


def generate_operation_id() -> str:
    """Generate unique operation ID with 16-char UUID suffix"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    unique_suffix = str(uuid4()).replace("-", "")[:16]  # 16 chars for better uniqueness
    return f"research-{timestamp}-{unique_suffix}"


def sanitize_slug(text: str, max_length: int = 50) -> str:
    """Convert text to filename-safe slug"""
    # Keep alphanumeric and spaces, replace spaces with hyphens
    slug = re.sub(r"[^a-zA-Z0-9\s-]", "", text)
    slug = re.sub(r"\s+", "-", slug.strip())
    return slug[:max_length].lower()


def mask_api_key(key: str) -> str:
    """Mask API key for display"""
    if not key or len(key) < 8:
        return "***"
    return f"{key[:3]}...{key[-3:]}"


def check_disk_space(path: Path, required_mb: int = 100) -> bool:
    """Check if sufficient disk space is available"""
    stat = shutil.disk_usage(path)
    available_mb = stat.free / (1024 * 1024)
    return available_mb >= required_mb


def _is_placeholder(value: str) -> bool:
    """Unresolved ${VAR} substitution from ConfigManager should count as missing."""
    return value.startswith("${") and value.endswith("}")
