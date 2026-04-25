from click.testing import CliRunner

from thoth.cli import cli


def test_pick_model_rejected_on_deep_research():
    r = CliRunner().invoke(cli, ["--pick-model", "deep_research", "some prompt"])
    assert r.exit_code != 0
    assert "only supported for quick" in r.output or "only supported for immediate" in r.output


def test_pick_model_rejected_on_exploration():
    r = CliRunner().invoke(cli, ["--pick-model", "exploration", "some prompt"])
    assert r.exit_code != 0


def test_pick_model_quick_mode_uses_picker(monkeypatch):
    picked = {}

    def fake_pick(models):
        picked["called"] = True
        return "gpt-4o-mini"

    monkeypatch.setattr("thoth.interactive_picker.pick_model", fake_pick)

    captured = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return 0

    monkeypatch.setattr("thoth.run.run_research", fake_run)

    r = CliRunner().invoke(cli, ["--pick-model", "default", "hello world"])
    assert r.exit_code == 0
    assert picked.get("called") is True
    assert captured.get("model_override") == "gpt-4o-mini"
