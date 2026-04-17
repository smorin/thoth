"""Research-output file management.

OutputManager generates unique output paths, writes results atomically
(tmp + rename), and can assemble a combined multi-provider report.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import aiofiles

from thoth.config import ConfigManager
from thoth.errors import DiskSpaceError
from thoth.models import OperationStatus
from thoth.utils import check_disk_space, sanitize_slug


class OutputManager:
    """Manages research output files"""

    def __init__(self, config: ConfigManager, no_metadata: bool = False):
        self.config = config
        self.base_output_dir = Path(config.data["paths"]["base_output_dir"])
        self.format = config.data["output"]["format"]
        self.no_metadata = no_metadata

    def get_output_path(
        self,
        operation: OperationStatus,
        provider: str,
        output_dir: str | None = None,
    ) -> Path:
        """Generate output path based on mode"""
        timestamp = operation.created_at.strftime(self.config.data["output"]["timestamp_format"])
        slug = sanitize_slug(operation.prompt)

        # Determine output directory
        if output_dir:
            # Explicit override - takes precedence over everything
            base_dir = Path(output_dir)
        elif operation.project:
            # Project mode
            base_dir = self.base_output_dir / operation.project
        else:
            # Ad-hoc mode - current directory
            base_dir = Path.cwd()

        # Ensure directory exists
        base_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with provider
        ext = "md" if self.format == "markdown" else "json"
        if provider == "combined":
            # Special case for combined reports: <timestamp>_<mode>_combined_<slug>.md
            base_name = f"{timestamp}_{operation.mode}_combined_{slug}"
        else:
            base_name = f"{timestamp}_{operation.mode}_{provider}_{slug}"
        filename = f"{base_name}.{ext}"

        # Handle deduplication
        output_path = base_dir / filename
        counter = 1
        while output_path.exists():
            filename = f"{base_name}-{counter}.{ext}"
            output_path = base_dir / filename
            counter += 1

        return output_path

    async def save_result(
        self,
        operation: OperationStatus,
        provider: str,
        content: str,
        output_dir: str | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
    ) -> Path:
        """Save research result to file"""
        output_path = self.get_output_path(operation, provider, output_dir)

        # Check disk space before writing
        if not check_disk_space(output_path.parent, 10):  # 10MB minimum
            raise DiskSpaceError("Insufficient disk space to save results")

        if (
            self.format == "markdown"
            and self.config.data["output"]["include_metadata"]
            and not self.no_metadata
        ):
            # Add metadata header
            metadata = f"""---
prompt: {operation.prompt}
mode: {operation.mode}
provider: {provider}
model: {model if model else "Unknown"}
operation_id: {operation.id}
created_at: {operation.created_at.isoformat()}
"""
            if operation.input_files:
                metadata += "input_files:\n"
                for f in operation.input_files:
                    metadata += f"  - {f}\n"
            metadata += "---\n\n"

            # Add prompt section
            metadata += "### Prompt\n\n```\n"
            if system_prompt:
                metadata += f"System: {system_prompt}\n\nUser: {operation.prompt}\n"
            else:
                metadata += operation.prompt + "\n"
            metadata += "```\n\n"

            content = metadata + content

        # Atomic write: stage to sibling .tmp file, then rename.
        # Ctrl-C mid-write leaves only the tmp file; the final path is never truncated.
        tmp_path = output_path.with_name(output_path.name + ".tmp")
        try:
            async with aiofiles.open(tmp_path, "w", encoding="utf-8") as f:
                await f.write(content)
            os.replace(tmp_path, output_path)
        except BaseException:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            raise

        return output_path

    async def generate_combined_report(
        self,
        operation: OperationStatus,
        contents: dict[str, str],
        output_dir: str | None = None,
        system_prompt: str | None = None,
    ) -> Path:
        """Generate a combined report from multiple provider results"""
        # Create synthesized content
        combined_content = f"# Combined Research Report: {operation.prompt}\n\n"
        combined_content += f"Generated: {datetime.now().isoformat()}\n\n"

        for provider, content in contents.items():
            combined_content += f"\n## {provider.title()} Results\n\n"
            combined_content += content
            combined_content += "\n\n---\n\n"

        # Save combined report
        return await self.save_result(
            operation,
            "combined",
            combined_content,
            output_dir,
            model="Multiple",
            system_prompt=system_prompt,
        )
