# Ops Run Plan Format

This document specifies the YAML format for ops plans used by `maestro ops run`.

## Overview

Ops plans are deterministic, non-AI runbook-like action lists that call Maestro subcommands in sequence. They are designed for:

- Repeatable automation workflows
- Testing and verification pipelines
- Setup and teardown sequences
- Batch operations

## Format Specification

### Basic Structure

```yaml
kind: ops_run
name: <plan-name>
steps:
  - maestro: "<command>"
  - maestro: "<command>"
```

### Fields

- **kind** (required): Must be `ops_run`
- **name** (required): Human-readable plan name
- **steps** (required): List of step objects
- **allow_legacy** (optional): If true, allow legacy commands by setting `MAESTRO_ENABLE_LEGACY=1`

### Step Format

Each step is an object with a single `maestro:` key containing the command to execute.

```yaml
- maestro: "repo resolve"
```

**Important**: Only `maestro:` command steps are allowed. Arbitrary shell commands are **not supported** for security and determinism.

## Examples

### Example 1: Repository Sanity Check

```yaml
kind: ops_run
name: EX-32 pipeline sanity
steps:
  - maestro: "repo resolve"
  - maestro: "log scan --source tests/fixtures/logs/build_error.log --kind build"
  - maestro: "issues triage"
```

### Example 2: Build and Test

```yaml
kind: ops_run
name: Build and verify
steps:
  - maestro: "make"
  - maestro: "log scan --last-run --kind build"
  - maestro: "issues list --severity blocker --status open"
```

### Example 3: Workflow Validation

```yaml
kind: ops_run
name: Workflow validation suite
steps:
  - maestro: "workflow list"
  - maestro: "workflow validate hello-cli-workflow"
  - maestro: "workflow render hello-cli-workflow puml"
```

## Placeholders

Ops plans may reference outputs from previous steps with simple placeholders:

- `<LAST_SCAN_ID>` - Last log scan ID
- `<LAST_RUN_ID>` - Last ops run ID

Placeholder notes:
- `<LAST_RUN_ID>` is available immediately (current ops run ID).
- `<LAST_SCAN_ID>` is filled from `log scan` output (`Scan created: <ID>`).
- If a placeholder is used before it is available, execution fails. In dry-run mode, unresolved placeholders remain unchanged.

## Run Records

When an ops plan executes, a run record is created under:

```
docs/maestro/ops/runs/<RUN_ID>/
```

### Run Record Structure

```
docs/maestro/ops/runs/<RUN_ID>/
  meta.json          # Run metadata (plan name, timestamp, exit code)
  steps.jsonl        # Step-by-step execution log (JSONL format)
  stdout.txt         # Aggregated stdout from all steps
  stderr.txt         # Aggregated stderr from all steps
  summary.json       # Final summary with statistics
```

### Run ID Format

Run IDs are deterministic and based on:
```
<timestamp>_<kind>_<hash>
```

Example: `20250130_120530_ops_run_a3f2`

### meta.json

```json
{
  "run_id": "20250130_120530_ops_run_a3f2",
  "plan_name": "EX-32 pipeline sanity",
  "plan_path": "/path/to/plan.yaml",
  "started_at": "2025-01-30T12:05:30.123456",
  "completed_at": "2025-01-30T12:05:45.789012",
  "dry_run": false,
  "exit_code": 0
}
```

### steps.jsonl

Each line is a JSON object representing one step execution:

```json
{"step_index": 0, "command": "repo resolve", "started_at": "2025-01-30T12:05:30.500", "exit_code": 0, "duration_ms": 1234}
{"step_index": 1, "command": "log scan --source tests/fixtures/logs/build_error.log --kind build", "started_at": "2025-01-30T12:05:31.800", "exit_code": 0, "duration_ms": 567}
```

### summary.json

```json
{
  "total_steps": 3,
  "successful_steps": 3,
  "failed_steps": 0,
  "total_duration_ms": 15456,
  "exit_code": 0
}
```

## Execution Modes

### Normal Mode

```bash
maestro ops run plan.yaml
```

Executes all steps and creates full run record.

### Dry-Run Mode

```bash
maestro ops run plan.yaml --dry-run
```

- Shows what would be executed without running
- Creates run record with `dry_run: true`
- Steps are logged but not executed

### Continue-on-Error Mode

```bash
maestro ops run plan.yaml --continue-on-error
```

- Continues executing remaining steps even if one fails
- Final exit code is non-zero if any step failed

## Exit Codes

- **0**: All steps completed successfully
- **1**: One or more steps failed (in continue-on-error mode)
- **2**: Execution stopped due to step failure (default mode)
- **3**: Internal error (plan parsing, invalid YAML, etc.)

## Security and Constraints

1. **No arbitrary shell**: Only `maestro:` commands allowed
2. **Subprocess isolation**: Each command runs in a controlled subprocess
3. **No network by default**: Commands should not require network access
4. **No auto-commit**: Git operations must be explicit
5. **Respects MAESTRO_DOCS_ROOT**: For testing in isolated environments
6. **Legacy commands disabled**: `MAESTRO_ENABLE_LEGACY=0` unless `allow_legacy: true`

## Index

All ops runs are tracked in:

```
docs/maestro/ops/index.json
```

Format:
```json
{
  "runs": [
    {
      "run_id": "20250130_120530_ops_run_a3f2",
      "plan_name": "EX-32 pipeline sanity",
      "started_at": "2025-01-30T12:05:30.123456",
      "exit_code": 0
    }
  ]
}
```

## See Also

- `docs/workflows/v3/cli/SIGNATURES.md` - Ops command signatures
- `docs/workflows/v3/cli/TREE.md` - CLI command tree
- `docs/workflows/v3/runbooks/examples/proposed/EX-36_ops_doctor_plus_run_thin_slice.sh` - Example usage
