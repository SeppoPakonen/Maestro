# Build Show/Status Reliability Regression Checklist

## Task 10 — Build Show/Status Reliability Sweep

This checklist confirms that `maestro build show` and `maestro build status` are bulletproof under real-world mess conditions.

## Test Cases for `build show`

### 1. No active target set
- [ ] Rename/remove `.maestro/build/active_target.txt`
- [ ] Run `maestro build show`
- [ ] Verify: Shows "No active build target set."
- [ ] Verify: Suggests `maestro build list` and `maestro build set …`
- [ ] Verify: Exit code 1
- [ ] Verify: Clean error message, no stack trace

### 2. Active target file missing
- [ ] Set an active target that points to a non-existent target file
- [ ] Run `maestro build show`
- [ ] Verify: Shows "Build target file not found." message
- [ ] Verify: Shows guidance to use `maestro build list` and re-select
- [ ] Verify: Clean error message, no stack trace

### 3. Target JSON corrupted
- [ ] Create/modify a target file with invalid JSON
- [ ] Set this as the active target
- [ ] Run `maestro build show`
- [ ] Verify: Shows "Build target JSON is invalid." message
- [ ] Verify: Shows JSON parse error information in verbose mode
- [ ] Verify: Suggests to regenerate or restore from git
- [ ] Verify: Clean error message, no stack trace in normal mode

### 4. Requested target name/index not found
- [ ] Run `maestro build show` with an invalid target name
- [ ] Verify: Shows valid targets list
- [ ] Verify: Suggests `maestro build list`
- [ ] Verify: Exit code 1
- [ ] Verify: Clean error message, no stack trace

### 5. Normal operation (should still work)
- [ ] Run `maestro build show` with valid target
- [ ] Verify: Shows full target details
- [ ] Verify: Works with both default (active) and named targets
- [ ] Verify: Works with both target names and indices

## Test Cases for `build status`

### 1. No active target
- [ ] Rename/remove `.maestro/build/active_target.txt`
- [ ] Run `maestro build status`
- [ ] Verify: Shows guidance and exits with code 1
- [ ] Verify: Clean error message, no stack trace

### 2. No runs exist
- [ ] Ensure `.maestro/build/runs/` directory is empty
- [ ] Run `maestro build status`
- [ ] Verify: Prints "No build runs found for this repo."
- [ ] Verify: Suggests `maestro build run`
- [ ] Verify: Exit code 0 (informational)

### 3. Runs exist but last-run pointer missing
- [ ] Remove `.maestro/build/last_run.txt` but keep run directories
- [ ] Run `maestro build status`
- [ ] Verify: Prints "Last-run pointer missing; using most recent run: <run_id>"
- [ ] Verify: Uses most recent run based on timestamp ordering
- [ ] Verify: Continues with normal status display

### 4. Last run folder exists but run.json missing
- [ ] Remove `run.json` from a run directory
- [ ] Ensure this run is referenced in `last_run.txt` or is most recent
- [ ] Run `maestro build status`
- [ ] Verify: Prints "Run metadata missing: <path>"
- [ ] Verify: Still shows log files if present
- [ ] Verify: Suggests re-running
- [ ] Verify: Continues without crash

### 5. Diagnostics missing
- [ ] Remove `diagnostics.json` from a run directory
- [ ] Run `maestro build status`
- [ ] Verify: Prints "No diagnostics.json found; run may have terminated early."
- [ ] Verify: Still shows step logs paths if available
- [ ] Verify: Continues without crash

### 6. Corrupted JSON files
- [ ] Introduce invalid JSON in `run.json` or `diagnostics.json`
- [ ] Run `maestro build status`
- [ ] Verify: Handles JSON decode errors gracefully
- [ ] Verify: Shows helpful error in verbose mode
- [ ] Verify: Continue with other available data

### 7. Normal operation (should still work)
- [ ] Run `maestro build status` with valid setup
- [ ] Verify: Shows correct active target
- [ ] Verify: Shows correct last run ID and timestamp
- [ ] Verify: Shows correct result: success/failure/interrupted
- [ ] Verify: Shows correct errors/warnings count
- [ ] Verify: Shows top 3 signatures if available
- [ ] Verify: Shows file paths correctly
- [ ] Verify: Verbose mode shows additional information

## Test Cases for Last-Run Pointer Stability

### 1. Stable pointer functionality
- [ ] Run a build to create a new run
- [ ] Verify: `.maestro/build/last_run.txt` is created/updated
- [ ] Verify: Points to the correct run directory
- [ ] Verify: `build status` uses this pointer

### 2. Fallback to directory scan
- [ ] Remove `.maestro/build/last_run.txt`
- [ ] Run `maestro build status`
- [ ] Verify: Falls back to scanning run directories
- [ ] Verify: Uses most recent directory by timestamp

## Test Cases for Recovery Guidance

### 1. Appropriate next moves
- [ ] For each error condition tested above
- [ ] Verify: Always includes recovery guidance such as:
  - `maestro build list`
  - `maestro build set 1`
  - `maestro build plan`
  - `maestro build run --dry-run -v`

## Test Cases for Output Format

### 1. Consistent formatting
- [ ] Run `maestro build status` with valid data
- [ ] Verify: Output follows the expected format:
  - Active target: name/id
  - Last run: timestamp (run_id)
  - Result: success/failure/interrupted
  - Errors: N  Warnings: M
  - Top signatures (3 max)
  - File paths

### 2. Verbose vs normal mode
- [ ] Run `maestro build show/status --verbose`
- [ ] Run `maestro build show/status` (normal)
- [ ] Verify: Verbose mode shows additional paths and context
- [ ] Verify: Normal mode shows clean, compact output
- [ ] Verify: Both modes avoid stack traces in normal operation

## Additional Edge Cases

### 1. Partial/corrupted metadata
- [ ] Test with various corrupted metadata files
- [ ] Verify graceful degradation

### 2. Missing directories
- [ ] Test when build directories don't exist
- [ ] Verify proper error handling

### 3. Empty diagnostics
- [ ] Test builds with no diagnostics
- [ ] Verify correct display of "Errors: 0  Warnings: 0"