from click.testing import CliRunner

from thoth.cli import cli


def test_pick_model_rejected_on_deep_research():
    r = CliRunner().invoke(cli, ["--pick-model", "deep_research", "some prompt"])
    assert r.exit_code != 0
    assert "only supported for quick" in r.output or "only supported for immediate" in r.output


def test_pick_model_rejected_on_exploration():
    r = CliRunner().invoke(cli, ["--pick-model", "exploration", "some prompt"])
    assert r.exit_code != 0
