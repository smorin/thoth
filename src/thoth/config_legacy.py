"""Legacy config filename detection and migration guidance for P21c."""

from __future__ import annotations

from pathlib import Path

from thoth.paths import user_config_dir

LEGACY_USER_FILENAME = "config.toml"
LEGACY_PROJECT_PATHS: tuple[str, ...] = ("./thoth.toml", "./.thoth/config.toml")


def detect_legacy_paths() -> list[Path]:
    """Return any legacy Thoth config files that exist on disk.

    These files are reported for migration guidance only; they are never loaded.
    """
    found: list[Path] = []
    legacy_user = user_config_dir() / LEGACY_USER_FILENAME
    if legacy_user.exists():
        found.append(legacy_user)
    for rel in LEGACY_PROJECT_PATHS:
        p = Path(rel)
        if p.exists():
            found.append(p)
    return found


def format_legacy_config_guidance(legacy_paths: list[Path] | None = None) -> str | None:
    """Return migration guidance for legacy config files, when any exist."""
    legacy = legacy_paths if legacy_paths is not None else detect_legacy_paths()
    if not legacy:
        return None

    lines: list[str] = []
    if len(legacy) == 1:
        lines.append(f"  Detected legacy file: {legacy[0]}")
    else:
        lines.append("  Detected legacy files:")
        for path in legacy:
            lines.append(f"    {path}")
    lines.append(
        "  These filenames are no longer read. Rename to "
        "thoth.config.toml (or .thoth.config.toml in the project root)."
    )
    return "\n".join(lines)


__all__ = [
    "LEGACY_PROJECT_PATHS",
    "LEGACY_USER_FILENAME",
    "detect_legacy_paths",
    "format_legacy_config_guidance",
]
