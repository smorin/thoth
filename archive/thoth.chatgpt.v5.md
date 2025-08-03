Product Requirements Document – Thoth v0.5

⸻

1 Document Control

Item	Value
Author	System Design Team
Date	27 Jul 2025
Status	Draft
Target Release	v0.5 (single‑file MVP)


⸻

2 Overview

Thoth is a single‑file Python command‑line tool that automates deep research using large‑language‑model agents.
Key features:
	•	Async‑safe integration with OpenAI Deep Research (long‑running, background jobs).
	•	Optional Perplexity provider.
	•	uv inline dependency block for zero‑install execution.
	•	Two output styles: stdout or structured Markdown/JSON artefacts under deep_research/<project>/.
	•	Interactive wizard for users who prefer guided prompts.
	•	Persistent defaults (e.g., favourite project) stored in ~/.thoth/defaults.toml.

⸻

3 Glossary

Term	Definition
Mode	Workflow phase (clarification, exploration, …) with its own prompt template.
Model slot	Alias that maps to {provider, model, options}.
Provider	LLM backend (openai, perplexity).
Research ID	Unique identifier returned when a Deep Research job starts.
Background mode	Asynchronous execution in Deep Research (background=True).
Polling	Repeated status checks until a job completes or times out.
Structured output	Files saved in deep_research/<project>/ with deterministic names.
Defaults file	~/.thoth/defaults.toml; user‑set system‑wide defaults.


⸻

4 Objectives
	1.	One‑command research with sensible defaults.
	2.	Async robustness – never hang; offer --async, --resume, listing, and configurable polling.
	3.	Deterministic, auditable artefacts for repeatability.
	4.	Zero system friction via uv inline dependencies.
	5.	Config‑over‑code – modes, model‑slots, and defaults overridable in user TOML.

⸻

5 Out of Scope (v0.5)
	•	Webhooks, private data (MCP), PDF/HTML export, citation verification, streaming token output, concurrent multi‑provider execution, rich TUI.

⸻

6 Assumptions
	•	Python ≥ 3.11 and Astral UV installed.
	•	Users provide provider API keys via env vars or CLI.
	•	Deep Research jobs can take 5–30 minutes.
	•	File paths must be cross‑platform.

⸻

7 Functional Requirements – Consolidated

ID	Requirement	Priority
F‑01	Built‑in modes hard‑coded; merge user file ~/.thoth/modes.toml.	Must
F‑02	Built‑in model‑slots hard‑coded; merge ~/.thoth/models.toml.	Must
F‑03	Built‑in defaults file ~/.thoth/defaults.toml overrides code when present.	Must
F‑04	Any CLI value may reference an external file with @/path or stdin with @-.	Must
F‑05	Create jobs in background; capture research_id.	Must
F‑06	Poll job status every n seconds (--poll-interval); default 30 s.	Must
F‑07	Abort after x minutes (--max-wait); default 30 min.	Must
F‑08	--async submits the job, prints research_id, and exits 0.	Must
F‑09	--research-id (alias --resume/-R) resumes an existing job.	Must
F‑10	--list-research (alias -L) lists queued/in‑progress jobs.	Should
F‑11	Dual‑provider run for model‑slot deep_research unless --provider given.	Must
F‑12	Structured output filenames: YYYYMMDD_HHMM-<mode>-<provider>-<slug>.{md,json}.	Must
F‑13	Slug deduplication by suffix (‑1, ‑2, …).	Should
F‑14	Config directory (~/.thoth) auto‑created on first run.	Should
F‑15	Interactive wizard: plain‑text prompts; escape with Ctrl‑C.	Must
F‑16	All diagnostics to stderr; DEBUG enabled with --verbose or THOTH_DEBUG=1.	Must
F‑17	Persistent default project: --set-default-project writes to defaults file; subsequent runs omit --project.	Must
F‑18	Command‑line overrides beat defaults file; defaults beat code.	Must
F‑19	Retry transient network/5xx errors up to 3 times with exponential back‑off.	Should
F‑20	Safety: mask API keys in logs and exceptions.	Must


⸻

8 Non‑Functional Requirements

ID	Requirement
N‑01	Poll requests ≤2 per minute by default.
N‑02	Tool runs on macOS, Linux, Windows.
N‑03	Only libraries declared in inline metadata are imported.
N‑04	Graceful exit on interrupt or validation errors.


⸻

9 Command‑Line Interface

9.1 Invocation Patterns

thoth <mode> "Query..." [OPTIONS]            # one‑shot (sync)
thoth -A <mode> -q "Query..."                # async submit & exit
thoth -R <ID> [OPTIONS]                      # resume job
thoth -L                                      # list jobs
thoth interactive                            # wizard

9.2 Options Matrix

Long	Short	Value	Description
–mode	-m	NAME	Workflow mode (optional if first arg is mode).
–query	-q	TEXT/@file/@-	Research prompt.
–structured	-s	flag	Enable file output.
–project	-p	NAME	Project folder; spaces→underscore.
–set-default-project	-S	NAME	Persist as default in defaults.toml.
–output-dir	-o	PATH	Root directory for structured output.
–model-slot	-M	SLOT	Override mode’s slot.
–provider	-P	NAME	openai / perplexity.
–api-key	-k	KEY	Override provider key.
–raw	-r	flag	Save raw JSON or print if not structured.
–fast	-f	flag	Use faster mini deep‑research model.
–no-code		flag	Disable code interpreter tool.
–poll-interval	-I	SECS	Seconds between status checks (default 30).
–max-wait	-W	MINS	Max minutes to wait (default 30).
–async	-A	flag	Fire‑and‑forget submit (mutually exclusive with -R).
–research-id / –resume	-R	ID	Resume existing research ID.
–list-research	-L	flag	List queued/in‑progress jobs.
–verbose	-v	flag	DEBUG log level.
–quiet		flag	Suppress spinner/progress messages.
–interactive	-i	flag	Launch wizard.
–version	-V	flag	Print version.
–help	-h	flag	Help.

Mutual exclusivity rules
	•	-A (async) cannot be combined with -R or -L.
	•	-L ignores all other flags except verbosity.
	•	When --structured is used without --project and a default project exists, the default is applied; else validation error.

⸻

10 Interactive Wizard (non‑TUI)

Step 1 Mode → Step 2 Prompt → Step 3 Structured? → Step 4 Project (prefill with default if exists) → Step 5 Provider (if deep_research) → Step 6 Advanced (async, polling, raw) → Confirmation screen.

⸻

11 Exit Codes

Code	Meaning
0	Success
1	Validation or user abort
2	Missing API key
3	Unsupported provider
4	API/network failure after retries
5	Max‑wait timeout
6	Research ID not found
7	Config/IO error (e.g., cannot write file)
127	Uncaught exception


⸻

12 Technical Requirements

12.1 Script Header

#!/usr/bin/env -S uv run --script
# /// script
requires-python = ">=3.11"
dependencies = [
  "openai>=1.14.0",
  "httpx>=0.27.0",
  "typer>=0.12",
  "rich>=13.7",
  'tomli>=2.0; python_version<"3.11"'
]
# ///

12.2 Async Workflow Outline

async def submit_job(query, model, tools):
    resp = await client.responses.create(
        model=model,
        input=[{"role": "system", "content": system_prompt},
               {"role": "user", "content": query}],
        tools=tools,
        background=True,
    )
    return resp.id

async def poll_job(job_id, poll_int, max_wait):
    start = time.monotonic()
    while True:
        resp = await client.responses.retrieve(job_id)
        if resp.status in ("completed", "failed"):
            return resp
        if time.monotonic() - start > max_wait:
            raise TimeoutError
        await asyncio.sleep(poll_int)

12.3 Dependencies
	•	openai – Deep Research & Responses API.
	•	httpx – HTTP + retry/back‑off.
	•	typer – CLI ergonomics.
	•	rich – optional pretty progress bar / table.
	•	Stdlib: asyncio, argparse (fallback), logging, pathlib, textwrap, tomllib/json, time, re.

⸻

13 Configuration Files

13.1 ~/.thoth/models.toml

[thinking]
provider = "openai"
model = "gpt-4o-mini"
options = { temperature = 0.4 }

[deep_research]
provider = "openai"
model = "o3-deep-research-2025-06-26"
options = { reasoning = { summary = "auto" } }

13.2 ~/.thoth/modes.toml

[competitive_analysis]
description = "Competitive landscape research"
default_slot = "deep_research"
prompt = """
Analyse «{query}» with respect to market share, pricing, and strategy.
"""
next = "solution"

13.3 ~/.thoth/defaults.toml

[general]
default_project = "research_notes"
output_dir = "/Users/alex/research"
poll_interval = 20        # seconds
max_wait = 45             # minutes


⸻

14 Error‑Handling Strategy
	•	Validation (exit 1): unknown mode/flag combos, mutually exclusive violations.
	•	Network or API 5xx (exit 4): retry ×3; log and abort if persistent.
	•	Timeout (exit 5): job exceeds --max-wait.
	•	Config/IO (exit 7): cannot read/write config or output files.
	•	All logged via logging with keys scrubbed.

⸻

15 Open Issues

#	Issue	Mitigation
O‑1	Perplexity async semantics not final.	Behind experimental flag.
O‑2	Rate‑limit tuning for high concurrency.	Allow user to raise poll interval.
O‑3	Large outputs overwhelm terminal.	Auto‑enable structured when tokens > 20 k.
O‑4	Defaults file corruption.	Validate on load; backup & regen.


⸻

16 Future Enhancements
	•	Webhook callbacks (no polling).
	•	Resume plus automatic file write upon completion.
	•	Private data (MCP) integration.
	•	Parallel provider execution.
	•	Rich TUI with live progress.
	•	Token usage & cost summary.
	•	Output to HTML/PDF and slides.

⸻

End of Thoth v0.5 PRD