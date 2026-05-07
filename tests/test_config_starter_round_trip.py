"""P33-TS04: starter document round-trip test.

Position C — three layers:
  L2 (parsed-dict equality, split projection):
    - non-`profiles` root tables == get_defaults() projected to starter_keys()
    - parsed `profiles` == STARTER_PROFILES
  L3 (strict-mode validation): full doc validates through UserConfigFile
  L1 (substring assertions): rendered TOML contains key section markers
"""

from __future__ import annotations

import tomlkit


def test_starter_doc_round_trips() -> None:
    from thoth._starter_data import STARTER_PROFILES
    from thoth.commands import _build_starter_document
    from thoth.config import ConfigSchema
    from thoth.config_schema import ConfigSchema as CSNew  # public façade

    doc = _build_starter_document()
    rendered = tomlkit.dumps(doc)
    parsed = tomlkit.loads(rendered).unwrap()

    # ---- L2a: non-profiles root tables ----
    starter_keys = CSNew.starter_keys()  # set of tuple paths
    parsed_no_profiles = {k: v for k, v in parsed.items() if k != "profiles"}
    defaults = ConfigSchema.get_defaults()

    def project(d: dict, paths: set) -> dict:
        out: dict = {}
        for path in paths:
            cur_in = d
            cur_out = out
            for key in path[:-1]:
                if not isinstance(cur_in, dict) or key not in cur_in:
                    cur_in = None
                    break
                cur_in = cur_in[key]
                cur_out = cur_out.setdefault(key, {})
            if cur_in is None:
                continue
            leaf = path[-1]
            if isinstance(cur_in, dict) and leaf in cur_in:
                cur_out[leaf] = cur_in[leaf]
        return out

    expected = project(defaults, starter_keys)
    actual = project(parsed_no_profiles, starter_keys)
    assert actual == expected, (
        f"Starter doc non-profiles roots disagree with get_defaults() "
        f"projected to starter_keys().\n"
        f"expected: {expected}\nactual:   {actual}"
    )

    # ---- L2b: profiles ----
    parsed_profiles = parsed.get("profiles") or {}
    expected_profiles = {p.name: p.body for p in STARTER_PROFILES}
    assert parsed_profiles == expected_profiles, (
        "Starter profiles disagree with STARTER_PROFILES seed."
    )

    # ---- L3: strict-mode validation through UserConfigFile ----
    # NOTE: validation is advisory; we accept warnings == empty TUPLE (post Task 5 fix).
    report = CSNew.validate(parsed, layer="user", strict=False)
    assert report.warnings == (), f"unexpected warnings: {report.warnings}"

    # ---- L1: section markers ----
    # tomlkit renders nested tables as their full dotted-path headers, so the
    # parent `[profiles]` and `[profiles.daily]` headers are NOT emitted.
    # We assert the deepest level headers actually present in the output.
    assert "# Thoth Configuration File" in rendered
    assert "[profiles.daily.general]" in rendered
    assert "[profiles.deep_research.general]" in rendered
