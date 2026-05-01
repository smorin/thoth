# P05 — VCR Cassette Replay Tests (v2.6.0)

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)

**Status:** `[x]` Completed (v2.6.0).

**Goal**: Add pytest-based VCR cassette replay tests that exercise OpenAIProvider against recorded API traffic, using Option B (separate pytest test file) from thoth_vcr.md.

**Out of Scope**
- Gemini/Perplexity cassettes (blocked on deepresearch_replay P03/P04)
- Integration into thoth_test runner (Option A rejected)

### Tests & Tasks
- [x] [P05-T01] Add pytest and vcrpy to dev dependencies
- [x] [P05-T02] Create tests/conftest.py with shared VCR configuration
- [x] [P05-TS01] VCR-OAI-SUBMIT: submit() returns response ID from cassette
- [x] [P05-TS02] VCR-OAI-SUBMIT: submit() returns exact cassette ID
- [x] [P05-TS03] VCR-OAI-SUBMIT: submit() stores job info with background=True
- [x] [P05-TS04] VCR-OAI-POLL: first check_status() returns queued/in_progress
- [x] [P05-TS05] VCR-OAI-POLL: polling reaches completed status
- [x] [P05-TS06] VCR-OAI-RESULT: get_result() returns substantial text
- [x] [P05-TS07] VCR-OAI-RESULT: get_result() contains domain-relevant content
- [x] [P05-T03] Add test-vcr justfile recipe and wire into just all
- [x] [P05-T04] Update PROJECTS.md

### Automated Verification
- `make check` passes
- `just test-vcr` → 7/7 pass
- `just all` completes without errors

### Regression Test Status
- [x] All existing thoth_test tests still pass
- [x] VCR tests run in `record_mode="none"` — no live API calls
