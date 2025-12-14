# Build Target Lifecycle Smoke Test Checklist

This checklist verifies that the Maestro build target lifecycle is working properly. Use this to validate all functionality after implementing changes.

## Prerequisites
- [ ] Maestro is installed and accessible via `maestro` command
- [ ] Repository has a `.maestro/` directory
- [ ] At least one session exists and is set as active

## Test Cases

### 1. Build Target Creation (`build new`)
- [ ] Execute: `maestro build new test-target`
- [ ] Verify: Target is created successfully with minimal valid schema
- [ ] Verify: Target file is created in `.maestro/build/targets/<target_id>.json`
- [ ] Verify: Target ID and name are displayed
- [ ] Verify: Target has minimal pipeline with at least a `build` step
- [ ] Verify: Target is set as active by default
- [ ] Verify: Index file (`.maestro/build/index.json`) is updated

### 2. Build Target Listing (`build list`)
- [ ] Execute: `maestro build list` (or `maestro b ls`)
- [ ] Verify: All build targets are listed with index numbers
- [ ] Verify: Target names are displayed
- [ ] Verify: Target IDs are displayed (shortened)
- [ ] Verify: Active target is marked with `[*]`
- [ ] Verify: Last modified time is shown
- [ ] Verify: Verbose mode shows additional path information

### 3. Build Target Activation (`build set`)
- [ ] Execute: `maestro build set test-target` (or `maestro b se test-target`)
- [ ] Verify: Target is set as active successfully
- [ ] Execute: `maestro build set 1` (using index number)
- [ ] Verify: Target can be selected by index
- [ ] Verify: Error message appears for invalid target name/index

### 4. Active Build Target Query (`build get`)
- [ ] Execute: `maestro build get` (or `maestro b g`)
- [ ] Verify: Active target name and ID are printed in one-liner format: `name (id)`
- [ ] Execute: `maestro build get -v`
- [ ] Verify: Verbose output shows detailed information
- [ ] Execute with no active target: Should show guidance message

### 5. Build Target Details (`build show`)
- [ ] Execute: `maestro build show` (no arguments - should default to active)
- [ ] Verify: Shows active target details
- [ ] Execute: `maestro build show test-target` (or `maestro b sh test-target`)
- [ ] Verify: Shows specified target details
- [ ] Verify: Shows name, ID, created time
- [ ] Verify: Shows pipeline steps with numbering
- [ ] Verify: Shows environment variables (if any)
- [ ] Verify: Shows patterns (if any)
- [ ] Verify: Shows "why/description" (if present)

### 6. Build Plan Default Behavior (`build plan`)
- [ ] Execute: `maestro build plan` (no target name provided)
- [ ] Verify: Uses active build target by default
- [ ] Execute: `maestro build plan` when no active target exists
- [ ] Verify: Prompts: "No active build target. Create one now? [Y/n]"
- [ ] Verify: Creates new target if user responds affirmatively

### 7. Build Run Uses Active Target (`build run`)
- [ ] Execute: `maestro build run` (no target name provided)
- [ ] Verify: Uses active build target
- [ ] Execute: `maestro build run` when no active target exists
- [ ] Verify: Shows error message about missing active target
- [ ] Verify: Runs pipeline from active target

### 8. Build Status Uses Active Target (`build status`)
- [ ] Execute: `maestro build status` (or `maestro b stat`)
- [ ] Verify: Shows status for active build target
- [ ] Verify: Prints active target name
- [ ] Verify: Prints last run result summary
- [ ] Execute when no active target exists
- [ ] Verify: Shows error message about missing active target

### 9. Alias Parity
- [ ] Verify: `maestro b n` works the same as `maestro build new`
- [ ] Verify: `maestro b ls` works the same as `maestro build list`
- [ ] Verify: `maestro b se` works the same as `maestro build set`
- [ ] Verify: `maestro b g` works the same as `maestro build get`
- [ ] Verify: `maestro b sh` works the same as `maestro build show`
- [ ] Verify: `maestro b p` works the same as `maestro build plan`
- [ ] Verify: `maestro b ru` works the same as `maestro build run`
- [ ] Verify: `maestro b stat` works the same as `maestro build status`

### 10. Help Consistency
- [ ] Execute: `maestro build h` or `maestro build help`
- [ ] Verify: Shows help for build commands
- [ ] Execute: `maestro build new h` or `maestro build new --help`
- [ ] Verify: Shows help for build new command
- [ ] Execute: `maestro b n h` (alias version)
- [ ] Verify: Shows same help as full command

### 11. Repository Root Discovery
- [ ] Execute any build command from a subdirectory of the repo
- [ ] Verify: Correctly finds `.maestro/` directory in parent
- [ ] Execute with `--verbose` flag
- [ ] Verify: Shows "Detected repository root" message
- [ ] Verify: Shows paths used during operation

### 12. Error Handling
- [ ] Execute `build set` with non-existent target name
- [ ] Verify: Clear error message, no stack trace
- [ ] Execute `build show` with non-existent target name
- [ ] Verify: Clear error message, no stack trace
- [ ] Break the index.json file manually
- [ ] Verify: Graceful recovery by rebuilding index from target files

## Success Criteria
- [ ] All basic lifecycle commands work: new, list, set, get, show
- [ ] Commands default to active target where appropriate
- [ ] Aliases behave identically to long forms
- [ ] Verbose mode shows repo root and path information
- [ ] No stack traces in normal operation
- [ ] Actionable error messages when inputs are invalid
- [ ] Index file is properly maintained

## Notes
If any test fails, please check:
- That `.maestro/` directory exists at repo root
- That a session is properly set as active
- That target files in `.maestro/build/targets/` are valid JSON
- That `.maestro/build/index.json` is properly formatted