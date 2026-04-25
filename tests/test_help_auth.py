from click.testing import CliRunner

from thoth.cli import cli


def test_help_auth_lists_env_first():
    r = CliRunner().invoke(cli, ["--help", "auth"])
    assert r.exit_code == 0
    out = r.output
    i_env = out.find("Environment variables")
    i_cfg = out.find("Config file")
    i_flag = out.find("CLI flags")
    assert 0 <= i_env < i_cfg < i_flag


def test_help_auth_marks_cli_flag_as_last_resort():
    r = CliRunner().invoke(cli, ["--help", "auth"])
    assert "not recommended" in r.output or "last resort" in r.output


def test_api_key_cli_flag_help_soft_warning():
    r = CliRunner().invoke(cli, ["--help"])
    assert "not recommended" in r.output


def test_help_auth_contains_toml_table_header():
    r = CliRunner().invoke(cli, ["--help", "auth"])
    assert "[providers.openai]" in r.output
