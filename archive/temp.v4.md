# Thoth v11 - Outstanding Questions and Issues

## Summary

After applying all recommendations from temp.v3.md to create thoth.v11.md, most logical inconsistencies have been resolved. However, a few questions remain that may require further clarification or design decisions.

---

## 1. Mode Chaining "next" Field Purpose

### Current State
The "next" field in mode configuration has been clarified as a hint for users about what mode to run next, but it's not used programmatically for automatic chaining.

### Outstanding Question
- Should the "next" field be removed entirely from the configuration to avoid confusion?
- Or should it be renamed to something clearer like "suggested_next_mode" or "user_hint"?

### Example from Config
```toml
[modes.exploration]
previous = "clarification"
next = "deep_research"  # This is just a hint, not used for chaining
```

---

## 2. Provider Selection Precedence

### Current State
The PRD mentions that multi-provider modes can have providers overridden via command line, but the exact precedence rules aren't fully specified.

### Outstanding Questions
- When using `--provider openai` with a multi-provider mode like deep_research, does it:
  a) Replace all providers with just OpenAI?
  b) Filter to only use OpenAI from the configured list?
  c) Fail with an error?

- Should there be a way to specify multiple providers on the command line?
  - e.g., `--providers openai,anthropic` (note plural)

---

## 3. Auto-input File Discovery Pattern

### Current State
F-35 now specifies "strict pattern matching" for finding output files, but the exact pattern isn't documented.

### Outstanding Questions
- What constitutes a "valid" output file for auto-input?
- Should the pattern include:
  - Operation ID matching?
  - Provider name matching?
  - Time window constraints?
  - File size/content validation?

### Example Scenario
```bash
# First command creates:
2024-08-03_143022_exploration-quantum-computing_openai.md
2024-08-03_143022_exploration-quantum-computing_perplexity.md

# Second command with auto-input - which files match?
thoth deep_research --auto --previous exploration
```

---

## 4. Combined Report Generation

### Current State
F-23 mentions "Generate combined report from multi-provider results" but details are sparse.

### Outstanding Questions
- When is a combined report generated?
  - Always for multi-provider modes?
  - Only when a flag is specified?
  - Based on config setting?

- How are conflicting information from providers handled?
- What's the filename pattern for combined reports?
  - `*_combined.md`?
  - No provider suffix?

---

## 5. Progress Tracking Implementation

### Current State
F-36 requires detailed progress tracking with elapsed time and polling information.

### Outstanding Questions
- How granular should progress updates be?
- Should progress percentages be:
  - Estimated based on typical operation times?
  - Reported by the provider APIs if available?
  - Simple elapsed/total time calculations?

- What happens if a provider doesn't support progress reporting?

---

## 6. Error Recovery Scenarios

### Current State
F-32 and F-33 cover basic error handling for mode chaining, but some scenarios are unclear.

### Outstanding Questions
- What happens if:
  - A checkpoint file is corrupted?
  - Disk space runs out during operation?
  - Network connectivity is lost mid-operation?
  - User's API quota is exceeded?

- Should there be automatic retry for specific error types?
- How are partial results handled in failure scenarios?

---

## 7. Configuration Migration

### Not Addressed
The PRD doesn't discuss configuration versioning or migration.

### Outstanding Questions
- What happens when thoth is updated and config schema changes?
- Should there be:
  - Automatic migration?
  - Version field in config.toml?
  - Backward compatibility guarantees?

---

## 8. Platform-Specific Paths

### Current State
The PRD now correctly states POSIX-only support, but some questions remain.

### Outstanding Questions
- Should paths in config.toml use:
  - Forward slashes only?
  - Platform-native separators?
  - Both with automatic conversion?

- How are symlinks handled in paths?

---

## 9. Stdin Content Size Limits

### Current State
F-28 mentions stdin support for queries via `--query-file -`.

### Outstanding Questions
- Is there a maximum size limit for stdin input?
- How are binary inputs handled/rejected?
- Should multi-line stdin be supported for queries?

---

## 10. Operation ID Uniqueness

### Current State
Operation IDs use timestamp + 8-char UUID suffix.

### Outstanding Questions
- What's the collision probability with 8 characters?
- Should the UUID portion be longer for better uniqueness?
- How are ID collisions handled if they occur?

---

## Recommendations for Resolution

1. **Remove or rename the "next" field** to avoid confusion
2. **Document exact provider selection behavior** with examples
3. **Specify the complete file matching pattern** for auto-input
4. **Clarify combined report generation rules** and naming
5. **Define progress tracking requirements** more precisely
6. **Add comprehensive error handling scenarios** to the PRD
7. **Consider adding configuration versioning** for future compatibility
8. **Specify path handling rules** for the POSIX environment
9. **Document stdin limitations** if any
10. **Evaluate operation ID uniqueness** requirements

---

## Minor Documentation Improvements

While not logical issues, these could improve clarity:

1. Add more examples showing multi-provider vs single-provider operations
2. Include sample output showing the progress display format
3. Add a troubleshooting section for common issues
4. Clarify whether "thinking" mode supports multiple providers
5. Document the exact checkpoint file format/schema

These outstanding questions don't prevent implementation but addressing them would make the specification more complete and reduce ambiguity during development.