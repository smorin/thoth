"""Thoth - AI-Powered Research Assistant.

Entry-point shim that re-exports the public surface from submodules.

Real implementations live in thoth.errors, thoth.config, thoth.models,
thoth.utils, thoth.signals, thoth.checkpoint, thoth.output, thoth.providers,
thoth.run, thoth.commands, thoth.help, thoth.interactive, and thoth.cli.

Kept for backward compatibility with the many `from thoth.__main__ import ...`
imports in tests/ and in the thoth_test black-box runner, and so that the
`[project.scripts] thoth = "thoth.__main__:main"` entry point in pyproject.toml
continues to resolve `main` at its documented location.

Signal-handling module globals (`_interrupt_event`, `_current_operation`,
`_current_checkpoint_manager`, `_last_interrupt_at`) are re-exported by
reference from `thoth.signals`. Tests that READ these names via
`thoth.__main__` observe the live values. Tests that need to REBIND them
(rare) must target `thoth.signals` directly.
"""

from __future__ import annotations

# Keep module-level Console and threading/time/aiofiles available for tests
# that reach into this module (e.g. monkeypatching `thoth.__main__.time` or
# `thoth.__main__.aiofiles.open`).
import threading  # noqa: F401
import time  # noqa: F401
from typing import Any

import aiofiles  # noqa: F401
from rich.console import Console

import thoth.config as _thoth_config  # noqa: F401
import thoth.signals as _thoth_signals  # noqa: F401
from thoth.checkpoint import CheckpointManager  # noqa: F401
from thoth.cli import cli, handle_error, main  # noqa: F401
from thoth.commands import (  # noqa: F401
    CommandHandler,
    list_command,
    list_operations,
    providers_command,
    show_status,
    status_command,
)
from thoth.config import (  # noqa: F401
    BUILTIN_MODES,
    CONFIG_VERSION,
    THOTH_VERSION,
    ConfigManager,
    ConfigSchema,
    get_config,
)
from thoth.errors import (  # noqa: F401
    APIKeyError,
    APIQuotaError,
    APIRateLimitError,
    DiskSpaceError,
    ProviderError,
    ThothError,
)
from thoth.interactive import (  # noqa: F401
    PROMPT_TOOLKIT_AVAILABLE,
    ClarificationSession,
    InteractiveSession,
    SlashCommandCompleter,
    SlashCommandRegistry,
    enter_interactive_mode,
)
from thoth.models import (  # noqa: F401
    InputMode,
    InteractiveInitialSettings,
    ModelCache,
    OperationStatus,
)
from thoth.output import OutputManager  # noqa: F401
from thoth.providers import (  # noqa: F401
    PROVIDER_ENV_VARS,
    PROVIDERS,
    MockProvider,
    OpenAIProvider,
    PerplexityProvider,
    ResearchProvider,
    create_provider,
    resolve_api_key,
)
from thoth.providers.openai import _map_openai_error  # noqa: F401
from thoth.run import (  # noqa: F401
    _execute_research,
    _run_polling_loop,
    find_latest_outputs,
    get_estimated_duration,
    resume_operation,
    run_research,
)
from thoth.signals import (  # noqa: F401
    _INTERRUPT_FORCE_EXIT_WINDOW_S,
    _current_checkpoint_manager,
    _current_operation,
    _interrupt_event,
    _last_interrupt_at,
    _raise_if_interrupted,
    handle_sigint,
)
from thoth.utils import (  # noqa: F401
    check_disk_space,
    generate_operation_id,
    mask_api_key,
)

# Module-level Console preserved for any caller that reached into
# `thoth.__main__.console` historically.
console = Console()


# ---------------------------------------------------------------------------
# Shim rebinding propagation
# ---------------------------------------------------------------------------
# Some callers (notably thoth_test) monkeypatch attributes on this shim and
# expect the rebinds to be observed at call sites inside the extracted
# submodules — e.g. `thoth_main.run_research = fake` must affect the
# `run_research` that `thoth.interactive.enter_interactive_mode` calls.
#
# Python modules don't auto-proxy attribute writes, so we upgrade this
# module's class (PEP 549) to a subclass whose __setattr__ mirrors a small
# allow-list of attributes into the real modules. No-op for attrs not in
# the allow-list, so normal shim imports are untouched.
import sys  # noqa: E402
import types  # noqa: E402


class _ShimModule(types.ModuleType):
    # Map attr name -> list of modules that should also be updated when
    # `thoth.__main__.<attr>` is rebound.
    _PROPAGATE = {
        "run_research": ("thoth.interactive", "thoth.cli"),
        "SlashCommandRegistry": ("thoth.interactive",),
        "SlashCommandCompleter": ("thoth.interactive",),
        "InteractiveSession": ("thoth.interactive",),
        "ClarificationSession": ("thoth.interactive",),
        "run_in_terminal": ("thoth.interactive",),
        "show_status": ("thoth.interactive", "thoth.commands"),
        "PROMPT_TOOLKIT_AVAILABLE": ("thoth.interactive",),
    }

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        for target in self._PROPAGATE.get(name, ()):
            mod = sys.modules.get(target)
            if mod is not None:
                setattr(mod, name, value)


sys.modules[__name__].__class__ = _ShimModule


# Re-export `run_in_terminal` from prompt_toolkit at module level so
# thoth_test can monkeypatch `thoth.__main__.run_in_terminal`. Mirrors
# the module availability handling in thoth.interactive.
run_in_terminal: Any = None
try:
    from prompt_toolkit.application import run_in_terminal  # noqa: F401, E402
except ImportError:
    pass


if __name__ == "__main__":
    main()
