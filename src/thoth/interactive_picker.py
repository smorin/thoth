"""Interactive model picker — only used for immediate (non-background) modes."""

from __future__ import annotations


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


def immediate_models_for_provider(provider: str) -> list[str]:
    """Return known immediate (non-background) models for the provider."""
    from thoth.config import BUILTIN_MODES, is_background_model

    seen: set[str] = set()
    for cfg in BUILTIN_MODES.values():
        raw = cfg.get("model")
        model_str: str | None = raw if isinstance(raw, str) else None
        if cfg.get("provider") == provider and not is_background_model(model_str):
            if model_str is not None:
                seen.add(model_str)
    if provider == "openai":
        seen.update({"o3", "gpt-4o-mini", "gpt-4o"})
    return sorted(seen)
