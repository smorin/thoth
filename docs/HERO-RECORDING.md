# Re-recording the README hero asciinema

Step-by-step guide for re-recording `docs/assets/hero.svg` (or `hero.gif`).
The currently-shipped recording was made before the standardization sweep
landed; this doc reflects the workflow that works against the
post-standardization CLI (`all_deep_research`, `openai_quick`, the new
preflight validations, the corrected default destinations).

The result is a ~60-90s animated asset embedded inline in the top-level
`README.md` showing parallel multi-provider Deep Research from one
command.

## Phase 1 — Install tools

```bash
brew install asciinema agg
npm install -g svg-term-cli           # only needed if you want SVG output
brew install uv                        # if not already installed
```

Verify:

```bash
asciinema --version    # 3.x writes v3 casts
agg --version
uv --version
```

**Important gotcha to remember.** asciinema 3.x writes v3 casts, but
`svg-term-cli` only accepts v1/v2 (last published 2021). You need to
convert before rendering SVG:

```bash
asciinema convert -f asciicast-v2 in.cast out.v2.cast
```

`agg` (the GIF renderer) handles v3 natively — no conversion needed.

## Phase 2 — Prep a clean terminal

Open a **fresh** terminal window. Do not reuse your dev session.

```bash
printf '\e[8;24;100t'             # resize to 24×100 (or whatever your style)
export PS1='$ '                    # bash — no username, no hostname
export PROMPT='$ '                 # zsh — same
cd "$(mktemp -d -t doxa-demo)"
clear
```

The `PS1='$ '` and `mktemp -d` matter — without them, every prompt frame
of the cast will leak your local username and hostname into a public
asset. (This was the root cause of the original cast's
PII-in-repo issue.)

## Phase 3 — Pick the demo content

Two viable demos. Pick one.

### Option A — Shell-parallel immediate `*_quick` modes (visual parallelism) ⭐

```bash
ASK_PROMPT="Compare Paxos, Raft, and Viewstamped Replication. Three bullets each."
mkdir -p research-outputs
uvx doxa-research ask --provider perplexity --mode perplexity_quick --out research-outputs/perplexity.md "$ASK_PROMPT" &
uvx doxa-research ask --provider gemini     --mode gemini_quick     --out research-outputs/gemini.md     "$ASK_PROMPT" &
uvx doxa-research ask --provider openai     --mode openai_quick     --out research-outputs/openai.md     "$ASK_PROMPT"
ls research-outputs/
head -50 research-outputs/openai.md
```

Wall-clock ~10–20s. Three files at the end. Shell job-control output
(`[1] done`, `[2] done`) visually proves parallelism during the wait.
This is the recommended approach for the hero — real output flows
through, shorter total time, doesn't require explaining "why are we
waiting 15 minutes."

### Option B — Single command via `all_deep_research --async`

```bash
uvx doxa-research providers list
uvx doxa-research ask --mode all_deep_research --async \
  "Compare Paxos, Raft, and Viewstamped Replication."
uvx doxa-research list
```

Wall-clock ~5–10s total. Submits three Deep Research jobs concurrently,
returns one operation ID covering all three providers, then `doxa list`
shows the in-flight operation. Doesn't show actual research output
(DR takes 5–15 min) but tells the whole multi-provider fan-out story
in 3 commands.

## Phase 4 — Pre-flight checklist (every time, before `asciinema rec`)

```bash
# 1. Confirm provider keys are present but won't be printed
env | grep -E "API_KEY|TOKEN|SECRET" >/dev/null && echo "keys present"

# 2. Warm uvx's cache so the recording doesn't capture a wheel download
uvx doxa-research --version          # may take 5-10s the first time
uvx doxa-research --version          # second must be <0.5s

# 3. Confirm all three providers are configured
uvx doxa-research providers list

# 4. Confirm the new modes exist in the published binary you're running
#    (if PyPI doesn't yet ship your new modes, the demo command errors
#     with ModeNotFoundError thanks to commit 0bcea0f — good)
uvx doxa-research modes list --kind immediate | grep -E "openai_quick|perplexity_quick|gemini_quick"

# 5. Full smoke-test of the demo command from Phase 3 (Option A shown)
ASK_PROMPT="Compare Paxos, Raft, and Viewstamped Replication. Three bullets each."
mkdir -p research-outputs
uvx doxa-research ask --provider perplexity --mode perplexity_quick --out research-outputs/perplexity.md "$ASK_PROMPT" &
uvx doxa-research ask --provider gemini     --mode gemini_quick     --out research-outputs/gemini.md     "$ASK_PROMPT" &
uvx doxa-research ask --provider openai     --mode openai_quick     --out research-outputs/openai.md     "$ASK_PROMPT"
ls -la research-outputs/              # must show 3 fresh .md files
head -50 research-outputs/openai.md   # eyeball content quality

# 6. Clean up smoke-test artifacts so the recording starts fresh
rm research-outputs/*
clear
```

Verify before recording:

- [ ] All three files appeared
- [ ] Each has substantive content (not just frontmatter)
- [ ] Total wall-clock under ~30s
- [ ] No errors, no empty files
- [ ] The `openai_quick` smoke shows `gpt-4.1-mini` with web search grounding working
- [ ] Step 4 listed all three `*_quick` modes — if not, the PyPI binary doesn't have them yet and you need to either publish first or use `uv run` against your local checkout
- [ ] **No username or hostname visible in your prompt** (Phase 2 setup)

## Phase 5 — Rehearse the script (silent, no recording)

Type the full sequence with no recording active. Aim for 60–90s total.
Type at ~80 wpm — fast typing reads as canned.

```text
$ uvx doxa-research providers list
[pause ~2s — let viewer see ✓ ✓ ✓]
$ ASK_PROMPT="Compare Paxos, Raft, and Viewstamped Replication. Three bullets each."
$ mkdir -p research-outputs
$ uvx doxa-research ask --provider perplexity --mode perplexity_quick --out research-outputs/perplexity.md "$ASK_PROMPT" &
$ uvx doxa-research ask --provider gemini     --mode gemini_quick     --out research-outputs/gemini.md     "$ASK_PROMPT" &
$ uvx doxa-research ask --provider openai     --mode openai_quick     --out research-outputs/openai.md     "$ASK_PROMPT"
[10-20s blocking foreground run — shell prints `[1] done`, `[2] done` mid-wait]
$ ls research-outputs/
$ head -50 research-outputs/openai.md
[Ctrl-D to end]
```

The visual narrative: viewer sees two background jobs spawn, then a
foreground that blocks. During the wait, the shell prints `[1] done`
and `[2] done` as perplexity/gemini finish. When openai returns, the
prompt comes back, `ls` shows three files, and `head` reveals the
content. Total ~60–90s.

For Option B, the script is much shorter and you can skip rehearsal.

## Phase 6 — Record

```bash
mkdir -p docs/assets
asciinema rec \
  --title "Doxa Research — parallel Deep Research from one command" \
  --cols 100 --rows 24 \
  --idle-time-limit 2 \
  docs/assets/hero.cast
```

`--idle-time-limit 2` compresses any pause >2s to exactly 2s — your
safety net for natural hesitation. No editor needed.

Run the rehearsed script. End with `Ctrl-D` (or `exit`).

## Phase 7 — Play back and decide

```bash
asciinema play docs/assets/hero.cast
```

Approve only if:

- [ ] No typos
- [ ] No env-var / path / hostname / API-key leak in any frame
- [ ] All three jobs completed visibly
- [ ] Final `head` shows substantive content
- [ ] Total runtime feels brisk

Anything off → `rm docs/assets/hero.cast` and re-record. Always faster
than editing the cast.

## Phase 8 — Render

### GIF (simpler, autoplays on GitHub reliably)

```bash
agg --font-size 14 \
    --theme monokai \
    --speed 1 \
    docs/assets/hero.cast \
    docs/assets/hero.gif

open docs/assets/hero.gif
```

Tweaks:

- Colors washed out → `--theme dracula` or `--theme solarized-dark`
- GIF over ~2 MB → raise `--font-size` (smaller font = smaller GIF) or
  use `--speed 1.3`

### SVG (smaller file, may not always animate on GitHub camo)

Convert v3 → v2 first because `svg-term-cli` doesn't accept v3:

```bash
asciinema convert -f asciicast-v2 docs/assets/hero.cast docs/assets/hero.v2.cast
svg-term --in docs/assets/hero.v2.cast \
  --out docs/assets/hero.svg \
  --window \
  --no-cursor \
  --width 100 --height 24
rm docs/assets/hero.v2.cast    # intermediate, regeneratable
```

## Phase 9 — Embed and commit

The README already embeds `docs/assets/hero.svg`. Re-recording
overwrites that file in place — no README edit needed.

If you switch GIF ↔ SVG, change the embed in README:

```markdown
![Doxa Research fanning out to OpenAI, Perplexity, and Gemini in parallel](docs/assets/hero.gif)
```

Commit:

```bash
git add docs/assets/hero.cast docs/assets/hero.svg     # or .gif
git commit -m "docs(readme): re-record asciinema hero with sanitized PS1"
```

## Phase 10 — Verify on GitHub

```bash
git push
gh pr view --web      # if there's a PR
```

Eyeball the rendered README:

- [ ] Demo plays without click
- [ ] No env-var / path / hostname / API-key leak in any frame
- [ ] Fits the README content column on desktop
- [ ] Mobile (narrow browser) renders reasonably
- [ ] Loops gracefully (agg loops by default; svg-term plays once then stops)

If the SVG renders static (no animation): GitHub's camo image proxy
occasionally strips SMIL. Fallback is the GIF path. The committed
`.cast` makes re-rendering a one-command redo.

## Known gotchas

- **asciinema v3 → svg-term-cli v2 conversion** — `svg-term-cli` was
  last published in 2021 and doesn't know about asciicast v3. Always
  convert first when rendering SVG. `agg` handles v3 natively.

- **PII in prompt** — Default shells include username and hostname in
  PS1. The `PS1='$ '` step in Phase 2 strips both. Verify with
  `echo $PS1` before recording.

- **Lengthy modes list** — `doxa modes list` now emits 30+ entries.
  If you record a `/mode` listing, pty buffering can throttle output
  past the ~24-row screen height. Avoid listing the full catalog in
  a hero recording; the providers list (`doxa providers list`) is
  short and demo-friendly.

- **uvx cold-cache** — First `uvx doxa-research` after install
  downloads the wheel and resolves dependencies (5–10s). Warm the
  cache before recording so the cast doesn't capture a wheel download.

- **PyPI lag** — If your demo uses features that haven't been
  published to PyPI yet, `uvx doxa-research` will run the published
  version, not your local checkout. Either publish first, or swap
  `uvx doxa-research` → `uv run doxa-research` to use your tree.

## See also

- [README.md](../README.md) — where the rendered asset is embedded
- [docs/COMMANDS.md](COMMANDS.md) — full CLI surface; modes catalog
- [docs/providers.md](providers.md) — per-provider configuration
