from click.testing import CliRunner

from thoth.cli import cli
from thoth.help import render_auth_help


def test_help_auth_lists_env_first():
    """P16 PR2 T8: `--help auth` shortcut removed; assert on render_auth_help()
    directly since it is retained for PR3's real auth subcommand."""
    out = render_auth_help()
    i_env = out.find("Environment variables")
    i_cfg = out.find("Config file")
    i_flag = out.find("CLI flags")
    assert 0 <= i_env < i_cfg < i_flag


def test_help_auth_marks_cli_flag_as_last_resort():
    out = render_auth_help()
    assert "not recommended" in out or "last resort" in out


def test_api_key_cli_flag_help_soft_warning():
    r = CliRunner().invoke(cli, ["--help"])
    assert "not recommended" in r.output


def test_help_auth_contains_toml_table_header():
    """P16 PR2 T8: assert on render_auth_help() directly (no `--help auth` shortcut)."""
    assert "[providers.openai]" in render_auth_help()
