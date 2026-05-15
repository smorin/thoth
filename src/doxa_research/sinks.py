"""P18 Phase E: output sinks for immediate-mode streaming.

`MultiSink` fans `write(chunk)` to a list of text-mode IO handles. Files
are opened lazily on first write so an aborted submit doesn't leave empty
files lying around. `close()` is idempotent and never closes `sys.stdout`.

CLI surface (wired in `cli_subcommands/_options.py:_RESEARCH_OPTIONS`):

  --out -                stdout (default if no --out given)
  --out PATH             file (replaces stdout)
  --out -,PATH           comma-list — tee to both
  --out - --out PATH     repeatable form — same as comma-list
  --append               file opened in "a" mode instead of "w"

Spec §5.3 + §5.7.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import IO


class _LazyFileSink:
    """File-backed sink that opens the underlying file only on first write."""

    def __init__(self, path: Path, *, append: bool):
        self._path = path
        self._mode = "a" if append else "w"
        self._handle: IO[str] | None = None

    def write(self, chunk: str) -> None:
        if self._handle is None:
            self._handle = open(self._path, self._mode, encoding="utf-8")
        self._handle.write(chunk)
        self._handle.flush()

    def close(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None


class _StdoutSink:
    """stdout-backed sink. Never closes the underlying stream."""

    def write(self, chunk: str) -> None:
        sys.stdout.write(chunk)
        sys.stdout.flush()

    def close(self) -> None:
        # Intentionally a no-op — sys.stdout outlives any single sink.
        pass


class MultiSink:
    """Fans `write(chunk)` to a list of underlying sinks; idempotent close."""

    def __init__(self, sinks: list[_LazyFileSink | _StdoutSink]):
        self._sinks = sinks
        self._closed = False

    @classmethod
    def from_specs(cls, specs: list[str], *, append: bool = False) -> MultiSink:
        """Construct from a list of `--out` specs.

        Each spec is one of:
          * "-"           → stdout
          * "PATH"        → file
          * "X,Y,..."     → comma-separated list of either form (recursively split)

        Empty `specs` defaults to stdout (matches existing behavior when no
        `--out` is passed).
        """
        flat: list[str] = []
        for spec in specs:
            if "," in spec:
                flat.extend(s.strip() for s in spec.split(",") if s.strip())
            else:
                flat.append(spec)

        if not flat:
            flat = ["-"]

        sinks: list[_LazyFileSink | _StdoutSink] = []
        seen_paths: set[Path] = set()
        seen_stdout = False
        for entry in flat:
            if entry == "-":
                if not seen_stdout:
                    sinks.append(_StdoutSink())
                    seen_stdout = True
            else:
                p = Path(entry).expanduser()
                resolved = p.resolve() if p.exists() else p
                if resolved in seen_paths:
                    continue
                seen_paths.add(resolved)
                sinks.append(_LazyFileSink(p, append=append))
        return cls(sinks)

    def write(self, chunk: str) -> None:
        if self._closed:
            raise RuntimeError("MultiSink: write after close")
        for sink in self._sinks:
            sink.write(chunk)

    def close(self) -> None:
        if self._closed:
            return
        for sink in self._sinks:
            sink.close()
        self._closed = True

    def __enter__(self) -> MultiSink:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


__all__ = ["MultiSink"]
