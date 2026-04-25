from click.testing import CliRunner

from thoth.cli import cli


def _help() -> str:
    return CliRunner().invoke(cli, ["--help"]).output


def test_auto_help_mentions_happy_path():
    assert "happy path for chaining modes" in _help()


def test_input_file_help_mentions_advanced_usage():
    assert "non-thoth document" in _help()
