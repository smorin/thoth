# P34 — VCR cassette coverage for OpenAIProvider.stream()

Offline cassette test for OpenAIProvider.stream() SSE translation.

### Open questions
- Q: VCR vs alternative offline-testing approach — VCR may not be a good fit for SSE streaming responses; need to evaluate alternatives (e.g. respx, captured-JSON fixtures, custom test doubles).
- Q: Which OpenAI model to use in the cassette / recording? Prefer smaller / faster (speed matters in the test loop) but it must be compatible with the streaming Responses API.

### Notes
Goal is pragmatic offline testing for the streaming path — somewhere between mock (which lies about wire format) and live (slow, costs API credits, runs nightly only). VCR is the obvious starting point but may not handle SSE well; the project should evaluate the right approach before committing to an implementation, rather than picking VCR by default.

<!-- Idea state. Minimal by convention.
     Promote with `project-refine P34` when ready. -->
