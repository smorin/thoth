"""P18 Phase E: MultiSink — fans write(chunk) to a list of IO[str] handles.

Lazy file open (don't truncate before first chunk arrives), ordered close
in finally, supports stdout + file + tee + append.
"""

from __future__ import annotations

import sys
from pathlib import Path

from thoth.sinks import MultiSink


def test_stdout_only(capsys) -> None:
    sink = MultiSink.from_specs(["-"])
    sink.write("hello ")
    sink.write("world")
    sink.close()
    captured = capsys.readouterr()
    assert captured.out == "hello world"


def test_file_only_truncates_by_default(tmp_path: Path) -> None:
    target = tmp_path / "out.md"
    target.write_text("PRE-EXISTING")
    sink = MultiSink.from_specs([str(target)])
    sink.write("fresh content")
    sink.close()
    assert target.read_text() == "fresh content"


def test_file_appends_when_requested(tmp_path: Path) -> None:
    target = tmp_path / "out.md"
    target.write_text("EXISTING\n")
    sink = MultiSink.from_specs([str(target)], append=True)
    sink.write("appended")
    sink.close()
    assert target.read_text() == "EXISTING\nappended"


def test_tee_to_stdout_and_file(tmp_path: Path, capsys) -> None:
    target = tmp_path / "tee.md"
    sink = MultiSink.from_specs(["-", str(target)])
    sink.write("teed")
    sink.close()
    assert target.read_text() == "teed"
    assert capsys.readouterr().out == "teed"


def test_comma_list_parsing(tmp_path: Path, capsys) -> None:
    target = tmp_path / "comma.md"
    sink = MultiSink.from_specs([f"-,{target}"])
    sink.write("via-comma")
    sink.close()
    assert target.read_text() == "via-comma"
    assert capsys.readouterr().out == "via-comma"


def test_file_opened_lazily(tmp_path: Path) -> None:
    """If we never write, the file is never opened — no empty file left behind."""
    target = tmp_path / "lazy.md"
    sink = MultiSink.from_specs([str(target)])
    sink.close()  # no writes
    assert not target.exists()


def test_close_is_idempotent(tmp_path: Path) -> None:
    target = tmp_path / "idem.md"
    sink = MultiSink.from_specs([str(target)])
    sink.write("once")
    sink.close()
    sink.close()  # second close must not raise
    assert target.read_text() == "once"


def test_default_when_no_specs_is_stdout(capsys) -> None:
    sink = MultiSink.from_specs([])  # empty list = stdout
    sink.write("default")
    sink.close()
    assert capsys.readouterr().out == "default"


def test_does_not_close_stdout(tmp_path: Path) -> None:
    """Even after close, sys.stdout must remain usable."""
    sink = MultiSink.from_specs(["-"])
    sink.write("a")
    sink.close()
    # If we accidentally closed sys.stdout, this would raise ValueError.
    sys.stdout.write("")  # no exception means stdout still open
