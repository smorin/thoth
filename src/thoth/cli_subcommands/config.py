"""`thoth config` Click subgroup with leaves: get, set, unset, list, path, edit."""

from __future__ import annotations

import sys

import click

from thoth.cli_subcommands._option_policy import (
    DEFAULT_HONOR,
    NO_INHERITED_OPTIONS,
    inherited_value,
    validate_inherited_options,
)
from thoth.completion.sources import config_keys as _config_keys_completer

_PASSTHROUGH_CONTEXT = {"ignore_unknown_options": True, "allow_extra_args": True}
_VALID_LAYERS = ("defaults", "user", "project", "env", "cli")


@click.group(name="config", invoke_without_command=True)
@click.pass_context
def config(ctx: click.Context) -> None:
    """Inspect and edit configuration."""
    if ctx.invoked_subcommand is None:
        validate_inherited_options(ctx, "config", NO_INHERITED_OPTIONS)
        click.echo(
            "Error: config command requires an op (get|set|unset|list|path|edit|help)",
            err=True,
        )
        ctx.exit(2)


def _dispatch(
    ctx: click.Context,
    op: str,
    args: tuple[str, ...],
    honored_options=DEFAULT_HONOR,
) -> None:
    from thoth.config_cmd import config_command

    validate_inherited_options(ctx, f"config {op}", honored_options)
    config_path = inherited_value(ctx, "config_path")
    if config_path is None:
        rc = config_command(op, list(args))
    else:
        rc = config_command(op, list(args), config_path=config_path)
    sys.exit(rc)


@config.command(name="get")
@click.argument("key", shell_complete=_config_keys_completer)
@click.option(
    "--layer",
    "layer",
    type=click.Choice(_VALID_LAYERS),
    default=None,
    help="Read from a specific config layer",
)
@click.option(
    "--raw",
    is_flag=True,
    help="Read pre-merge layer data (formatting only; does NOT bypass masking)",
)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.option(
    "--show-secrets",
    is_flag=True,
    help="Reveal masked secret values (security-sensitive)",
)
@click.pass_context
def config_get(
    ctx: click.Context,
    key: str,
    layer: str | None,
    raw: bool,
    as_json: bool,
    show_secrets: bool,
) -> None:
    """Get a configuration value."""
    validate_inherited_options(ctx, "config get", DEFAULT_HONOR)
    config_path = inherited_value(ctx, "config_path")

    if as_json:
        from thoth.config_cmd import get_config_get_data
        from thoth.json_output import emit_error, emit_json

        data = get_config_get_data(
            key, layer=layer, raw=raw, show_secrets=show_secrets, config_path=config_path
        )
        if data.get("error") == "INVALID_LAYER":
            emit_error(
                "INVALID_LAYER",
                f"--layer must be one of {', '.join(_VALID_LAYERS)}",
                exit_code=2,
            )
        if not data["found"]:
            emit_error("KEY_NOT_FOUND", f"key not found: {key}", {"key": key}, exit_code=1)
        emit_json(data)

    rebuilt: list[str] = [key]
    if layer is not None:
        rebuilt.extend(["--layer", layer])
    if raw:
        rebuilt.append("--raw")
    if show_secrets:
        rebuilt.append("--show-secrets")
    _dispatch(ctx, "get", tuple(rebuilt))


@config.command(name="set", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def config_set(ctx: click.Context, args: tuple[str, ...], as_json: bool) -> None:
    """Set a configuration value."""
    if as_json:
        from thoth.config_cmd import get_config_set_data
        from thoth.json_output import emit_error, emit_json

        validate_inherited_options(ctx, "config set", DEFAULT_HONOR)
        config_path = inherited_value(ctx, "config_path")

        positional: list[str] = []
        project = False
        force_string = False
        for a in args:
            if a == "--project":
                project = True
            elif a == "--string":
                force_string = True
            else:
                positional.append(a)

        if len(positional) != 2:
            emit_error("USAGE_ERROR", "config set takes KEY VALUE", exit_code=2)
        key, raw_value = positional[0], positional[1]
        data = get_config_set_data(
            key,
            raw_value,
            project=project,
            force_string=force_string,
            config_path=config_path,
        )
        if data.get("error") == "PROJECT_CONFIG_CONFLICT":
            emit_error(
                "PROJECT_CONFIG_CONFLICT",
                "--config cannot be used with --project",
                exit_code=2,
            )
        emit_json(data)

    _dispatch(ctx, "set", args)


@config.command(name="unset", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def config_unset(ctx: click.Context, args: tuple[str, ...], as_json: bool) -> None:
    """Unset a configuration value."""
    if as_json:
        from thoth.config_cmd import get_config_unset_data
        from thoth.json_output import emit_error, emit_json

        validate_inherited_options(ctx, "config unset", DEFAULT_HONOR)
        config_path = inherited_value(ctx, "config_path")

        positional: list[str] = []
        project = False
        for a in args:
            if a == "--project":
                project = True
            else:
                positional.append(a)

        if len(positional) != 1:
            emit_error("USAGE_ERROR", "config unset takes KEY", exit_code=2)
        key = positional[0]
        data = get_config_unset_data(key, project=project, config_path=config_path)
        if data.get("error") == "PROJECT_CONFIG_CONFLICT":
            emit_error(
                "PROJECT_CONFIG_CONFLICT",
                "--config cannot be used with --project",
                exit_code=2,
            )
        emit_json(data)

    _dispatch(ctx, "unset", args)


@config.command(name="list", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def config_list(ctx: click.Context, args: tuple[str, ...], as_json: bool) -> None:
    """List all configuration values. Supports --json."""
    if as_json:
        from thoth.config_cmd import get_config_list_data
        from thoth.json_output import emit_error, emit_json

        validate_inherited_options(ctx, "config list", DEFAULT_HONOR)
        config_path = inherited_value(ctx, "config_path")

        layer: str | None = None
        keys_only = False
        show_secrets = False
        i = 0
        rest = list(args)
        while i < len(rest):
            a = rest[i]
            if a == "--layer":
                if i + 1 >= len(rest):
                    emit_error("USAGE_ERROR", "--layer requires a value", exit_code=2)
                layer = rest[i + 1]
                i += 2
            elif a == "--keys":
                keys_only = True
                i += 1
            elif a == "--show-secrets":
                show_secrets = True
                i += 1
            else:
                emit_error("USAGE_ERROR", f"unknown arg: {a}", exit_code=2)
        data = get_config_list_data(
            layer=layer,
            keys_only=keys_only,
            show_secrets=show_secrets,
            config_path=config_path,
        )
        if data.get("error") == "INVALID_LAYER":
            emit_error(
                "INVALID_LAYER",
                f"--layer must be one of {', '.join(_VALID_LAYERS)}",
                exit_code=2,
            )
        emit_json(data)

    _dispatch(ctx, "list", args)


@config.command(name="path", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def config_path(ctx: click.Context, args: tuple[str, ...], as_json: bool) -> None:
    """Show config file path."""
    if as_json:
        from thoth.config_cmd import get_config_path_data
        from thoth.json_output import emit_error, emit_json

        validate_inherited_options(ctx, "config path", DEFAULT_HONOR)
        config_path_inh = inherited_value(ctx, "config_path")
        project = "--project" in args
        data = get_config_path_data(project=project, config_path=config_path_inh)
        if data.get("error") == "PROJECT_CONFIG_CONFLICT":
            emit_error(
                "PROJECT_CONFIG_CONFLICT",
                "--config cannot be used with --project",
                exit_code=2,
            )
        emit_json(data)

    _dispatch(ctx, "path", args)


@config.command(name="edit", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def config_edit(ctx: click.Context, args: tuple[str, ...]) -> None:
    """Open config file in $EDITOR."""
    _dispatch(ctx, "edit", args)


@config.command(name="help", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def config_help(ctx: click.Context, args: tuple[str, ...]) -> None:
    """Show config command help."""
    _dispatch(ctx, "help", args, NO_INHERITED_OPTIONS)
