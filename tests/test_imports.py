"""Pin the public import surface of `doxa_research.__main__` before decomposition (P09).

This file is a safety net: the P09 refactor moves code out of `doxa_research.__main__`
into a package of submodules. Existing callers (tests/ and the `doxa_test`
black-box runner) import directly from `doxa_research.__main__`. After each extraction
phase, every symbol listed here MUST still be reachable via `doxa_research.__main__`
(via the re-export shim), or the test suite and black-box runner break.

If this file goes red, the shim in `src/doxa_research/__main__.py` is missing a
re-export — fix the shim, not this file.
"""

from __future__ import annotations

import doxa_research.__main__ as doxa_main

# Union of every symbol currently imported with `from doxa_research.__main__ import …`
# across /Users/stevemorin/c/doxa_research/tests and /Users/stevemorin/c/doxa_research/doxa_test.
PUBLIC_IMPORTED_SYMBOLS: tuple[str, ...] = (
    # Errors (tests/test_openai_errors.py, test_api_key_resolver.py)
    "APIKeyError",
    "APIQuotaError",
    "APIRateLimitError",
    "ProviderError",
    "DoxaError",
    # Models (tests/test_sigint_handler.py, doxa_test inline)
    "OperationStatus",
    # Managers (tests/test_sigint_handler.py)
    "CheckpointManager",
    "OutputManager",
    # Config (tests/test_config.py)
    "ConfigManager",
    "get_config",
    # Providers (tests/test_openai_errors.py, test_vcr_openai.py, doxa_test)
    "OpenAIProvider",
    "_map_openai_error",
    # API-key resolver (tests/test_api_key_resolver.py)
    "PROVIDER_ENV_VARS",
    "resolve_api_key",
    # Signal handling (tests/test_sigint_handler.py)
    "handle_sigint",
    "_raise_if_interrupted",
    # Research execution (doxa_test inline)
    "_execute_research",
)

# Module-level attributes that tests access as `doxa_main.X` (read or rebind).
# These must continue to exist on the __main__ module after extraction.
# See tests/test_sigint_handler.py for the access patterns.
PUBLIC_MODULE_ATTRIBUTES: tuple[str, ...] = (
    "_interrupt_event",
    "_last_interrupt_at",
    "_current_checkpoint_manager",
    "_current_operation",
    # Imported modules that tests monkeypatch via attribute path:
    #   monkeypatch.setattr(doxa_main.aiofiles, "open", ...)
    #   monkeypatch.setattr(doxa_main.time, "monotonic", ...)
    "aiofiles",
    "time",
)


def test_all_imported_symbols_resolvable() -> None:
    """Every symbol imported `from doxa_research.__main__ import X` across the test
    suite and the black-box runner must resolve."""
    missing = [name for name in PUBLIC_IMPORTED_SYMBOLS if not hasattr(doxa_main, name)]
    assert not missing, (
        f"doxa_research.__main__ is missing re-exports: {missing}. "
        f"Update src/doxa_research/__main__.py to re-export them."
    )


def test_all_module_attributes_present() -> None:
    """Module-level attributes that tests read or rebind via
    `doxa_main.X` must exist."""
    missing = [name for name in PUBLIC_MODULE_ATTRIBUTES if not hasattr(doxa_main, name)]
    assert not missing, (
        f"doxa_research.__main__ is missing module attributes: {missing}. "
        f"Re-import them at module scope in src/doxa_research/__main__.py."
    )


def test_main_entry_point_callable() -> None:
    """pyproject.toml declares `doxa = doxa_research.__main__:main`.
    The shim must preserve `main` as a callable at that path."""
    assert hasattr(doxa_main, "main"), "main() missing — pyproject entry point will break"
    assert callable(doxa_main.main), "doxa_research.__main__.main is not callable"


def test_cli_group_callable() -> None:
    """The click command group is invoked by main(); external tools
    (doxa_test subprocesses via the console-script) need it reachable."""
    assert hasattr(doxa_main, "cli"), "cli command group missing from doxa_research.__main__"
