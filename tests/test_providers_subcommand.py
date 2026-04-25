from click.testing import CliRunner

from thoth.cli import cli


def test_providers_list_exits_zero():
    r = CliRunner().invoke(cli, ["providers", "list"])
    assert r.exit_code == 0
    assert "openai" in r.output.lower()


def test_providers_models_exits_zero():
    r = CliRunner().invoke(cli, ["providers", "models"])
    assert r.exit_code == 0


def test_providers_check_returns_status():
    r = CliRunner().invoke(cli, ["providers", "check"])
    # 0 if all keys present, 2 if any missing — both are valid clean exits.
    assert r.exit_code in (0, 2)


def test_old_form_deprecated_but_works():
    r = CliRunner().invoke(cli, ["providers", "--", "--list"])
    assert r.exit_code == 0
    assert "deprecated" in r.output.lower()
    assert "openai" in r.output.lower()
