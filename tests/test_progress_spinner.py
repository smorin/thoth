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
