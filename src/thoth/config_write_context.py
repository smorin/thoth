"""Shared write-target context for config file mutations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from thoth.config import ConfigManager
from thoth.config_document import ConfigDocument
from thoth.config_profiles import ProfileLayer, collect_profile_catalog
from thoth.paths import user_config_file


class ConfigTargetConflictError(ValueError):
    """Raised when a write target is ambiguous by command options."""


@dataclass(frozen=True)
class ConfigWriteContext:
    """Resolved target and raw read context for config mutation commands.

    This class owns the write-target contract shared by config mutators:
    ``--project`` writes ``./thoth.config.toml``, ``--config PATH`` writes
    that path, and the default writes the user config file.
    """

    target_path: Path
    project: bool
    config_path: Path | None

    @classmethod
    def resolve(
        cls,
        *,
        project: bool,
        config_path: str | Path | None = None,
    ) -> ConfigWriteContext:
        normalized = Path(config_path).expanduser().resolve() if config_path else None
        if project and normalized is not None:
            raise ConfigTargetConflictError("--config cannot be used with --project")

        if project:
            target_path = Path.cwd() / "thoth.config.toml"
        elif normalized is not None:
            target_path = normalized
        else:
            target_path = user_config_file()

        return cls(target_path=target_path, project=project, config_path=normalized)

    def load_document(self) -> ConfigDocument:
        """Load the target document for mutation."""
        return ConfigDocument.load(self.target_path)

    def raw_profile_catalog(self) -> list[ProfileLayer]:
        """Collect profiles without resolving the currently selected profile."""
        manager = ConfigManager(self.config_path)
        user_raw = (
            manager._load_toml_file(manager.user_config_path)
            if manager.user_config_path.exists()
            else {}
        )
        project_raw, project_path = manager._load_project_config_with_path()
        return collect_profile_catalog(
            user_config=user_raw,
            project_config=project_raw,
            user_path=manager.user_config_path,
            project_path=project_path,
        )


__all__ = ["ConfigTargetConflictError", "ConfigWriteContext"]
