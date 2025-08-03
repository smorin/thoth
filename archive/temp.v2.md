# Thoth v9 PRD Review - Logical Consistency Analysis

## 1. F-03: @-syntax for File References

### Analysis of @-syntax
The `@/path` and `@-` syntax for referencing external files is **NOT** a widely adopted standard in CLI tools.

**Common Standards:**
- Most CLI tools use explicit flags like `--file` or `-f`
- Some tools use `<` for stdin redirection (shell feature)
- Docker uses `@` prefix for reading from files in some contexts (e.g., `docker build -t tag -f @filename`)
- curl uses `@` for file uploads (`curl -d @file.json`)

**Pros of keeping @-syntax:**
- Concise and elegant
- Allows inline file references without separate flags
- Consistent with some tools (curl, docker)
- Already implemented in code

**Cons of @-syntax:**
- Not widely recognized by users
- Could be confused with email addresses or other @ uses
- Requires documentation and user education
- Non-standard approach

**Recommendation: REMOVE F-03**
- Use standard `--query-file` flag instead
- Support stdin with explicit `--query -` or `--query-file -`
- This is more discoverable and standard

---

## 2. F-13 & F-23: Filename Format Issues

### Current Issues:
- F-13: `YYYY-MM-DD_HHMMSS_<mode>-<slug>.md` 
- F-23: Says "Generate combined report" but should be removed
- Missing provider in filename for multi-provider results

**Recommendation: UPDATE F-13 and REMOVE F-23**
- F-13 should be: `YYYY-MM-DD_HHMMSS_<mode>_<provider>_<slug>.md`
- F-23 should be removed entirely - no combined reports
- Each provider gets separate file with provider name in filename

---

## 3. N-02: Platform Support

**Current:** "Tool runs identically on macOS, Linux, Windows"

**Recommendation: UPDATE N-02**
- Change to: "Tool runs on macOS and Linux"
- Remove Windows support to simplify path handling and dependencies

---

## 4. Section 5 (Objectives) Inconsistency

Objective #8 states "Universal compatibility – run on macOS, Linux, and Windows" which conflicts with the recommended N-02 change.

**Recommendation: UPDATE Objective #8**
- Change to: "Cross-platform compatibility – run on macOS and Linux"

---

## 5. Mode Dependencies and Chaining

The configuration shows modes (clarification → exploration → deep_research) but doesn't specify:
- How modes reference previous outputs
- Default behavior for chained modes
- Command-line arguments for input files

**Recommendation: ADD new functional requirements**
```
F-26: Modes can reference previous outputs via --input-file flag
F-27: When mode specifies "next", it should automatically look for latest output from current mode
F-28: For multi-provider previous steps, use latest file from each provider as inputs
```

**Add to modes configuration:**
```toml
[modes.exploration]
provider = "openai"
model = "gpt-4o"
system_prompt = "Provide initial exploration and identify research directions."
previous = "clarification"  # Indicates this mode typically follows clarification
auto_input = true          # Automatically use latest clarification output
```

---

## 6. Section 7 (Assumptions) Issues

"File paths must be cross-platform compatible" conflicts with removing Windows support.

**Recommendation: UPDATE assumption**
- Change to: "File paths must work on POSIX systems (macOS/Linux)"

---

## 7. Section 10.2 (Usage Examples) Issues

Examples show incorrect filenames:
- Missing provider name in filename
- Shows combined report creation which should be removed

**Recommendation: UPDATE examples**
```bash
# Ad-hoc mode - saves to current directory
thoth deep_research "impact of quantum computing"
# Creates: 
#   ./2024-08-03_143022_deep_research_openai_impact-quantum.md
#   ./2024-08-03_143022_deep_research_perplexity_impact-quantum.md
```

---

## 8. Section 14 (Configuration File) Issues

Line 681: `combine_reports = true` should be removed

**Recommendation: UPDATE configuration**
- Remove `combine_reports` option entirely
- Add mode chaining configuration options

---

## 9. Section 16.2 (Status Display) Issues

Shows incorrect filename format in output example

**Recommendation: UPDATE example**
```
Output Files:
────────────
./research-outputs/quantum_research/
  └── 2024-08-03_143022_deep_research_perplexity_impact-quantum.md
```

---

## 10. Remove Section 18

**Recommendation: DELETE Section 18 (Performance Metrics)**
- As requested, remove entire Section 18
- Renumber Section 19 to Section 18

---

## Summary of Recommended Changes

1. **REMOVE F-03** - Replace @-syntax with standard --query-file flag
2. **UPDATE F-13** - Add provider to filename: `YYYY-MM-DD_HHMMSS_<mode>_<provider>_<slug>.md`
3. **REMOVE F-23** - No combined reports
4. **ADD F-26, F-27, F-28** - Mode chaining and input handling
5. **UPDATE N-02** - Support only macOS and Linux
6. **UPDATE Objective #8** - Remove Windows compatibility
7. **UPDATE Assumption** - POSIX paths only
8. **UPDATE all examples** - Show correct filename format with provider
9. **UPDATE configuration** - Remove combine_reports, add mode chaining options
10. **DELETE Section 18** - Remove Performance Metrics
11. **ADD to glossary** - Define "mode chaining" and "auto_input"

## Additional Logical Inconsistencies Found

1. **Structured output flag confusion**: The --structured flag behavior is unclear. In ad-hoc mode, files are always created, making this flag redundant.

2. **Project vs output-dir overlap**: Having both --project and --output-dir creates confusion about precedence and behavior.

3. **Missing provider fallback**: What happens if one provider fails in multi-provider mode? This isn't specified.

4. **Checkpoint frequency**: F-20 says "every 2 minutes" but this could miss fast operations or waste resources on long ones.

**Recommendations for these:**
- Clarify that --structured is only needed when you want file output instead of stdout
- Document that --output-dir overrides all other output location logic
- Add F-29: "If one provider fails in multi-provider mode, continue with others and note failure"
- Change F-20 to: "Checkpoint operations at meaningful state changes (start, provider complete, etc.)"