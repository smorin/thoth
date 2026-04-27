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


@click.command(name="resume")
@click.argument("operation_id", metavar="OP_ID")
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
) -> None:
    """Resume a previously-checkpointed operation by ID."""
    # Local import: avoids cli.py → cli_subcommands → cli.py circular at module load.
    import thoth.run as _thoth_run
    from thoth.cli import _apply_config_path, _build_app_context, _run_maybe_async

    # Group-level inheritance for honored values per Q1-PR2-C
    inherited = ctx.obj or {}
    effective_verbose = bool(verbose or inherited.get("verbose"))
    effective_quiet = bool(quiet or inherited.get("quiet"))
    effective_no_metadata = bool(no_metadata or inherited.get("no_metadata"))
    effective_timeout = timeout if timeout is not None else inherited.get("timeout")
    effective_config = config_path or inherited.get("config_path")
    cli_api_keys = {
        "openai": api_key_openai or inherited.get("api_key_openai"),
        "perplexity": api_key_perplexity or inherited.get("api_key_perplexity"),
        "mock": api_key_mock or inherited.get("api_key_mock"),
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
