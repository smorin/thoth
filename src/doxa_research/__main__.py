"""Doxa Research - AI-Powered Research Assistant.

Entry-point shim that re-exports the public surface from submodules.

Real implementations live in doxa_research.errors, doxa_research.config, doxa_research.models,
doxa_research.utils, doxa_research.signals, doxa_research.checkpoint, doxa_research.output, doxa_research.providers,
doxa_research.run, doxa_research.commands, doxa_research.help, doxa_research.interactive, and doxa_research.cli.

Kept for backward compatibility with the many `from doxa_research.__main__ import ...`
imports in tests/ and in the doxa_test black-box runner, and so that the
`[project.scripts] doxa = "doxa_research.__main__:main"` entry point in pyproject.toml
continues to resolve `main` at its documented location.

Signal-handling module globals (`_interrupt_event`, `_current_operation`,
`_current_checkpoint_manager`, `_last_interrupt_at`) are re-exported by
reference from `doxa_research.signals`. Tests that READ these names via
`doxa_research.__main__` observe the live values. Tests that need to REBIND them
(rare) must target `doxa_research.signals` directly.
"""

from __future__ import annotations

# Keep module-level Console and threading/time/aiofiles available for tests
# that reach into this module (e.g. monkeypatching `doxa_research.__main__.time` or
# `doxa_research.__main__.aiofiles.open`).
import threading  # noqa: F401
import time  # noqa: F401
from typing import Any

import aiofiles  # noqa: F401
from rich.console import Console

import doxa_research.config as _doxa_config  # noqa: F401
import doxa_research.signals as _doxa_signals  # noqa: F401
from doxa_research.checkpoint import CheckpointManager  # noqa: F401
from doxa_research.cli import cli, handle_error, main  # noqa: F401
from doxa_research.commands import (  # noqa: F401
    CommandHandler,
    list_command,
    list_operations,
    providers_command,
    show_status,
    status_command,
)
from doxa_research.config import (  # noqa: F401
    BUILTIN_MODES,
    CONFIG_VERSION,
    DOXA_VERSION,
    ConfigManager,
    ConfigSchema,
    get_config,
)
from doxa_research.errors import (  # noqa: F401
    APIKeyError,
    APIQuotaError,
    APIRateLimitError,
    DiskSpaceError,
    DoxaError,
    ProviderError,
)
from doxa_research.interactive import (  # noqa: F401
    PROMPT_TOOLKIT_AVAILABLE,
    ClarificationSession,
    InteractiveSession,
    SlashCommandCompleter,
    SlashCommandRegistry,
    enter_interactive_mode,
)
from doxa_research.models import (  # noqa: F401
    InputMode,
    InteractiveInitialSettings,
    ModelCache,
    OperationStatus,
)
from doxa_research.output import OutputManager  # noqa: F401
from doxa_research.providers import (  # noqa: F401
    PROVIDER_ENV_VARS,
    PROVIDERS,
    MockProvider,
    OpenAIProvider,
    PerplexityProvider,
    ResearchProvider,
    create_provider,
    resolve_api_key,
)
from doxa_research.providers.openai import _map_openai_error  # noqa: F401
from doxa_research.run import (  # noqa: F401
    _execute_research,
    _run_polling_loop,
    find_latest_outputs,
    get_estimated_duration,
    resume_operation,
    run_research,
)
from doxa_research.signals import (  # noqa: F401
    _INTERRUPT_FORCE_EXIT_WINDOW_S,
    _current_checkpoint_manager,
    _current_operation,
    _interrupt_event,
    _last_interrupt_at,
    _raise_if_interrupted,
    handle_sigint,
)
from doxa_research.utils import (  # noqa: F401
    check_disk_space,
    generate_operation_id,
    mask_api_key,
)

# Module-level Console preserved for any caller that reached into
# `doxa_research.__main__.console` historically.
console = Console()


# ---------------------------------------------------------------------------
# Shim rebinding propagation
# ---------------------------------------------------------------------------
# Some callers (notably doxa_test) monkeypatch attributes on this shim and
# expect the rebinds to be observed at call sites inside the extracted
# submodules — e.g. `doxa_main.run_research = fake` must affect the
# `run_research` that `doxa_research.interactive.enter_interactive_mode` calls.
#
# Python modules don't auto-proxy attribute writes, so we upgrade this
# module's class (PEP 549) to a subclass whose __setattr__ mirrors a small
# allow-list of attributes into the real modules. No-op for attrs not in
# the allow-list, so normal shim imports are untouched.
import sys  # noqa: E402
import types  # noqa: E402


class _ShimModule(types.ModuleType):
    # Map attr name -> list of modules that should also be updated when
    # `doxa_research.__main__.<attr>` is rebound.
    _PROPAGATE = {
        "run_research": ("doxa_research.interactive", "doxa_research.cli"),
        "SlashCommandRegistry": ("doxa_research.interactive",),
        "SlashCommandCompleter": ("doxa_research.interactive",),
        "InteractiveSession": ("doxa_research.interactive",),
        "ClarificationSession": ("doxa_research.interactive",),
        "run_in_terminal": ("doxa_research.interactive",),
        "show_status": ("doxa_research.interactive", "doxa_research.commands"),
        "PROMPT_TOOLKIT_AVAILABLE": ("doxa_research.interactive",),
    }

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        for target in self._PROPAGATE.get(name, ()):
            mod = sys.modules.get(target)
            if mod is not None:
                setattr(mod, name, value)


sys.modules[__name__].__class__ = _ShimModule


# Re-export `run_in_terminal` from prompt_toolkit at module level so
# doxa_test can monkeypatch `doxa_research.__main__.run_in_terminal`. Mirrors
# the module availability handling in doxa_research.interactive.
run_in_terminal: Any = None
try:
    from prompt_toolkit.application import run_in_terminal  # noqa: F401, E402
except ImportError:
    pass


if __name__ == "__main__":
    main()
