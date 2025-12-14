# Maestro Chaos Rehearsal - Intentional Broken-Code Scenarios

This directory contains tests that intentionally introduce broken code and configurations to verify that Maestro's build + fix machinery works correctly.

## Overview

The chaos rehearsal includes 4 main scenarios:

### Scenario A - Trivial Compile Error (Guaranteed Fixable)
- Introduces a simple compile failure (missing semicolon, undefined variable)
- Runs Maestro build and fix
- Verifies the error is fixed and patch is kept

### Scenario B - Path/CWD Misconfiguration
- Creates build target with problematic relative paths
- Runs build from subdirectory to trigger path issues
- Verifies Maestro diagnoses path/CWD problems clearly

### Scenario C - "Library Trap" Error (Rulebook Trigger + Escalation)
- Introduces U++/template style errors
- Uses rulebook to trigger matching
- Tests escalation from Qwen to Claude if issues persist

### Scenario D - Multi-Error Situation
- Seeds multiple independent compile errors
- Verifies targeted signature fixing doesn't mask other errors
- Ensures one fix doesn't break others

## How to Run

### Basic Usage
```bash
cd /path/to/maestro/repo
python .maestro/tests/run_scenarios.py
```

### With Options
```bash
# Continue running even if some scenarios fail
python .maestro/tests/run_scenarios.py --keep-going

# List scenarios without running them
python .maestro/tests/run_scenarios.py --list
```

## Output Artifacts

Each scenario creates various artifacts:

- **Diagnostics JSON files**: Before/after fix diagnostics
- **Build run logs**: Detailed build output
- **Fix run data**: Iteration records, patch files
- **Improvement report**: `improvements_YYYYMMDD_HHMMSS.md` with UX suggestions

## Improvement Suggestions

During execution, the harness captures improvement suggestions whenever:
- Output is confusing
- Status lacks information
- Help text is incomplete
- Commands feel silent
- File paths are unclear

These are saved to `.maestro/reports/` with severity levels (minor/major/critical).

## Requirements

- Git repository (required for Maestro's checkpoint/revert functionality)
- C++ compiler (g++) for test builds
- Maestro properly installed and configured