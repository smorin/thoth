"""`thoth resume OP_ID` Click subcommand.

Per Q1-PR2-C (Tight + Honor) accepts a focused set of options:
  --verbose / -v
  --config / -c PATH
  --quiet / -Q
  --no-metadata
  --timeout / -T SECS
  --api-key-{openai,perplexity,mock} VALUE

All other globals are naturally rejected by Click (they are not declared
on this subcommand).
"""

from __future__ import annotations

import click

from thoth.cli_subcommands._option_policy import (
    DEFAULT_HONOR,
    inherited_api_keys,
    validate_inherited_options,
)
from thoth.completion.sources import operation_ids as _operation_ids_completer

_RESUME_HONOR = DEFAULT_HONOR | {
    "verbose",
    "quiet",
    "no_metadata",
    "timeout",
    "api_key_openai",
    "api_key_perplexity",
    "api_key_mock",
}


@click.command(name="resume")
@click.argument("operation_id", metavar="OP_ID", shell_complete=_operation_ids_completer)
@click.option("--verbose", "-v", is_flag=True, help="Enable debug output")
@click.option("--config", "-c", "config_path", help="Path to custom config file")
@click.option("--quiet", "-Q", is_flag=True, help="Minimal output during execution")
@click.option(
    "--no-metadata",
    is_flag=True,
    help="Disable metadata headers and prompt section in output files",
)
@click.option("--timeout", "-T", type=float, help="Override request timeout in seconds")
@click.option("--api-key-openai", help="API key for OpenAI provider")
@click.option("--api-key-perplexity", help="API key for Perplexity provider")
@click.option("--api-key-mock", help="API key for Mock provider")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON snapshot envelope")
@click.pass_context
def resume(
    ctx: click.Context,
    operation_id: str,
    verbose: bool,
    config_path: str | None,
    quiet: bool,
    no_metadata: bool,
    timeout: float | None,
    api_key_openai: str | None,
    api_key_perplexity: str | None,
    api_key_mock: str | None,
    as_json: bool,
) -> None:
    """Resume a previously-checkpointed operation by ID."""
    validate_inherited_options(ctx, "resume", _RESUME_HONOR)

    # Local import: avoids cli.py → cli_subcommands → cli.py circular at module load.
    import thoth.run as _thoth_run
    from thoth.cli import _apply_config_path, _build_app_context, _run_maybe_async

    if as_json:
        from thoth.json_output import emit_error, emit_json

        effective_config = config_path or (ctx.obj or {}).get("config_path")
        _apply_config_path(effective_config)

        data = _thoth_run.get_resume_snapshot_data(operation_id)
        if data is None:
            emit_error(
                "OPERATION_NOT_FOUND",
                f"Operation {operation_id} not found",
                {"operation_id": operation_id},
                exit_code=6,
            )
        if data["status"] == "failed_permanent":
            emit_error(
                "OPERATION_FAILED_PERMANENTLY",
                data["last_error"] or "operation failed permanently",
                data,
                exit_code=7,
            )
        emit_json(data)

    # Group-level inheritance for honored values per Q1-PR2-C
    inherited = ctx.obj or {}
    effective_verbose = bool(verbose or inherited.get("verbose"))
    effective_quiet = bool(quiet or inherited.get("quiet"))
    effective_no_metadata = bool(no_metadata or inherited.get("no_metadata"))
    effective_timeout = timeout if timeout is not None else inherited.get("timeout")
    effective_config = config_path or inherited.get("config_path")
    root_api_keys = inherited_api_keys(ctx)
    cli_api_keys = {
        "openai": api_key_openai or root_api_keys["openai"],
        "perplexity": api_key_perplexity or root_api_keys["perplexity"],
        "mock": api_key_mock or root_api_keys["mock"],
    }

    _apply_config_path(effective_config)
    app_ctx = _build_app_context(effective_verbose)
    _run_maybe_async(
        _thoth_run.resume_operation(
            operation_id,
            effective_verbose,
            ctx=app_ctx,
            quiet=effective_quiet,
            no_metadata=effective_no_metadata,
            timeout_override=effective_timeout,
            cli_api_keys=cli_api_keys,
        )
    )


__all__ = ["resume"]
