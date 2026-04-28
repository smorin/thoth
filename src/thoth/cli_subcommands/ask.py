"""`thoth ask "PROMPT"` Click subcommand.

Per Q7-PR2-B accepts `nargs=-1` positional arguments joined with single spaces.
Per Q3-PR2-C duplicates the full research-options stack via `_research_options`,
so both `thoth ask --mode X "..."` and `thoth --mode X ask "..."` work.
"""

from __future__ import annotations

import click

from thoth.cli_subcommands._options import _research_options


@click.command(name="ask")
@click.argument("prompt_args", nargs=-1)
@_research_options
@click.pass_context
def ask(
    ctx: click.Context,
    prompt_args: tuple[str, ...],
    mode_opt: str | None,
    prompt_opt: str | None,
    prompt_file: str | None,
    async_mode: bool,
    project: str | None,
    output_dir: str | None,
    provider: str | None,
    input_file: str | None,
    auto: bool,
    verbose: bool,
    api_key_openai: str | None,
    api_key_perplexity: str | None,
    api_key_mock: str | None,
    config_path: str | None,
    combined: bool,
    quiet: bool,
    no_metadata: bool,
    timeout: float | None,
    interactive: bool,
    clarify: bool,
    pick_model: bool,
) -> None:
    """Run a research operation with the given prompt."""
    positional = " ".join(prompt_args) if prompt_args else None

    # Q7-B + Q3-C mutex: positional vs --prompt vs --prompt-file
    if positional and prompt_opt:
        raise click.BadParameter(
            "Cannot use --prompt with positional prompt argument", param_hint="--prompt"
        )
    if positional and prompt_file:
        raise click.BadParameter(
            "Cannot use --prompt-file with positional prompt argument",
            param_hint="--prompt-file",
        )
    if prompt_opt and prompt_file:
        raise click.BadParameter(
            "Cannot use --prompt-file with --prompt", param_hint="--prompt-file"
        )
    if not (positional or prompt_opt or prompt_file):
        raise click.BadParameter("Provide a prompt: positional, --prompt, or --prompt-file")

    # Q3-PR2-C: ask is the scripted research entry point. The interactive-only
    # flags --interactive / --clarify / --pick-model don't apply; reject them
    # with a clear error rather than silently dropping (least-surprise).
    if interactive:
        raise click.UsageError(
            "--interactive does not apply to 'thoth ask'; "
            "use 'thoth -i' (interactive mode) instead."
        )
    if clarify:
        raise click.UsageError(
            "--clarify does not apply to 'thoth ask'; "
            "use 'thoth --clarify' (interactive mode with clarification) instead."
        )
    if pick_model:
        raise click.UsageError(
            "--pick-model does not apply to 'thoth ask'; "
            "it requires interactive mode. Use 'thoth -i --pick-model' instead."
        )

    # Subcommand-level option wins over group-level (already true via Click)
    inherited = ctx.obj or {}

    def _pick(local, key: str):
        return local if local is not None else inherited.get(key)

    effective_mode = _pick(mode_opt, "mode_opt") or "default"
    effective_provider = _pick(provider, "provider")
    effective_project = _pick(project, "project")
    effective_output_dir = _pick(output_dir, "output_dir")
    effective_input_file = _pick(input_file, "input_file")
    effective_async = bool(async_mode or inherited.get("async_mode"))
    effective_auto = bool(auto or inherited.get("auto"))
    effective_verbose = bool(verbose or inherited.get("verbose"))
    effective_combined = bool(combined or inherited.get("combined"))
    effective_quiet = bool(quiet or inherited.get("quiet"))
    effective_no_metadata = bool(no_metadata or inherited.get("no_metadata"))
    effective_timeout = _pick(timeout, "timeout")
    effective_config = _pick(config_path, "config_path")
    cli_api_keys = {
        "openai": _pick(api_key_openai, "api_key_openai"),
        "perplexity": _pick(api_key_perplexity, "api_key_perplexity"),
        "mock": _pick(api_key_mock, "api_key_mock"),
    }

    # Local import: avoids cli.py → cli_subcommands → cli.py circular at module load.
    from thoth.cli import (
        _apply_config_path,
        _prompt_max_bytes,
        _read_prompt_input,
        _run_research_default,
    )

    _apply_config_path(effective_config)

    if prompt_file:
        effective_prompt = _read_prompt_input(str(prompt_file), _prompt_max_bytes())
    elif prompt_opt:
        effective_prompt = prompt_opt
    else:
        effective_prompt = positional or ""

    _run_research_default(
        mode=effective_mode,
        prompt=effective_prompt,
        async_mode=effective_async,
        project=effective_project,
        output_dir=effective_output_dir,
        provider=effective_provider,
        input_file=effective_input_file,
        auto=effective_auto,
        verbose=effective_verbose,
        cli_api_keys=cli_api_keys,
        combined=effective_combined,
        quiet=effective_quiet,
        no_metadata=effective_no_metadata,
        timeout_override=effective_timeout,
        model_override=None,
    )


__all__ = ["ask"]
