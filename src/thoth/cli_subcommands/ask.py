"""`thoth ask "PROMPT"` Click subcommand.

Per Q7-PR2-B accepts `nargs=-1` positional arguments joined with single spaces.
Per Q3-PR2-C duplicates the full research-options stack via `_research_options`,
so both `thoth ask --mode X "..."` and `thoth --mode X ask "..."` work.
"""

from __future__ import annotations

import click

from thoth.cli_subcommands._option_policy import (
    DEFAULT_HONOR,
    inherited_api_keys,
    inherited_value,
    pick_value,
    validate_inherited_options,
)
from thoth.cli_subcommands._options import _research_options

_ASK_HONOR = DEFAULT_HONOR | {
    "mode_opt",
    "prompt_opt",
    "prompt_file",
    "async_mode",
    "project",
    "output_dir",
    "provider",
    "input_file",
    "auto",
    "verbose",
    "api_key_openai",
    "api_key_perplexity",
    "api_key_mock",
    "combined",
    "quiet",
    "no_metadata",
    "timeout",
    "out",
    "append",
    "cancel_on_interrupt",
}


@click.command(name="ask")
@click.argument("prompt_args", nargs=-1)
@_research_options
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
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
    profile: str | None,
    combined: bool,
    quiet: bool,
    no_metadata: bool,
    timeout: float | None,
    out: tuple[str, ...],
    append: bool,
    interactive: bool,
    clarify: bool,
    pick_model: bool,
    cancel_on_interrupt: bool | None,
    no_validate: bool,
    as_json: bool,
) -> None:
    """Run a research operation with the given prompt."""
    validate_inherited_options(ctx, "ask", _ASK_HONOR)

    positional = " ".join(prompt_args) if prompt_args else None
    inherited_prompt_opt = inherited_value(ctx, "prompt_opt")
    inherited_prompt_file = inherited_value(ctx, "prompt_file")
    effective_prompt_opt = prompt_opt if prompt_opt is not None else inherited_prompt_opt
    effective_prompt_file = prompt_file if prompt_file is not None else inherited_prompt_file

    # Q7-B + Q3-C mutex: positional vs --prompt vs --prompt-file
    if positional and effective_prompt_opt:
        raise click.BadParameter(
            "Cannot use --prompt with positional prompt argument", param_hint="--prompt"
        )
    if positional and effective_prompt_file:
        raise click.BadParameter(
            "Cannot use --prompt-file with positional prompt argument",
            param_hint="--prompt-file",
        )
    if effective_prompt_opt and effective_prompt_file:
        raise click.BadParameter(
            "Cannot use --prompt-file with --prompt", param_hint="--prompt-file"
        )
    if not (positional or effective_prompt_opt or effective_prompt_file):
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

    effective_provider = pick_value(provider, ctx, "provider")
    effective_output_dir = pick_value(output_dir, ctx, "output_dir")
    effective_input_file = pick_value(input_file, ctx, "input_file")
    effective_async = bool(async_mode or inherited.get("async_mode"))
    effective_auto = bool(auto or inherited.get("auto"))
    effective_verbose = bool(verbose or inherited.get("verbose"))
    effective_combined = bool(combined or inherited.get("combined"))
    effective_quiet = bool(quiet or inherited.get("quiet"))
    effective_no_metadata = bool(no_metadata or inherited.get("no_metadata"))
    effective_timeout = pick_value(timeout, ctx, "timeout")
    effective_config = pick_value(config_path, ctx, "config_path")
    effective_profile = pick_value(profile, ctx, "profile")
    effective_cancel_on_interrupt = pick_value(cancel_on_interrupt, ctx, "cancel_on_interrupt")
    effective_no_validate = bool(no_validate or inherited.get("no_validate"))
    root_api_keys = inherited_api_keys(ctx)
    cli_api_keys = {
        "openai": api_key_openai or root_api_keys["openai"],
        "perplexity": api_key_perplexity or root_api_keys["perplexity"],
        "mock": api_key_mock or root_api_keys["mock"],
    }

    # Local import: avoids cli.py → cli_subcommands → cli.py circular at module load.
    from thoth.cli import (
        _apply_config_path,
        _apply_no_validate,
        _config_default_mode,
        _config_default_project,
        _prompt_max_bytes_from_config,
        _read_prompt_input,
        _run_research_default,
    )
    from thoth.config import get_config

    def _prepare_request() -> tuple[str, str | None, str]:
        _apply_config_path(effective_config)
        _apply_no_validate(effective_no_validate)
        config = get_config(profile=effective_profile)
        selected_mode = pick_value(mode_opt, ctx, "mode_opt") or _config_default_mode(config)
        selected_project = pick_value(project, ctx, "project")
        if selected_project is None:
            selected_project = _config_default_project(config)

        if effective_prompt_file:
            selected_prompt = _read_prompt_input(
                str(effective_prompt_file),
                _prompt_max_bytes_from_config(config),
            )
        elif effective_prompt_opt:
            selected_prompt = effective_prompt_opt
        else:
            selected_prompt = positional or ""
        return selected_mode, selected_project, selected_prompt

    if as_json:
        # Option E (spec §6.7, §8.4): background mode → submit envelope;
        # immediate → run synchronously and emit snapshot from latest checkpoint.
        # We invoke `_run_research_default` via a stdout redirect because it
        # writes Rich progress/log lines even with `quiet=True`. Only the
        # final `emit_json` reaches the real stdout so the envelope parses.
        # Post-hoc operation_id lookup via the checkpoint store is a known
        # scope-minimization choice (T13 plan); a future PR could refactor
        # `_run_research_default` to RETURN the operation_id directly.
        import contextlib
        import io

        from thoth.completion.sources import operation_ids
        from thoth.config import BUILTIN_MODES, mode_kind
        from thoth.errors import ThothError
        from thoth.json_output import (
            emit_error,
            emit_json,
            emit_thoth_error,
            run_json_thoth_boundary,
        )
        from thoth.run import get_resume_snapshot_data

        effective_mode, effective_project, effective_prompt = run_json_thoth_boundary(
            _prepare_request
        )
        mode_config = BUILTIN_MODES.get(effective_mode, {})
        # P18: resolution-path migration — `mode_kind(cfg) == "background"`
        # replaces the legacy `is_background_mode(cfg)` substring branch.
        is_bg = mode_kind(mode_config) == "background" if mode_config else False
        force_async = is_bg or effective_async

        sink = io.StringIO()
        try:
            with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                _run_research_default(
                    mode=effective_mode,
                    prompt=effective_prompt,
                    async_mode=force_async,
                    project=effective_project,
                    output_dir=effective_output_dir,
                    provider=effective_provider,
                    input_file=effective_input_file,
                    auto=effective_auto,
                    verbose=False,
                    cli_api_keys=cli_api_keys,
                    combined=effective_combined,
                    quiet=True,
                    no_metadata=effective_no_metadata,
                    timeout_override=effective_timeout,
                    model_override=None,
                    profile=effective_profile,
                    cancel_on_interrupt=effective_cancel_on_interrupt,
                    as_json=True,
                )
        except SystemExit as exc:
            if exc.code not in (None, 0):
                emit_error(
                    "PROVIDER_FAILURE",
                    "ask --json failed",
                    {"exit_code": exc.code},
                    exit_code=1,
                )
        except ThothError as exc:
            emit_thoth_error(exc)
        except Exception as exc:  # noqa: BLE001 — wrap any provider error in envelope
            emit_error(
                "PROVIDER_FAILURE",
                str(exc) or "ask --json failed",
                {"exception": type(exc).__name__},
                exit_code=1,
            )

        ids = operation_ids(None, None, "")
        op_id = ids[-1] if ids else None

        if force_async:
            emit_json(
                {
                    "operation_id": op_id,
                    "status": "submitted",
                    "mode": effective_mode,
                    "provider": effective_provider,
                }
            )
        else:
            data = get_resume_snapshot_data(op_id) if op_id else None
            if data is None:
                emit_json({"status": "no_checkpoint", "mode": effective_mode})
            emit_json(data)

    effective_mode, effective_project, effective_prompt = _prepare_request()
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
        out=out,
        append=append,
        profile=effective_profile,
        cancel_on_interrupt=effective_cancel_on_interrupt,
    )


__all__ = ["ask"]
