# Build Run Path Resolution & Diagnostics Regression Checklist

This checklist ensures the reliability of `maestro build run` and its diagnostics pipeline across different working directories, scripts, and environments.

## Test Cases

### 1. Run from repo root
- [ ] Navigate to repository root (where `.maestro/` directory exists)
- [ ] Execute: `maestro b ru`
- [ ] Verify: Build runs successfully and completes as expected
- [ ] Verify: Repo root is correctly detected and shown in verbose mode
- [ ] Verify: Commands execute in correct working directory

### 2. Run from a deep subdirectory
- [ ] Navigate to a subdirectory: `cd src/foo/bar` (or similar nested path in your project)
- [ ] Execute: `maestro b ru`
- [ ] Verify: Build runs successfully and completes as expected
- [ ] Verify: Repo root is correctly detected regardless of current directory
- [ ] Verify: Commands execute in correct working directory (repo root)

### 3. Dry-run execution
- [ ] Execute: `maestro b ru --dry-run -v`
- [ ] Verify: No actual commands are executed
- [ ] Verify: All pipeline steps are printed with their resolved commands
- [ ] Verify: Working directory (CWD) is clearly shown for each step
- [ ] Verify: Environment variables (if any) are shown

### 4. Test "file exists but not found" scenarios
- [ ] Modify a build target to reference a non-existent script: `"cmd": ["bash", "nonexistent_script.sh"]`
- [ ] Execute: `maestro b ru`
- [ ] Verify: Error message includes resolved CWD
- [ ] Verify: Error message includes hint to check `build show`, `--dry-run`, or repo root
- [ ] Verify: Raw traceback is not shown in normal mode

### 5. Verify logging and artifacts
- [ ] Execute: `maestro b ru` (after a successful build target has been set)
- [ ] Navigate to: `.maestro/build/runs/`
- [ ] Verify: A new timestamp-based run directory was created (e.g., `run_1234567890`)
- [ ] Verify: `run.json` file exists in the run directory with complete metadata
- [ ] Verify: `diagnostics.json` file exists with extracted diagnostic information
- [ ] Verify: `step_*.stdout.txt` and `step_*.stderr.txt` files exist for each step
- [ ] Check content of log files to ensure they contain expected output

### 6. Test build status command
- [ ] Execute: `maestro b stat`
- [ ] Verify: Active target is shown
- [ ] Verify: Last run timestamp is shown
- [ ] Verify: Last run result (success/failure) is shown
- [ ] Verify: Error count and warning count are shown
- [ ] Verify: Top signatures with counts are shown
- [ ] Verify: Paths to run.json, diagnostics.json, and log directory are clearly shown

### 7. Path resolution with relative paths
- [ ] Create a build target that uses relative paths in commands
- [ ] Execute: `maestro b ru` from various subdirectories
- [ ] Verify: Relative paths resolve correctly relative to repo root
- [ ] Verify: Commands execute successfully regardless of current working directory

### 8. Verbose mode information
- [ ] Execute: `maestro b ru -v`
- [ ] Verify: Repo root path is printed early in the output
- [ ] Execute: `maestro b stat -v`
- [ ] Verify: Detailed information about target file and repo root is shown

---

## Expected Outcomes

After applying the fixes in Task 9:
- `build run` works identically from any working directory
- `--dry-run` prints exactly what would be executed
- "file exists but not found" class bugs are eliminated or clearly diagnosed
- Logs and run metadata are always persisted
- Diagnostics extraction produces stable signatures suitable for fix verification
- `build status` provides actionable "where are we" visibility