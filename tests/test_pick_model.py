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


def test_pick_model_rejected_with_resume(monkeypatch):
    picked = {"called": False}

    def fake_pick(models):
        picked["called"] = True
        return "gpt-4o-mini"

    monkeypatch.setattr("thoth.interactive_picker.pick_model", fake_pick)
    r = CliRunner().invoke(cli, ["--pick-model", "resume", "op_test_123"])
    assert r.exit_code != 0
    assert "only applies to research runs" in r.output
    assert picked["called"] is False


def test_pick_model_rejected_with_interactive(monkeypatch):
    picked = {"called": False}

    def fake_pick(models):
        picked["called"] = True
        return "gpt-4o-mini"

    monkeypatch.setattr("thoth.interactive_picker.pick_model", fake_pick)
    r = CliRunner().invoke(cli, ["--pick-model", "-i"])
    assert r.exit_code != 0
    assert "only applies to research runs" in r.output
    assert picked["called"] is False


def test_pick_model_rejected_with_command(monkeypatch):
    picked = {"called": False}

    def fake_pick(models):
        picked["called"] = True
        return "gpt-4o-mini"

    monkeypatch.setattr("thoth.interactive_picker.pick_model", fake_pick)
    r = CliRunner().invoke(cli, ["--pick-model", "providers", "list"])
    assert r.exit_code != 0
    assert "only applies to research runs" in r.output
    assert picked["called"] is False


def test_pick_model_rejected_without_prompt(monkeypatch):
    picked = {"called": False}

    def fake_pick(models):
        picked["called"] = True
        return "gpt-4o-mini"

    monkeypatch.setattr("thoth.interactive_picker.pick_model", fake_pick)
    r = CliRunner().invoke(cli, ["--pick-model"])
    assert r.exit_code != 0
    assert picked["called"] is False


def test_pick_model_error_does_not_say_mode_none(monkeypatch):
    """BUG-07 verification: when --pick-model has no resolvable mode, the
    rejection must come from the combo guard, not the background-mode reject
    (which would print 'Mode None uses None')."""
    picked = {"called": False}

    def fake_pick(models):
        picked["called"] = True
        return "gpt-4o-mini"

    monkeypatch.setattr("thoth.interactive_picker.pick_model", fake_pick)

    for argv in (
        ["--pick-model"],
        ["--pick-model", "resume", "op_test_123"],
        ["--pick-model", "-i"],
        ["--pick-model", "providers", "list"],
    ):
        r = CliRunner().invoke(cli, argv)
        assert "Mode 'None'" not in r.output
        assert "uses None" not in r.output
