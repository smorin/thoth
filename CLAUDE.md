## Development Principles
- When planning features, look at using design patterns that make it easy to keep code consistent. And then put in place best practices.

## Code Quality Assurance Workflow

After making any code changes, follow this verification workflow:

1. **Main Executable Verification** (thoth):
   ```bash
   make check    # Run lint and typecheck on main executable
   make fix      # Auto-fix any issues found
   ```

2. **Run Tests**:
   ```bash
   ./thoth_test -r  # Run the test suite to ensure functionality
   ```

3. **Test Suite Verification** (thoth_test):
   ```bash
   make test-check  # Run lint and typecheck on test suite
   make test-fix    # Auto-fix any issues in test suite
   ```

4. **Final Verification**:
   - Only consider the change complete when:
     - `make check` passes without errors
     - All tests pass
     - `make test-check` passes without errors

This ensures both the main executable and test suite maintain code quality standards.

### Test Debugging Workflow
- When a test fails, start by running the test suite with only the failing tests
- Fix the specific tests while running the subset of tests
- Once fixed, run the full test suite to ensure no regressions
- Systematically run `./thoth_test` with targeted test subsets
- Always follow the verification steps:
  1. `make check`
  2. `make fix`
  3. `./thoth_test`
  4. `make test-check`
  5. `make test-fix`
  6. Verify all tests pass in the full test suite

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

 🤖 Generated with [Claude Code](https://claude.ai/code)          

 or 

   Co-Authored-By: Claude <noreply@anthropic.com>

## API and UV References
Please check @planning/references.md URLs to look up detail about the openai, perplexity, and UV documentation.

## OpenAI API Key
get the openai api key from @openai.env