# P38 - Perplexity Sync VCR Replay

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)
- **Predecessor:** P23 (`projects/P23-perplexity-immediate-sync.md`) - implements Perplexity synchronous immediate calls without depending on cassette replay.
- **Related:** `thoth_vcr.md`
- **Related:** `tests/test_vcr_openai.py`
- **Related:** `thoth_test_cassettes/`

**Status:** `[ ]` Scoped, not started.

**Goal**: Add offline VCR replay coverage for Perplexity synchronous Sonar calls after sanitized Perplexity cassettes are available.

### Scope

- Add Perplexity sync cassette replay tests for the P23 immediate provider path.
- Use the repo's existing `tests/conftest.py` VCR setup with `record_mode = "none"`.
- Mirror the useful parts of `tests/test_vcr_openai.py`, adjusted for a one-shot synchronous Sonar response rather than OpenAI background polling.
- Verify answer text, model/id shape, deduped sources, and no live network dependency.
- P38 is a follow-up only. P23 must not block on P38.

### Out of scope

- Implementing Perplexity provider behavior - P23.
- Recording/sanitizing the source cassette in `deepresearch_replay`.
- Perplexity background/deep-research replay - P27.

### Tests & Tasks

- [ ] [P38-TS01] Design cassette replay assertions for Perplexity sync happy path: submit/get_result output, source extraction, no live network, and stable sanitized cassette data.
- [ ] [P38-T01] Add `thoth_test_cassettes/perplexity/sync-happy-path.yaml` after the sanitized cassette is available.
- [ ] [P38-T02] Add `tests/test_vcr_perplexity_sync.py` using the existing shared VCR fixture.
- [ ] [P38-T03] Wire any needed `just test-vcr` or docs updates if the existing VCR command does not pick up the new file.
- [ ] [P38-T04] Run VCR tests and update this project/trunk status.

### Acceptance Criteria

- `uv run pytest tests/test_vcr_perplexity_sync.py -v` passes without live network access.
- Default pytest remains offline and deterministic.
- P23 remains complete even if P38 is not started.

### Definition of Done

- All P38 tasks are checked.
- The Perplexity cassette is sanitized and committed.
- VCR replay passes with `record_mode = "none"`.
