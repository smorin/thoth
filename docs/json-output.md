# JSON output (`--json`) — envelope contract

Every data/action admin command in thoth supports `--json` for scripted
consumption. The output is a single JSON object on stdout; the exit code
indicates success (0) or failure (non-zero).

## Envelope shapes

**Success:**

    {"status": "ok", "data": {...}}

**Error:**

    {"status": "error", "error": {"code": "STRING_CODE", "message": "...",
                                   "details": {...}?}}

`details` is optional and code-specific.

## Error codes (catalog)

| Code | Used by | Exit | Meaning |
|---|---|---|---|
| `OPERATION_NOT_FOUND` | `status`, `resume` | 6 | Op ID not in checkpoint store |
| `OPERATION_FAILED_PERMANENTLY` | `resume` | 7 | Permanent failure |
| `JSON_REQUIRES_NONINTERACTIVE` | `init` | 2 | `init --json` without `--non-interactive` |
| `EDITOR_FAILED` | `config edit` | 1 | `$EDITOR` exited non-zero |
| `UNSUPPORTED_SHELL` | `completion` | 2 | Shell name not in {bash, zsh, fish} |
| `INSTALL_REQUIRES_TTY` | `completion --install` | 2 | non-TTY + no `--force` + no `--manual` |
| `INSTALL_FILE_PERMISSION` | `completion --install` | 1 | Can't write to rc file |
| `KEY_NOT_FOUND` | `config get` | 1 | Config key doesn't exist |
| `INVALID_LAYER` | `config get --layer` | 2 | Click choice validation |
| `PROVIDER_FAILURE` | `ask`, `resume` | 1 | Upstream provider error |
| `API_KEY_MISSING` | `ask`, `resume`, `providers check` | 1 | Required key not set |
| `INTERRUPTED` | any | 130 | SIGINT during `--json` run |

## Per-command schemas (sketch)

**`status OP_ID --json`:**

    {"status": "ok",
     "data": {"operation_id": "...", "status": "running"|"completed"|...,
              "mode": "...", "prompt": "...",
              "providers": {...}, "output_paths": {...}}}

**`list --json`:**

    {"status": "ok",
     "data": {"count": N,
              "operations": [{"operation_id": "...", "status": "...", ...}, ...]}}

**`providers list --json`:**

    {"status": "ok",
     "data": {"providers": [{"name": "openai", "key_set": true}, ...]}}

**`completion <shell> --install --json`:**

    {"status": "ok",
     "data": {"shell": "bash", "action": "written"|"preview"|"skipped",
              "path": "/.../.bashrc", "message": "..."}}

**`resume OP_ID --json` (snapshot — never advances state):**

    {"status": "ok",
     "data": {"operation_id": "...", "status": "running"|"recoverable_failure"|...,
              "mode": "...", "prompt": "...", "last_error": "..."|null,
              "retry_count": N}}

`recoverable_failure` is an envelope-data state mapped from on-disk
`status="failed"` + `failure_type` not equal to `"permanent"`. The
COMMAND succeeded (`status:"ok"`); `data.status` describes the
operation. To advance/retry, run `thoth resume OP_ID` WITHOUT `--json`.

## Non-blocking guarantee (Option E)

`--json` is non-blocking and snapshot-shaped:

  * `ask --json` immediate-mode: synchronous; full result inline.
  * `ask --json` background-mode: auto-async — submit + return op-id envelope.
  * `resume --json`: pure snapshot; never polls; never advances state.

Tests assert these complete within 5 seconds.

## Uninstalling completion

The completion `--install` writes a fenced block:

    # >>> thoth completion >>>
    eval "$(_THOTH_COMPLETE=bash_source thoth)"
    # <<< thoth completion <<<

Remove with one sed invocation:

    sed -i '/# >>> thoth completion >>>/,/# <<< thoth completion <<</d' ~/.bashrc

A real `--uninstall` flag is a future PR.
