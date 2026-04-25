from contextlib import contextmanager

import pytest

from thoth.progress import should_show_spinner


class FakeTTY:
    def isatty(self):
        return True


class FakePipe:
    def isatty(self):
        return False


@pytest.mark.parametrize(
    "model,async_mode,verbose,stream,expected",
    [
        ("o3-deep-research", False, False, FakeTTY(), True),
        ("o3-deep-research", True, False, FakeTTY(), False),  # async
        ("o3-deep-research", False, True, FakeTTY(), False),  # -v
        ("o3-deep-research", False, False, FakePipe(), False),  # piped
        ("o3", False, False, FakeTTY(), False),  # immediate
        (None, False, False, FakeTTY(), False),
    ],
)
def test_gate(model, async_mode, verbose, stream, expected):
    assert (
        should_show_spinner(model=model, async_mode=async_mode, verbose=verbose, stream=stream)
        is expected
    )


def test_maybe_spinner_calls_spinner_when_gate_passes(monkeypatch):
    called = {"entered": False}

    @contextmanager
    def fake_spinner(label, expected_minutes=20):
        called["entered"] = True
        yield

    monkeypatch.setattr("thoth.run.run_with_spinner", fake_spinner)
    monkeypatch.setattr("thoth.run.should_show_spinner", lambda **kw: True)

    from thoth.run import _maybe_spinner

    with _maybe_spinner(
        model="o3-deep-research",
        async_mode=False,
        verbose=False,
        label="Deep research running",
    ):
        pass
    assert called["entered"] is True


def test_maybe_spinner_is_noop_when_gate_fails(monkeypatch):
    called = {"entered": False}

    @contextmanager
    def fake_spinner(label, expected_minutes=20):
        called["entered"] = True
        yield

    monkeypatch.setattr("thoth.run.run_with_spinner", fake_spinner)
    monkeypatch.setattr("thoth.run.should_show_spinner", lambda **kw: False)

    from thoth.run import _maybe_spinner

    with _maybe_spinner(
        model="o3",
        async_mode=False,
        verbose=False,
        label="x",
    ):
        pass
    assert called["entered"] is False
