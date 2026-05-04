# OpenAI Deep Research
- https://cookbook.openai.com/examples/deep_research_api/introduction_to_deep_research_api
- https://platform.openai.com/docs/guides/deep-research

# UV
- https://docs.astral.sh/uv/guides/scripts/#declaring-script-dependencies

# Perplexity Sonar Deep Research
- https://docs.perplexity.ai/getting-started/models/models/sonar-deep-research
- https://docs.perplexity.ai/getting-started/models
- https://docs.perplexity.ai/guides/structured-outputs
- https://docs.perplexity.ai/guides/prompt-guide
- https://docs.perplexity.ai/guides/chat-completions-guide

# Gemini Deep Research
- https://ai.google.dev/gemini-api/docs/deep-research
- https://ai.google.dev/gemini-api/docs/interactions
- https://ai.google.dev/gemini-api/docs/gemini-for-research

# Gemini Model
- Agents (Deep Research, two-tier as of 2026-05-04):
  - `deep-research-preview-04-2026` — speed/efficiency, default for P28 v1
  - `deep-research-max-preview-04-2026` — max comprehensiveness, deferred to a successor project
- Legacy (no longer listed): `deep-research-pro-preview-12-2025`
- API: Interactions API (`/v1beta/interactions`)
- Auth header: `x-goog-api-key: $GEMINI_API_KEY`

# OpenAI model list
- https://platform.openai.com/docs/api-reference/models/list

# Perplexity Model
- `sonar-deep-research`

## TypeChecker for the Project `ty`
https://docs.astral.sh/ty/

## Linter and Formatter for the Project `ruff`
https://docs.astral.sh/ruff/

## Make example
https://github.com/smorinlabs/py-launch-blueprint/blob/main/Makefile


## openai request models
`curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"`
