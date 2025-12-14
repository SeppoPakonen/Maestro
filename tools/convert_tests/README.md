# Maestro Convert Test Harness

This directory contains a standardized test harness for Maestro's convert functionality using a dual-repository setup.

## Overview

The harness enables testing of Maestro's convert capabilities with:

- A **source repository** (read-only fixture)
- A **target repository** (write-only output)
- Deterministic artifacts and "golden" reports
- Safe interruption/resume functionality
- Zero accidental writes to source repository
- Clear success/failure definitions per scenario

## Directory Structure

```
convert_tests/
  scenarios/
    <scenario_name>/
      source_repo/        # repo A (fixture)
      target_repo/        # repo B (created/initialized by harness)
      expected/           # golden expected summaries (optional)
      notes.md            # scenario-specific intent + success criteria
  runs/
    <scenario_name>/<timestamp>/
      artifacts/          # copy of .maestro/convert artifacts
      reports/            # report.md + machine JSON summaries
      logs/               # command logs
      diff/               # git diff snapshots (target repo only)
```

## Usage

### List All Scenarios

```bash
tools/convert_tests/run_scenario.py --list
```

### Run a Specific Scenario

```bash
tools/convert_tests/run_scenario.py --scenario minimal_dual_repo --force-clean --verbose
```

### Run with Forced Interruption

```bash
tools/convert_tests/run_scenario.py --scenario minimal_dual_repo --force-clean --interrupt-after 2 --verbose
```

## Command Line Options

- `--scenario <name>`: Name of scenario to run
- `--list`: List all available scenarios
- `--keep-target`: Don't delete target repo between runs
- `--force-clean`: Wipe target repo and rerun
- `--verbose`: Show verbose output
- `--no-ai`: Dry mode; runs inventory + validates wiring
- `--interrupt-after <seconds>`: Send SIGINT after N seconds
- `--update-golden`: Update golden files instead of checking them

## Scenario Creation

To create a new scenario, create a directory under `scenarios/` with:

1. `source_repo/` - The input repository to convert from
2. `target_repo/` - Will be created/initialized by harness (optional)
3. `expected/` - Golden files for validation (optional)
4. `notes.md` - Documentation about the scenario's intent and success criteria

## Features

- **Write Protection**: Verifies no changes are made to the source repository
- **Artifact Capture**: Copies all Maestro convert artifacts to the run directory
- **Diff Recording**: Captures git status, diff, and log from the target repository
- **Summary Generation**: Creates detailed JSON summary of the run
- **Golden Matching**: Validates output against expected results
- **Interrupt/Resume**: Tests Maestro's ability to handle interruptions gracefully