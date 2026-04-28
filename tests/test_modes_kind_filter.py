"""P18 Phase D: `thoth modes --kind <immediate|background>` filter.

The filter applies to both the JSON envelope path (`get_modes_list_data`) and
the Rich-rendering CLI path. Tab-completion uses the dead-code `mode_kind`
completer in `completion/sources.py:79` (left as P18 forward-compat by PR3).

Spec §10 acceptance: `thoth modes --kind immediate` filters; tab-complete
returns `["immediate", "background"]`.
"""

from __future__ import annotations

from click.testing import CliRunner

from thoth.cli import cli
from thoth.completion.sources import mode_kind as mode_kind_completer
from thoth.modes_cmd import get_modes_list_data


def test_get_modes_list_data_filters_immediate() -> None:
    data = get_modes_list_data(name=None, source="all", show_secrets=False, kind="immediate")
    assert data["modes"], "expected at least one immediate mode"
    assert all(m["kind"] == "immediate" for m in data["modes"])


def test_get_modes_list_data_filters_background() -> None:
    data = get_modes_list_data(name=None, source="all", show_secrets=False, kind="background")
    assert data["modes"], "expected at least one background mode"
    assert all(m["kind"] == "background" for m in data["modes"])


def test_get_modes_list_data_no_filter_returns_all() -> None:
    data = get_modes_list_data(name=None, source="all", show_secrets=False)
    kinds = {m["kind"] for m in data["modes"]}
    assert "immediate" in kinds
    assert "background" in kinds


def test_modes_list_cli_with_kind_immediate() -> None:
    """`thoth modes list --kind immediate --json` returns only immediate modes."""
    r = CliRunner().invoke(cli, ["modes", "list", "--kind", "immediate", "--json"])
    assert r.exit_code == 0, r.output
    import json

    payload = json.loads(r.output)
    modes = payload["data"]["modes"]
    assert modes
    assert all(m["kind"] == "immediate" for m in modes)


def test_modes_list_cli_invalid_kind_value_exits_2() -> None:
    r = CliRunner().invoke(cli, ["modes", "list", "--kind", "fast"])
    assert r.exit_code == 2, r.output


def test_mode_kind_completer_offers_both_values() -> None:
    """The dead-code completer in completion/sources.py:79 is now wired."""
    candidates = mode_kind_completer(None, None, "")
    assert "immediate" in candidates
    assert "background" in candidates


def test_mode_kind_completer_filters_by_prefix() -> None:
    candidates = mode_kind_completer(None, None, "im")
    assert candidates == ["immediate"]
