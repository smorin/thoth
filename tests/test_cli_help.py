from click.testing import CliRunner

from thoth.cli import cli


def _help() -> str:
    return CliRunner().invoke(cli, ["--help"]).output


def test_auto_help_mentions_happy_path():
    assert "happy path for chaining modes" in _help()


def test_input_file_help_mentions_advanced_usage():
    assert "non-thoth document" in _help()


def test_help_has_workflow_chain():
    out = _help()
    assert "Workflow chain" in out
    assert "clarification → exploration → deep_dive" in out


def test_help_has_resume_example():
    out = _help()
    assert "thoth --resume" in out


def test_help_has_verbose_example():
    out = _help()
    assert "Debug API issues" in out
    assert "-v" in out


def test_help_has_async_chain_example():
    out = _help()
    assert "thoth deep_research --auto" in out
    assert "--async" in out
