# Gemini Deep Research API Spike — Findings

**STATUS: pending live-API run.** Scripts at `scripts/spike/p28/` are ready but have not been
executed; running them costs ~$2-6 in Gemini paid-tier API spend and requires user authorization.

---

## §1 Confirmed agent IDs

Which agent IDs are actually listed by the live `client.models.list()` API call.
Determines whether `deep-research-preview-04-2026` (v1 default) and
`deep-research-max-preview-04-2026` (max-tier) are both present, and whether the
legacy `deep-research-pro-preview-12-2025` has been retired.

Block-if-failed: if `deep-research-preview-04-2026` is NOT listed, Task 2+ cannot
proceed with the current agent ID. Re-scope P28 v1 agent before continuing.

> TODO: populate from `spike_dr_models.py` output (and `research/_dr_spike_models.txt`)

---

## §2 Submit response shape

Exact format of the object returned by `client.aio.interactions.create(...)`:
`interaction.id` format (e.g., `"interactions/..."` prefix), list of top-level attributes,
initial status value, and any other relevant fields on the returned interaction object.
Drives the `_deep_research_submit` implementation in Task 2.

> TODO: populate from `spike_dr_submit.py` output (and `research/_dr_spike_submit.json`)

---

## §3 Final response shape

Complete structure of a finished interaction:
- `steps[]` list — how many steps, what `step.type` values appear
- `step.content[]` items — item shapes, `type` values, `text` previews
- Any other top-level attributes present on completion (e.g., `outputs`, `status`, timestamps)

Drives the `_deep_research_get_result` implementation in Task 2.

> TODO: populate from `spike_dr_poll.py` output (and `research/_dr_spike_poll.json`)

---

## §4 Citation extraction strategy (the v1 gate)

Which attribute(s) on content items (or the interaction object itself) hold citation
data — e.g., `citations`, `annotations`, `references`, `grounding`, `url`, etc.
Exact shape of the citation records (fields present, nesting level).

If NO citation-shaped attribute is found anywhere in the response, this section reads:
**BLOCKED — escalate to user.** Task 8 (citation extraction) cannot proceed.

Per spec scope §8: v1 parses `interaction.outputs[-1].annotations[]` for `{url, start_index, end_index}`
records. This section confirms or refutes that assumption.

> TODO: populate from `spike_dr_poll.py` output — specifically the "found attr" probe lines
> and the `_dr_spike_poll.json` dump of `step.content[]` items

---

## §5 Status enum values observed

Every distinct `status` string value observed during the lifecycle of a Deep Research
interaction: from submission through poll transitions to terminal state.
Expected values from spec: `"in_progress"`, `"completed"`, `"failed"`, `"cancelled"`.
Actual observed values may differ in capitalization or naming.

Feeds the `_deep_research_check_status` implementation and the `OperationStatus` mapping in Task 2.

> TODO: populate from `spike_dr_poll.py` output — the "status ->" transition lines
> and the `transitions` array in `_dr_spike_poll.json`

---

## §6 Cancel behavior

Answers three questions from the plan:
1. Does `client.aio.interactions.cancel()` exist on the SDK surface?
2. Does calling it cause the interaction to transition to `"cancelled"` status within ~60s?
3. Does a cancelled interaction preserve partial `steps[]` / `outputs` or arrive empty?

Block-if-failed: if `cancel()` is missing or raises `NotImplementedError`, Task 9
(SIGINT cooperative cancel) requires an alternative strategy.

Also feeds spec delta #4 (server-initiated vs user-initiated cancel disambiguation).

> TODO: populate from `spike_dr_cancel.py` output

---

## §7 Interactions-specific error classes

Exception class hierarchy from `google.genai.errors` module, plus the actual exception
type + HTTP status code raised for each probed failure path:
- Invalid API key on `interactions.create`
- Unknown agent on `interactions.create`
- Unknown interaction ID on `interactions.get`

Feeds `_map_gemini_error` extension in Task 2 — specifically the discrimination between
existing error branches (401/403/404/429) that now need interaction-context-aware messages.

> TODO: populate from `spike_dr_errors.py` output

---

## §8 Updated Open Questions resolutions

Resolution status for each open question from `projects/P28-gemini-background-deep-research.md §Open questions`:

| # | Question | Status | Evidence |
|---|---|---|---|
| 1 | VCR-vs-`google-genai` transport compatibility | OPEN | Not probed by spike scripts; resolved during Task 3 cassette-recording step |
| 2 | `google-genai` version pinning strategy (`>=1.55,<2` vs loose) | OPEN | Architectural decision; not resolvable by live-API spike |
| 3 | Citation prompt-prepend workaround (auto-prepend vs rely on annotations) | TODO: populate from §4 findings | Depends on whether §4 finds a reliable citation attribute |
| 4 | Resume after retention expiry (404 shape) | TODO: populate from §7 findings | Depends on error-class probes for interactions.get |
| 5 | `extended` marker scope — `GEMINI_API_KEY` secret in Extended workflow | OPEN | Workflow YAML decision; not resolvable by API spike |
| 6 | ~~Single-agent assumption~~ | RESOLVED (pre-spike) | Two-tier agents documented 2026-05-04; see §1 for live confirmation |
| 7 | Cancel-on-Ctrl-C default | TODO: populate from §6 findings | Depends on whether cancel() preserves partial output |
| 8 | Free-tier error message URL stability (`https://ai.google.dev/pricing`) | OPEN | URL audit at implementation time |

> TODO: update each row after running the spike scripts and populating §1–§7 above
