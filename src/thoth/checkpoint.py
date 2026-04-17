"""Operation state persistence with corruption recovery.

CheckpointManager writes per-operation JSON files atomically (tmp + replace)
and recovers gracefully if a checkpoint file is corrupted on load.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import aiofiles
from rich.console import Console

from thoth.config import ConfigManager
from thoth.models import OperationStatus

_console = Console()


class CheckpointManager:
    """Handles operation persistence with corruption recovery"""

    def __init__(self, config: ConfigManager):
        self.checkpoint_dir = Path(config.data["paths"]["checkpoint_dir"])
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, operation: OperationStatus) -> None:
        """Save operation state atomically"""
        checkpoint_file = self.checkpoint_dir / f"{operation.id}.json"
        temp_file = checkpoint_file.with_suffix(".tmp")

        data = asdict(operation)
        # Convert datetime and Path objects to strings
        data["created_at"] = operation.created_at.isoformat()
        data["updated_at"] = operation.updated_at.isoformat()
        data["output_paths"] = {k: str(v) for k, v in operation.output_paths.items()}
        data["input_files"] = [str(p) for p in operation.input_files]

        async with aiofiles.open(temp_file, "w") as f:
            await f.write(json.dumps(data, indent=2))

        temp_file.replace(checkpoint_file)

    async def load(self, operation_id: str) -> OperationStatus | None:
        """Load operation from checkpoint with corruption handling"""
        checkpoint_file = self.checkpoint_dir / f"{operation_id}.json"

        if not checkpoint_file.exists():
            return None

        try:
            async with aiofiles.open(checkpoint_file) as f:
                data = json.loads(await f.read())

            # Convert back to proper types
            data["created_at"] = datetime.fromisoformat(data["created_at"])
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
            data["output_paths"] = {k: Path(v) for k, v in data["output_paths"].items()}
            data["input_files"] = [Path(p) for p in data.get("input_files", [])]
            # failure_type is new; default to None for checkpoints written before this field
            data.setdefault("failure_type", None)

            return OperationStatus(**data)
        except (json.JSONDecodeError, KeyError, ValueError):
            _console.print(
                f"[yellow]Warning:[/yellow] Checkpoint file corrupted: {checkpoint_file}"
            )
            _console.print("[yellow]Creating new checkpoint. Previous state lost.[/yellow]")
            # Remove corrupted file
            checkpoint_file.unlink()
            return None

    def trigger_checkpoint(self, event: str) -> bool:
        """Determine if checkpoint should be saved based on event"""
        checkpoint_events = [
            "operation_start",
            "provider_start",
            "provider_complete",
            "provider_fail",
            "operation_complete",
            "operation_fail",
        ]
        return event in checkpoint_events
