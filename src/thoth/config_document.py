"""TOML document mutation helpers for Thoth config files."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import tomlkit


class ConfigDocument:
    """Edit a single TOML config file while preserving TOMLKit formatting.

    This class owns file-level mutation rules only. Runtime config loading,
    layer precedence, profile resolution, and schema validation remain the
    responsibility of ``ConfigManager``.
    """

    def __init__(self, path: Path, document: tomlkit.TOMLDocument):
        self.path = path
        self._document = document

    @classmethod
    def load(cls, path: Path) -> ConfigDocument:
        if path.exists():
            return cls(path, tomlkit.parse(path.read_text()))

        document = tomlkit.document()
        document["version"] = "2.0"
        return cls(path, document)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(tomlkit.dumps(self._document))

    def set_config_value(self, key: str, value: Any) -> None:
        self._set_segments(_parse_config_key(key), value)

    def unset_config_value(self, key: str, *, prune_empty: bool = True) -> bool:
        return self._unset_segments(_parse_config_key(key), prune_empty=prune_empty)

    def ensure_profile(self, name: str) -> bool:
        if self._table_at(("profiles", name)) is not None:
            return False
        self._ensure_table(("profiles", name))
        return True

    def remove_profile(self, name: str) -> bool:
        profiles = self._table_at(("profiles",))
        if profiles is None or name not in profiles:
            return False
        profile = profiles[name]
        if not hasattr(profile, "keys"):
            return False
        del profiles[name]
        return True

    def set_profile_value(self, name: str, key: str, value: Any) -> None:
        self._set_segments(("profiles", name, *_parse_config_key(key)), value)

    def unset_profile_value(self, name: str, key: str) -> bool:
        return self._unset_segments(
            ("profiles", name, *_parse_config_key(key)),
            prune_empty=False,
        )

    def set_default_profile(self, name: str) -> None:
        self.set_config_value("general.default_profile", name)

    def unset_default_profile(self) -> bool:
        return self.unset_config_value("general.default_profile", prune_empty=False)

    def default_profile_name(self) -> str | None:
        general = self._table_at(("general",))
        if general is None or "default_profile" not in general:
            return None
        value = general["default_profile"]
        return value if isinstance(value, str) and value else None

    def unset_default_profile_if(self, name: str) -> bool:
        if self.default_profile_name() != name:
            return False
        return self.unset_default_profile()

    # ------------------------------------------------------------------
    # Mode primitives (P12) — base tier `[modes.<NAME>]` or overlay
    # tier `[profiles.<X>.modes.<NAME>]` when `profile` is set.
    # ------------------------------------------------------------------

    def _mode_segments(self, name: str, profile: str | None) -> tuple[str, ...]:
        if profile is not None:
            return ("profiles", profile, "modes", name)
        return ("modes", name)

    def ensure_mode(self, name: str, *, profile: str | None = None) -> bool:
        segments = self._mode_segments(name, profile)
        if self._table_at(segments) is not None:
            return False
        self._ensure_table(segments)
        return True

    def _table_at(self, segments: tuple[str, ...]) -> Any | None:
        current: Any = self._document
        for segment in segments:
            if segment not in current:
                return None
            child: Any = current[segment]
            if not hasattr(child, "keys"):
                return None
            current = cast(Any, child)
        return current

    def _ensure_table(self, segments: tuple[str, ...]) -> Any:
        current: Any = self._document
        for segment in segments:
            existing: Any = current[segment] if segment in current else None
            if existing is None or not hasattr(existing, "keys"):
                new_table = tomlkit.table()
                current[segment] = new_table
                current = cast(Any, new_table)
            else:
                current = cast(Any, existing)
        return current

    def _set_segments(self, segments: tuple[str, ...], value: Any) -> None:
        if not segments:
            raise ValueError("config path must contain at least one segment")
        parent = self._ensure_table(segments[:-1])
        parent[segments[-1]] = value

    def _unset_segments(self, segments: tuple[str, ...], *, prune_empty: bool) -> bool:
        if not segments:
            return False

        stack: list[Any] = [self._document]
        current: Any = self._document
        for segment in segments[:-1]:
            if segment not in current:
                return False
            child: Any = current[segment]
            if not hasattr(child, "keys"):
                return False
            current = cast(Any, child)
            stack.append(current)

        leaf = segments[-1]
        if leaf not in current:
            return False
        del current[leaf]

        if prune_empty:
            for container, segment in zip(
                reversed(stack[:-1]),
                reversed(segments[:-1]),
                strict=True,
            ):
                child = container[segment]
                if hasattr(child, "keys") and len(child) == 0:
                    del container[segment]
                else:
                    break

        return True


def _parse_config_key(key: str) -> tuple[str, ...]:
    return tuple(key.split("."))


__all__ = ["ConfigDocument"]
