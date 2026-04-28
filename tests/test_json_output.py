"""Envelope-contract tests for `thoth.json_output`.

Per spec §6.1 + §8.3, every `--json` command's output MUST satisfy:
1. Output parses as JSON (json.loads doesn't raise)
2. Top-level is a dict
3. Has "status" key with value "ok" or "error"
4. If "ok": has "data" key (dict)
5. If "error": has "error" key with "code" (str) and "message" (str);
   optionally "details" (dict)

This file tests the envelope-emitter functions in isolation. The
parametrized per-command contract test lives in test_json_envelopes.py.
"""

from __future__ import annotations

import json

import pytest


def test_emit_json_writes_success_envelope_and_exits_zero(capsys):
    from thoth.json_output import emit_json

    with pytest.raises(SystemExit) as excinfo:
        emit_json({"foo": 1, "bar": "baz"})

    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload == {"status": "ok", "data": {"foo": 1, "bar": "baz"}}


def test_emit_error_writes_error_envelope_with_default_exit_code_one(capsys):
    from thoth.json_output import emit_error

    with pytest.raises(SystemExit) as excinfo:
        emit_error("CODE", "human message", {"detail_key": 42})

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload == {
        "status": "error",
        "error": {
            "code": "CODE",
            "message": "human message",
            "details": {"detail_key": 42},
        },
    }


def test_emit_error_omits_details_when_none(capsys):
    from thoth.json_output import emit_error

    with pytest.raises(SystemExit):
        emit_error("CODE", "msg")

    payload = json.loads(capsys.readouterr().out)
    assert "details" not in payload["error"]


def test_emit_error_honors_exit_code_override(capsys):
    from thoth.json_output import emit_error

    with pytest.raises(SystemExit) as excinfo:
        emit_error("CODE", "msg", exit_code=2)

    assert excinfo.value.code == 2


def test_emit_json_honors_exit_code_override(capsys):
    from thoth.json_output import emit_json

    with pytest.raises(SystemExit) as excinfo:
        emit_json({"x": 1}, exit_code=130)

    assert excinfo.value.code == 130
