Always check CLAUDE.md for appropriate rules

## Development Principles
- When planning features, look at using design patterns that make it easy to keep code consistent. And then put in place best practices.


## Code Quality Assurance Workflow

After making any code changes, follow this verification workflow:

1. **Main Executable Verification** (thoth):
   ```bash
   make env-check  # Verify bootstrap dependencies are installed
   just fix        # Auto-fix any issues found
   just check      # Run lint and typecheck on main executable
   ```

2. **Run Tests**:
   ```bash
   ./thoth_test -r  # Run the test suite to ensure functionality
   ```

3. **Test Suite Verification** (thoth_test):
   ```bash
   just test-fix        # Auto-fix any issues in test suite
   just test-lint       # Run lint on test suite
   just test-typecheck  # Run typecheck on test suite
   ```

4. **Final Verification**:
   - Only consider the change complete when:
     - `make env-check` passes without errors
     - `just check` passes without errors
     - All tests pass
     - `just test-lint` passes without errors
     - `just test-typecheck` passes without errors

This ensures both the main executable and test suite maintain code quality standards.

### Test Debugging Workflow
- When a test fails, start by running the test suite with only the failing tests
- Fix the specific tests while running the subset of tests
- Once fixed, run the full test suite to ensure no regressions
- Systematically run `./thoth_test` with targeted test subsets
- Always follow the verification steps:
  1. `make env-check`
  2. `just fix`
  3. `just check`
  4. `./thoth_test`
  5. `just test-fix`
  6. `just test-lint`
  7. `just test-typecheck`
  8. Verify all tests pass in the full test suite

## Planning Documents Management

### Location and Structure
- **Primary Planning Directory**: `planning/`
  - This is where all active planning documents should be stored
  - Always check this directory for the latest versions of planning documents
  - Key documents include PRDs (Product Requirements Documents) and implementation plans

### Versioning Format
Planning documents follow this versioning format:
- **PRD Documents**: `thoth.prd.vXX.md` (e.g., `thoth.prd.v22.md`)
- **Plan Documents**: `thoth.plan.vX.md` (e.g., `thoth.plan.v5.md`)
- **Other Documents**: `[name].vX.md` (e.g., `temp.v5.md`)

### Version Detection and Incrementing
1. **Finding Latest Version**:
   - List files in `planning/` directory
   - Use regex pattern: `thoth\.(prd\.)?v([0-9]+)\.md`
   - Extract version numbers and find the highest

2. **Creating New Version**:
   - Increment the highest version number by 1
   - For PRDs: `thoth.prd.v[N+1].md`
   - For Plans: `thoth.plan.v[N+1].md`

### Archiving Process
When creating a new version:
1. Create the new version in `planning/` directory
2. After completing updates to the new version:
   - Move the old version to `archive/` directory using git commands:
   ```bash
   git mv planning/thoth.prd.v22.md archive/
   git mv planning/thoth.plan.v5.md archive/
   ```
3. Commit both the move and the new file:
   ```bash
   git add planning/thoth.prd.v23.md
   git commit -m "Archive v22 PRD and create v23 PRD"
   ```

### References Location
- **References Document**: `planning/references.md`
  - Contains API documentation links and external references
  - Should be checked for OpenAI, Perplexity, and UV documentation

## Git Best Practices

Never say in commits:

 🤖 Generated with [Codex](https://Codex.ai/code)

 or

   Co-Authored-By: Codex <noreply@anthropic.com>

## API and UV References
Please check @planning/references.md URLs to look up detail about the openai, perplexity, and UV documentation.

## OpenAI API Key
get the openai api key from @openai.env

# Test-driven development.

- Always when creating an implementation plan, make the first thing to design the tests for each task and the milestone. The testing design should be the first step. Then, in the implementation, either a test should be created and then the code updated to pass, or a series of tests should be created and then implementation should pass them all. But it should be test-driven development.
