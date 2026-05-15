# Milestone 5: Async Operations & Lifecycle Management - Manual Testing

**Date**: 2026-03-15
**Milestone**: M5 - Async Operations
**Features Tested**: F-67 (Operation Lifecycle), F-82 (Checkpoint Corruption Recovery), Async Mode, Status/List Commands

---

## Prerequisites

```bash
# Ensure you're in the doxa-research project directory
cd /path/to/doxa-research

# Source API key (needed for provider tests only)
source openai.env

# Verify doxa-research is executable
./doxa --version
```

---

## Part A: Operation Lifecycle State Machine

### Test A-1: Valid States and Transitions (queued → running → completed)

Run a synchronous research operation with the mock provider and verify it transitions through all states.

```bash
# Run a synchronous mock research
./doxa "test lifecycle manual" --provider mock -v
```

**Expected Result**:
- Output shows progress bar (running state)
- Final output: `✓ Research completed!`
- A markdown file is created: `*_mock_*.md`
- Exit code: 0

```bash
# Verify output file exists
ls -la *_mock_*test-lifecycle-manual*.md

# Clean up
rm -f *_mock_*test-lifecycle-manual*.md
```

### Test A-2: Async Mode Returns Immediately in Queued State

```bash
# Run with --async flag
./doxa "test async manual" --async --provider mock
```

**Expected Result**:
- Output: `✓ Research submitted`
- Output contains `Operation ID: research-YYYYMMDD-HHMMSS-<uuid>`
- Output contains `Check status: doxa-research status research-...`
- Returns immediately (< 1 second)
- Exit code: 0

**Save the Operation ID** for use in later tests:
```bash
# Capture the operation ID
OP_ID=$(./doxa "test async capture" --async --provider mock 2>&1 | grep "Operation ID:" | awk '{print $NF}')
echo "Captured Operation ID: $OP_ID"
```

### Test A-3: Verify Queued State via Status Command

```bash
# Check the async operation status (should be "queued" since async doesn't execute)
./doxa status $OP_ID
```

**Expected Result**:
- Displays `Operation Details:` header
- Shows `Status: queued`
- Shows the prompt text
- Shows mode: `default`
- Exit code: 0

### Test A-4: Verify Completed State After Sync Execution

```bash
# Run synchronous operation
./doxa "test completed state" --provider mock -v

# Get the operation ID from the most recent checkpoint
COMPLETED_ID=$(ls -t ~/.config/doxa-research/checkpoints/*.json | head -1 | xargs basename .json)
echo "Completed Operation ID: $COMPLETED_ID"

# Check its status
./doxa status $COMPLETED_ID
```

**Expected Result**:
- Status shows `Status: completed`
- Shows elapsed time
- Provider status shows `✓ Completed` for mock
- Exit code: 0

```bash
# Clean up output files
rm -f *_mock_*test-completed-state*.md
```

---

## Part B: Checkpoint Persistence

### Test B-1: Checkpoint Survives Process Exit

This verifies that checkpoint data persists across separate doxa-research invocations.

```bash
# Step 1: Create an operation (async so it stays in queued state)
./doxa "checkpoint persistence test" --async --provider mock
# Note the Operation ID displayed

# Step 2: In a NEW invocation, check the status
./doxa status <OPERATION_ID_FROM_STEP_1>
```

**Expected Result**:
- Step 2 successfully loads the checkpoint from a different process
- Displays the operation prompt: `checkpoint persistence test`
- Shows `Status: queued`
- Exit code: 0

### Test B-2: Checkpoint File Location

```bash
# Verify checkpoint files exist in the expected directory
ls -la ~/.config/doxa-research/checkpoints/

# Inspect a checkpoint file
cat ~/.config/doxa-research/checkpoints/$(ls ~/.config/doxa-research/checkpoints/ | head -1)
```

**Expected Result**:
- Checkpoint directory exists at `~/.config/doxa-research/checkpoints/`
- Files are named `<operation-id>.json`
- JSON content contains: id, prompt, mode, status, created_at, updated_at, providers, output_paths

### Test B-3: Atomic Write Verification

```bash
# Run a research operation and check that no partial files exist
./doxa "atomic write test" --provider mock

# Check for temp files (should be none)
ls ~/.config/doxa-research/checkpoints/*.tmp 2>/dev/null
echo "Temp files found: $?"
```

**Expected Result**:
- No `.tmp` files remain in the checkpoint directory
- The checkpoint file for this operation is valid JSON

```bash
rm -f *_mock_*atomic-write-test*.md
```

---

## Part C: Checkpoint Corruption Recovery (F-82)

### Test C-1: Corrupted JSON Checkpoint

```bash
# Step 1: Create a corrupted checkpoint file
mkdir -p ~/.config/doxa-research/checkpoints
echo "{this is not valid json!!!" > ~/.config/doxa-research/checkpoints/test-corrupt-manual.json

# Step 2: Try to load it
./doxa status test-corrupt-manual
```

**Expected Result**:
- Output contains: `Warning: Checkpoint file corrupted:`
- Output contains: `Creating new checkpoint. Previous state lost.`
- Output contains: `Error: Operation test-corrupt-manual not found`
- The corrupted file is deleted automatically
- Exit code: 6

```bash
# Verify corrupted file was cleaned up
ls ~/.config/doxa-research/checkpoints/test-corrupt-manual.json 2>/dev/null
echo "File exists: $?"
# Expected: "File exists: 2" (file not found)
```

### Test C-2: Missing Checkpoint

```bash
# Try to get status of a non-existent operation
./doxa status nonexistent-operation-12345
```

**Expected Result**:
- Output: `Error: Operation nonexistent-operation-12345 not found`
- Exit code: 6

### Test C-3: Empty Checkpoint File

```bash
# Create an empty checkpoint file
echo "" > ~/.config/doxa-research/checkpoints/test-empty-manual.json

# Try to load it
./doxa status test-empty-manual
```

**Expected Result**:
- Warning about corrupted checkpoint displayed
- Empty file is removed
- Exit code: 6

```bash
# Clean up
rm -f ~/.config/doxa-research/checkpoints/test-empty-manual.json
```

---

## Part D: Status Command

### Test D-1: Status Without Operation ID Shows Error

```bash
./doxa status
```

**Expected Result**:
- Output: `Error: status command requires an operation ID`
- Exit code: 1

### Test D-2: Status Shows Full Operation Details

```bash
# Create a completed operation first
./doxa "detailed status test" --provider mock

# Get the most recent operation ID
RECENT_ID=$(ls -t ~/.config/doxa-research/checkpoints/*.json | head -1 | xargs basename | sed 's/.json//')

# Show status
./doxa status $RECENT_ID
```

**Expected Result**:
- Shows `Operation Details:` header with separator line
- Shows `ID:` matching the operation ID
- Shows `Prompt:` with the original prompt text
- Shows `Mode:` (default)
- Shows `Status:` (completed)
- Shows `Started:` with formatted timestamp
- Shows `Elapsed:` with duration
- Shows `Provider Status:` section with `Mock: ✓ Completed`
- Exit code: 0

```bash
rm -f *_mock_*detailed-status-test*.md
```

---

## Part E: List Command

### Test E-1: List Shows Recent Operations

```bash
# Create a few operations to populate the list
./doxa "list test one" --async --provider mock
./doxa "list test two" --async --provider mock
./doxa "list test three" --provider mock

# List recent operations
./doxa list
```

**Expected Result**:
- Displays a table with header `Research Operations`
- Columns: ID, Prompt, Status, Elapsed, Mode
- Shows the recently created operations
- Operations sorted by creation time (newest first)
- Exit code: 0

```bash
rm -f *_mock_*list-test-three*.md
```

### Test E-2: List With --all Flag

```bash
./doxa list --all
```

**Expected Result**:
- Shows all operations (including those older than 24 hours)
- Same table format as E-1
- Exit code: 0

### Test E-3: List Shows Correct Status Values

```bash
./doxa list
```

**Expected Result**:
- Async operations show status: `queued`
- Completed operations show status: `completed`
- Status column correctly reflects each operation's lifecycle state

---

## Part F: Error Handling and Failed State

### Test F-1: Invalid Provider Triggers Error

```bash
./doxa "test invalid provider" --provider nonexistent
```

**Expected Result**:
- Error message about invalid/unknown provider
- Operation does NOT remain in "running" state
- Exit code: non-zero

### Test F-2: Cancellation via Ctrl+C

```bash
# Start a long-running operation and cancel it
./doxa "very long detailed research on quantum computing" --provider mock &
DOXA_PID=$!
sleep 1
kill -INT $DOXA_PID
wait $DOXA_PID 2>/dev/null
```

**Expected Result**:
- Operation is interrupted gracefully
- If checkpoint was saved, status should show `cancelled` (not `running` or `interrupted`)

---

## Part G: State Machine Validation

### Test G-1: Verify All Valid States Are Recognized

Create checkpoint files for each valid state and verify they display correctly:

```bash
for STATE in queued running completed failed cancelled; do
  cat > ~/.config/doxa-research/checkpoints/test-state-${STATE}.json << EOF
{
  "id": "test-state-${STATE}",
  "prompt": "state test ${STATE}",
  "mode": "default",
  "status": "${STATE}",
  "created_at": "2026-03-15T10:00:00",
  "updated_at": "2026-03-15T10:05:00",
  "providers": {"mock": {"status": "completed"}},
  "output_paths": {},
  "error": null,
  "progress": 0.5,
  "project": null,
  "input_files": []
}
EOF
  echo "--- Status for state: ${STATE} ---"
  ./doxa status test-state-${STATE}
  echo ""
done
```

**Expected Result**:
- Each state is displayed correctly in the status output
- No errors for any valid state
- All show exit code: 0

```bash
# Clean up
for STATE in queued running completed failed cancelled; do
  rm -f ~/.config/doxa-research/checkpoints/test-state-${STATE}.json
done
```

---

## Cleanup

After all tests are complete, clean up test artifacts:

```bash
# Remove test checkpoint files
rm -f ~/.config/doxa-research/checkpoints/test-*.json

# Remove any test output files
rm -f *_mock_*.md

# List remaining checkpoints to verify cleanup
ls ~/.config/doxa-research/checkpoints/
```

---

## Summary Checklist

| Test | Description | Pass/Fail |
|------|-------------|-----------|
| A-1 | Sync lifecycle: queued → running → completed | |
| A-2 | Async returns immediately with operation ID | |
| A-3 | Queued state visible via status command | |
| A-4 | Completed state preserved after execution | |
| B-1 | Checkpoint persists across process exits | |
| B-2 | Checkpoint files in correct location | |
| B-3 | Atomic writes leave no temp files | |
| C-1 | Corrupted JSON detected and cleaned up | |
| C-2 | Missing checkpoint returns proper error | |
| C-3 | Empty checkpoint handled gracefully | |
| D-1 | Status without ID shows error | |
| D-2 | Status shows full operation details | |
| E-1 | List shows recent operations in table | |
| E-2 | List --all shows all operations | |
| E-3 | List shows correct status values | |
| F-1 | Invalid provider triggers error | |
| F-2 | Ctrl+C sets cancelled state | |
| G-1 | All 5 valid states display correctly | |

**Tester**: _______________
**Date**: _______________
**Result**: _____ / 18 passed
