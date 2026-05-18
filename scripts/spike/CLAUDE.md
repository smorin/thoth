# Writing live-API spike scripts

Spike scripts probe live provider APIs to validate plan assumptions
before code is written. Live-API spend MUST be user-authorized.

## Survival rule: write outputs DIRECTLY, never via tee

Scripts dispatched by a subagent often outlive the dispatching agent
(subagents have ~30 min wall budgets; spikes can take 60+ min). When
the agent dies, the `tee` pipe dies with it, and `script.py | tee out.txt`
loses ALL output even though the Python process keeps running.

```bash
# WRONG — output lost if subagent dies before script completes
uv run scripts/spike/my_spike.py 2>&1 | tee research/_my_spike.txt

# RIGHT — script writes its own log + JSON internally
uv run scripts/spike/my_spike.py
# inside the script:
LOG = OUT_DIR / "_my_spike.txt"
def log(msg): LOG.open("a").write(msg + "\n")
```

See the P28 Task 6b incident in `research/gemini-dr-api-spike-2026-05-11.md §6b`:
~$5-7 of API spend lost across two attempts before pivoting to a
surface-only probe.

## Checkpoint intermediate state

If a spike has multiple probes, write JSON state after EACH probe
completes. A 60-min spike that crashes at minute 59 with no
checkpointing loses everything:

```python
RESULTS = {}
for probe_name, probe_fn in PROBES:
    RESULTS[probe_name] = await probe_fn(client)
    # Write checkpoint after EACH probe — survives mid-run termination.
    OUT_JSON.write_text(json.dumps(RESULTS, indent=2, default=str))
```

## UV-shebang convention

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["google-genai>=1.74.0", "httpx"]
# ///
"""Brief description. Outputs to research/_my_spike.{json,txt}."""

from __future__ import annotations
import asyncio, json, os, sys
from pathlib import Path
```

Make executable: `chmod +x scripts/spike/p<NN>/my_spike.py`.

## File layout

| Path | Purpose |
|---|---|
| `scripts/spike/p<NN>/spike_*.py` | The executable spike scripts |
| `research/_<spike_name>.json` | Structured evidence (machine-readable) |
| `research/_<spike_name>.txt` | Human-readable log (optional) |
| `research/<topic>-api-spike-<DATE>.md` | Findings doc that interprets the evidence |

Filename convention: `_dr_spike_<topic>.*` for raw evidence (leading
underscore signals "raw data, not the writeup"). The findings doc has
no underscore prefix.

## Reproducibility headers

Include in each JSON dump:

```python
{
    "captured_at": datetime.now(tz=timezone.utc).isoformat(),
    "script": Path(__file__).name,
    "sdk_versions": {"google-genai": genai.__version__},  # if accessible
    "inputs": {"prompt": PROMPT[:200], "agent": AGENT},
    "results": [...],
}
```

Lets a v1.1 maintainer re-run the script against a newer SDK and
diff the findings.

## Live-API spend awareness

Estimate spend per probe upfront in the script's docstring:

```python
"""Cost: ~$2-5 for 3 probes against deep-research-preview-04-2026.

User-authorize before running. Free tier is ineligible (DR is paid-only)."""
```

Surface the estimate to the user when the spike is queued in a plan
task. Don't run paid spikes silently.

## Parallel-subagent hygiene

If another subagent is concurrently writing code in `src/` or `tests/`,
spike subagents MUST use explicit `git add` paths:

```bash
# RIGHT — explicit paths, won't pick up the other subagent's WIP
git add scripts/spike/p<NN>/my_spike.py research/_my_spike.* research/findings.md
git commit -m "..."

# WRONG — will pick up any uncommitted files in the worktree
git add -A
git commit -m "..."
```

Conventional Commits: spike commits use `chore(<scope>):` —
`spike(<scope>):` is NOT in the allowed commitlint types and will be
rejected.
