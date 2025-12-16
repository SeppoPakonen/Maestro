# Reactive Fix Loop Verification - Test Checklist

## Goal
Verify that `maestro build fix` implements a controlled feedback loop that can safely attempt fixes, verify specific errors are eliminated, and automatically revert if verification fails.

## Test Cases

### 1. Easy Fix Scenario (Trivial Compile Error)
**Objective**: Verify fix loop keeps patch when targeted signature disappears

**Setup**:
- Create C++ file with trivial compile error (missing semicolon)
- Initialize git repo
- Create Maestro session

**Steps**:
1. Run `maestro build run` to generate baseline diagnostics
2. Run `maestro build fix run --target top` to attempt fix
3. Verify fix attempt is recorded with proper artifacts
4. Check that after fix, target signature is gone
5. Verify changes are kept (not reverted)
6. Confirm build succeeds after fix

**Expected Results**:
- Fix attempt recorded in `.maestro/build/fix/runs/<id>/`
- Input/output files created: `inputs/iter_1_qwen.txt`, `outputs/iter_1_qwen.txt`
- Patch files created: `patches/iter_1_before.patch`, `patches/iter_1_after.patch`
- Diagnostics before/after saved: `diagnostics_before.json`, `diagnostics_after.json`
- Fix run JSON contains proper iteration record with `patch_kept: true`
- Changes are kept in the repository

### 2. Misleading Library Error Scenario (Complex Template Error)
**Objective**: Verify fix loop reverts on failure and escalation occurs

**Setup**:
- Create C++ file with complex template/ownership issue
- Initialize git repo
- Create Maestro session

**Steps**:
1. Run `maestro build run` to generate baseline diagnostics
2. Run `maestro build fix run --target top --max-iterations 3` 
3. Verify fix attempt fails and changes are reverted
4. Check escalation to claude after 2 failed iterations on same signature
5. Verify proper revert behavior when fix doesn't work

**Expected Results**:
- Fix attempts recorded with proper artifacts
- Changes reverted when verification fails
- Escalation message logged: "Escalating fix attempt to claude (signature persisted twice)"
- Git repository state properly restored after failed attempts
- Iteration records show `patch_kept: false` and proper revert reasons

### 3. Rule Matching and Action Selection
**Objective**: Verify rule matching works with priority/confidence ordering

**Setup**:
- Create rulebook with multiple matching rules for a diagnostic
- Ensure rules have different priorities and confidence levels

**Steps**:
1. Create diagnostic that matches multiple rules
2. Run `maestro build fix run`
3. Verify best rules are selected by priority/confidence (descending)

**Expected Results**:
- Rules sorted by priority, then confidence (both descending)
- Matched rules included in AI prompt context
- Priority/confidence information recorded in fix run JSON

### 4. Target Selection Logic
**Objective**: Verify `--target` flag options work correctly

**Test Cases**:
- `--target top` (default): Selects most frequent signature
- `--target signature:<sig>`: Targets specific signature
- `--target file:<path>`: Targets signatures from specific file

**Expected Results**:
- Correct signatures selected based on target option
- Verbose mode shows selected targets with representative diagnostic messages
- Target selection logic properly implemented

### 5. Audit Trail Verification
**Objective**: Verify full audit trail exists per iteration

**Checkpoints**:
- [ ] `fix_run.json` contains iteration records with all required fields:
  - iteration index
  - selected target signatures  
  - matched rule IDs
  - model used
  - patch info (kept/reverted)
  - verification result
  - new signatures introduced
- [ ] Input files saved as `inputs/iter_<n>_<model>.txt`
- [ ] Output files saved as `outputs/iter_<n>_<model>.txt`
- [ ] Patch files saved as `patches/iter_<n>_before.patch` and `patches/iter_<n>_after.patch`
- [ ] Diagnostics saved as `diagnostics_before.json` and `diagnostics_after.json`

### 6. Escalation Policy
**Objective**: Verify deterministic escalation to claude

**Setup**:
- Create diagnostic that persists across multiple iterations
- Configure rulebook that doesn't resolve the issue

**Steps**:
1. Run fix loop with same persistent signature
2. Verify escalation after 2 failed iterations on same signature
3. Check log message: "Escalating fix attempt to claude (signature persisted twice)"

**Expected Results**:
- Model used changes from qwen to claude after 2 failed attempts
- Proper escalation logging
- Continues to use escalated model for that signature

### 7. User-Facing Summaries
**Objective**: Verify iteration summaries are printed correctly

**Expected Format**:
```
[maestro] Fix iter 2/5 | model=qwen | target=3a1b… (2 errors)
Result: reverted (signature still present)
Errors: 7 -> 7 | New signatures: 1
```

**Checkpoints**:
- [ ] Shows iteration number / limit
- [ ] Shows targeted signatures
- [ ] Shows model used
- [ ] Shows kept or reverted
- [ ] Shows errors before/after counts
- [ ] Shows new signature count

### 8. Keep/Revert Policy
**Objective**: Verify changes are kept only when verification passes

**Scenarios**:
- Success: When target signatures disappear → changes kept
- Failure: When signatures remain → changes reverted
- Worse: When new errors appear → changes reverted

**Expected Results**:
- Git repository state properly maintained
- Changes reverted using checkpoint mechanism
- No lingering changes after failed fixes
- Proper model checkpoint and restore using git

### 9. Output Streaming and Quiet Mode
**Objective**: Verify proper streaming/quiet behavior

**Scenarios**:
- With `--stream-ai-output` and without `--quiet`: stream model stdout during attempts
- With `--quiet`: no streaming, but all outputs saved

**Expected Results**:
- Streaming works as expected when enabled
- Quiet mode suppresses iteration summaries
- All outputs still saved to files regardless of mode

## Manual Verification Steps

### Before Testing
1. Ensure git repo is initialized in test directory
2. Create a Maestro session file
3. Configure build pipeline to use Makefile or simple build command

### During Testing
1. Run each scenario and observe console output
2. Check file system for proper artifact creation
3. Verify git history shows proper commit states before/after fixes
4. Examine JSON files for proper data structure

### After Testing
1. Verify all expected files were created
2. Confirm data integrity in JSON files
3. Test manual inspection of patch files
4. Validate git state restoration worked properly

## Success Criteria
- All test cases pass
- Full audit trail exists for each iteration
- Changes kept only when verification passes
- Changes reverted when verification fails
- Proper escalation from qwen to claude
- User-facing summaries match expected format
- Git repository state properly maintained throughout