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

    def get_mode(self, name: str, *, profile: str | None = None) -> dict[str, Any] | None:
        """Return the mode's TOML table as a plain dict, or None if absent
        in the chosen tier.

        Public read-only accessor used by CLI data functions to detect mode
        existence and inspect current values (e.g. for idempotency checks).
        Returns a snapshot dict — modifications do NOT propagate back to the
        document.
        """
        segments = self._mode_segments(name, profile)
        table = self._table_at(segments)
        if table is None:
            return None
        return dict(table)

    def set_mode_value(
        self, name: str, key: str, value: Any, *, profile: str | None = None
    ) -> None:
        """Set `[<tier>.modes.<NAME>.<KEY>]`. Dotted KEY creates nested tables."""
        prefix = self._mode_segments(name, profile)
        self._set_segments((*prefix, *_parse_config_key(key)), value)

    def unset_mode_value(
        self, name: str, key: str, *, profile: str | None = None
    ) -> tuple[bool, bool]:
        """Unset `[<tier>.modes.<NAME>.<KEY>]` with empty-table pruning.

        Returns (removed, table_pruned). `removed` is False when KEY was
        absent. `table_pruned` is True when removing KEY emptied the
        `[modes.<NAME>]` (or `[profiles.<X>.modes.<NAME>]`) table and that
        table was deleted as a result. Pruning is intentional divergence
        from `unset_profile_value` (B17) — empty mode tables are
        meaningless; users delete a whole mode via `remove_mode`.
        """
        prefix = self._mode_segments(name, profile)
        if self._table_at(prefix) is None:
            return False, False

        removed = self._unset_segments(
            (*prefix, *_parse_config_key(key)),
            prune_empty=True,
        )
        if not removed:
            return False, False

        # Did the prune cascade up and remove the mode table?
        table_pruned = self._table_at(prefix) is None
        return True, table_pruned

    def remove_mode(self, name: str, *, profile: str | None = None) -> bool:
        """Drop `[<tier>.modes.<NAME>]` entirely. Idempotent.

        Returns True when the table existed and was removed; False when it
        was already absent. Like `remove_profile`, leaves any sibling
        tables (and the parent `profiles.<X>.modes` table) intact.
        """
        prefix = self._mode_segments(name, profile)
        if self._table_at(prefix) is None:
            return False

        # Walk to the parent and delete the leaf key. parent_segments is
        # non-empty (prefix has length 2 or 4) and _table_at(prefix)
        # already succeeded above, so the parent must exist.
        parent_segments = prefix[:-1]
        leaf = prefix[-1]
        parent = self._table_at(parent_segments)
        assert parent is not None
        del parent[leaf]
        return True

    def rename_mode(self, old: str, new: str, *, profile: str | None = None) -> bool:
        """Rename `[<tier>.modes.<OLD>]` to `[<tier>.modes.<NEW>]`.

        Refuses (returns False) if OLD is absent or NEW already exists in
        the same tier. The CLI layer is responsible for translating the
        False return into MODE_NOT_FOUND vs DST_NAME_TAKEN by inspecting
        which side existed.

        Implementation note: tomlkit doesn't have an in-place rename for
        super-tables, so we copy the table contents to a new table and
        delete the old one. Inline-table comments survive; super-table
        comments may not.
        """
        old_prefix = self._mode_segments(old, profile)
        new_prefix = self._mode_segments(new, profile)
        old_table = self._table_at(old_prefix)
        if old_table is None:
            return False
        if self._table_at(new_prefix) is not None:
            return False

        # Materialise the new table and copy keys.
        new_table = self._ensure_table(new_prefix)
        for k in list(old_table.keys()):
            new_table[k] = old_table[k]

        # Delete the old leaf. parent_segments is non-empty (old_prefix
        # has length 2 or 4) and the parent table was just walked to find
        # old_table, so _table_at can't return None here.
        parent_segments = old_prefix[:-1]
        leaf = old_prefix[-1]
        parent = self._table_at(parent_segments)
        assert parent is not None
        del parent[leaf]
        return True

    def copy_mode(
        self,
        src: str,
        dst: str,
        *,
        from_profile: str | None = None,
        profile: str | None = None,
    ) -> bool:
        """Copy mode SRC → DST in raw tomlkit-table form (no layering).

        Direct table-to-table copy; does NOT layer with BUILTIN_MODES.
        Returns True on success, False if SRC is absent or DST exists.

        Note: the `thoth modes copy` CLI does NOT use this primitive —
        it iterates `effective.items()` and writes via `set_mode_value`
        per key in order to layer BUILTIN_MODES with any user override
        (see `get_modes_copy_data` in `modes_cmd.py`). This primitive
        is retained for any future use case that needs a non-layered
        raw copy (e.g., scripting, migration tools).
        """
        src_prefix = self._mode_segments(src, from_profile)
        dst_prefix = self._mode_segments(dst, profile)
        src_table = self._table_at(src_prefix)
        if src_table is None:
            return False
        if self._table_at(dst_prefix) is not None:
            return False

        new_table = self._ensure_table(dst_prefix)
        for k in list(src_table.keys()):
            new_table[k] = src_table[k]
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
