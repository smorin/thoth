"""P16 PR2 — Category C: Q5-A cleanup-batch tests."""

from __future__ import annotations

from click.testing import CliRunner

from thoth.cli import cli


def test_providers_models_refresh_and_no_cache_mutex():
    """Q5-A row 1: --refresh-cache and --no-cache are mutually exclusive."""
    r = CliRunner().invoke(cli, ["providers", "models", "--refresh-cache", "--no-cache"])
    assert r.exit_code == 2, r.output
    combined = r.output or ""
    assert "mutually exclusive" in combined.lower() or "cannot use" in combined.lower()


def test_modes_no_leaf_exits_2():
    """Q5-A row 5: bare `thoth modes` exits 2 (no leaf default)."""
    r = CliRunner().invoke(cli, ["modes"])
    assert r.exit_code == 2, r.output


def test_modes_list_name_and_source_intersect():
    """Q5-A row 11.i: --name X --source Y applies BOTH filters.

    A builtin mode (`deep_research`) requested with `--source user` should
    yield empty / no-match output (exit 0) — the source filter must NOT be
    dropped by the name short-circuit.
    """
    r = CliRunner().invoke(
        cli, ["modes", "list", "--name", "deep_research", "--source", "user", "--json"]
    )
    assert r.exit_code == 0, r.output
    # Detail render of the builtin deep_research must NOT appear when source=user.
    assert "Source: builtin" not in r.output
    # JSON form: mode key should be null (no match) per intersection semantics.
    import json as _json

    data = _json.loads(r.output)
    assert data.get("mode") is None, f"expected mode=None, got {data!r}"


def test_clarify_alone_rejected():
    """Q5-A row 7: --clarify without --interactive → exit 2."""
    r = CliRunner().invoke(cli, ["--clarify"])
    assert r.exit_code == 2, r.output
    combined = r.output or ""
    assert "--interactive" in combined or "interactive" in combined.lower()


def test_status_no_arg_exits_2():
    """Q5-A row 6: bare `thoth status` exits 2 (Click default for missing required arg)."""
    r = CliRunner().invoke(cli, ["status"])
    assert r.exit_code == 2, r.output


def test_config_get_invalid_layer_exits_2():
    """Q5-A row 8: `config get KEY --layer NOPE` exits 2 via Click choice validation."""
    r = CliRunner().invoke(cli, ["config", "get", "general.default_mode", "--layer", "NOPE"])
    assert r.exit_code == 2, r.output
    combined = r.output or ""
    assert "invalid value" in combined.lower() or "choose from" in combined.lower()


def test_providers_no_leaf_exits_2():
    """Q5-A row 4: bare `thoth providers` exits 2 (no-leaf default)."""
    r = CliRunner().invoke(cli, ["providers"])
    assert r.exit_code == 2, r.output
