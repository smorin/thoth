# P34 — Offline testing for OpenAIProvider.stream() (VCR or alternative)

Pragmatic offline-test approach for OpenAIProvider.stream() SSE translation, sitting between mock and live. The approach (VCR / respx / captured-JSON / other) is itself part of what this project decides.

### Open questions
- Q: VCR vs alternative offline-testing approach — VCR may not be a good fit for SSE streaming responses; need to evaluate alternatives (e.g. respx, captured-JSON fixtures, custom test doubles).
- Q: Which OpenAI model to use in the recording / fixture? Prefer smaller / faster (speed matters in the test loop) but it must be compatible with the streaming Responses API.

### Notes
Goal is pragmatic offline testing for the streaming path — somewhere between mock (which lies about wire format) and live (slow, costs API credits, runs nightly only). The deliverable is a *decision* on the offline-test approach plus the test that proves it works; not a pre-committed VCR adoption. VCR is one candidate among several and may turn out to be a poor fit for SSE.

<!-- Idea state. Minimal by convention.
     Promote with `project-refine P34` when ready. -->
