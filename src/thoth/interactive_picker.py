"""Interactive model picker — only used for immediate (non-background) modes."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from thoth.config import ConfigManager


def pick_model(models: list[str]) -> str:
    """Show a numbered picker and return the selected model string.

    Tests monkeypatch this function directly so the picker UI is never
    actually shown during pytest runs.
    """
    import click

    if not models:
        raise RuntimeError("No models available to pick from")
    click.echo("Available immediate-mode models:")
    for i, m in enumerate(models, start=1):
        click.echo(f"  {i}. {m}")
    idx = click.prompt("Pick a model", type=click.IntRange(1, len(models)))
    return models[idx - 1]


def immediate_models_for_provider(provider: str, config: ConfigManager) -> list[str]:
    """Return immediate (non-background) models for `provider` from merged config.

    Walks `config.data["modes"]` (merged BUILTIN + user overlay), so user-defined
    modes in `[modes.*]` are surfaced. No provider-specific hardcoded extras —
    the picker reflects what is actually configured.

    P18: each mode dict carries `kind`; we filter on declared kind first
    (canonical), falling back to substring sniff via `mode_kind` for legacy
    user modes that haven't migrated.
    """
    from thoth.config import mode_kind

    seen: set[str] = set()
    for cfg in config.data.get("modes", {}).values():
        if not isinstance(cfg, dict):
            continue
        if cfg.get("provider") != provider:
            continue
        model = cfg.get("model")
        if isinstance(model, str) and mode_kind(cfg) == "immediate":
            seen.add(model)
    return sorted(seen)
