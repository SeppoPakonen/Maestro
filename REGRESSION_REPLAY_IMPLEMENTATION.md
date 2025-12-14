# Maestro Regression Replay System - Implementation Summary

## Overview
This implementation adds comprehensive regression replay functionality to Maestro to address the requirement: "the same conversion run produces different results next week". The system includes run manifests, replay capabilities, drift detection, and convergence enforcement.

## Features Implemented

### 1. Run Manifest System
- **Location**: `.maestro/convert/runs/<run_id>/`
- **Files generated for each run**:
  - `manifest.json` - Contains run metadata (ID, timestamps, source/target paths, revisions, flags, etc.)
  - `plan.json` - Copy of the plan at run start
  - `decisions.json` - Active decisions snapshot
  - `conventions.json` - Conventions snapshot
  - `glossary.json` - Glossary snapshot
  - `open_issues.json` - Open issues snapshot
  - `environment.json` - Environment information (OS, Python, Maestro, engine versions)
  - `artifacts_index.json` - Index of generated artifacts

### 2. Environment Capture
- Captures OS information, Python version, Maestro version, and engine CLI versions
- Handles missing GitPython gracefully (shows "unknown" for revisions)

### 3. Replay Command
- **Command**: `maestro convert replay <run_id> <source> <target>`
- **Modes**:
  - `--dry` (default): Dry run without applying changes
  - `--apply`: Apply changes to target
  - `--limit N`: Limit number of tasks to execute
  - `--only task:<id>` / `--only phase:<name>`: Run only specific task or phase
  - `--use-recorded-engines` (default): Use engines from original run
  - `--allow-engine-change`: Allow using different engines
  - `--max-replay-rounds K` (default 2): Maximum rounds for convergence
  - `--fail-on-any-drift`: Fail if any drift detected

### 4. Drift Detection
- **Structural Drift**: File content hash changes, file count changes, diff metrics
- **Decision Drift**: Decision fingerprint differences
- **Semantic Drift**: Semantic summary changes and reappearing issues
- **Output**: Both JSON (`drift_report.json`) and human-readable Markdown (`drift_report.md`) reports

### 5. Convergence Policy
- **Default policy**: Allow up to 2 replay rounds with decreasing changes
- **Convergence analysis**: Detects if changes are decreasing (trending toward convergence)
- **Non-convergence detection**: Identifies oscillating or diverging changes
- **Enforcement**: Configurable strictness with `--fail-on-any-drift` flag

### 6. Golden Baseline Support
- **Command**: `maestro convert replay baseline <run_id> [baseline_id]`
- **Storage**: `.maestro/convert/baselines/<baseline_id>.json`
- **Content**: Target file hashes, semantic summary, plan revision, decision fingerprint

### 7. CLI Commands for Run Management
- **List runs**: `maestro convert runs list` - Shows last 10 runs with status
- **Show run**: `maestro convert runs show <run_id>` - Detailed run information
- **Diff runs**: `maestro convert runs diff <run_id> --against <other_run_or_baseline>` - Compare runs/baselines

### 8. Integration
- Seamlessly integrated into existing Maestro CLI structure
- Uses subprocess calls to the underlying convert orchestrator
- All conversion runs automatically generate run manifests

## Technical Implementation

### Key Components
- `regression_replay.py`: Core implementation including all functionality
- Integration with `convert_orchestrator.py` for command handling 
- Integration with `maestro/main.py` for CLI commands

### Data Structures
- `RunManifest`: Contains all run metadata
- `EnvironmentInfo`: Captured environment details
- `DriftReport`: Comprehensive drift analysis results

### Error Handling
- Graceful handling of missing GitPython dependency
- Proper fallback mechanisms for missing data
- Clear error messages for invalid inputs

## Testing
- Comprehensive test suite in `test_regression_replay.py`
- Tests cover all major functionality: manifests, drift detection, convergence, CLI commands
- All tests pass successfully

## Usage Examples

```bash
# Run a conversion (automatic manifest generation)
maestro convert run --source /path/to/source --target /path/to/target

# List all runs
maestro convert runs list

# Show details of a specific run
maestro convert runs show <run_id>

# Compare two runs
maestro convert runs diff <run1> --against <run2>

# Replay a run in dry mode
maestro convert replay <run_id> /path/to/source /path/to/target --dry

# Create a golden baseline
maestro convert replay baseline <run_id> <baseline_name>

# Apply a replay with convergence enforcement
maestro convert replay <run_id> /path/to/source /path/to/target --apply --max-replay-rounds 3 --fail-on-any-drift
```

## Compliance with Requirements
✅ Every conversion run generates a full manifest + snapshots
✅ Replay can run in dry mode and detect drift  
✅ Drift reports include structural + semantic changes
✅ Convergence is enforced with configurable strictness
✅ Runs can be listed and inspected via CLI
✅ Tests cover drift and convergence behavior
✅ GitPython is optional (graceful degradation)
✅ Supports golden baseline functionality