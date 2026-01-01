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

Ops plans support two step formats:

#### Old Format (Backward Compatible)

Simple string command format:

```yaml
- maestro: "repo resolve"
```

#### New Structured Format (Recommended)

Explicit format with timeout and metadata support:

```yaml
- kind: maestro
  args: ["repo", "resolve", "-v"]
  timeout_s: 120
  cwd: "."
  allow_write: false
```

**Fields**:
- `kind` (required): Must be `maestro`
- `args` (required): List of command arguments (e.g., `["repo", "resolve", "-v"]`)
- `timeout_s` (optional): Timeout in seconds (default: 300)
- `cwd` (optional): Working directory for command execution
- `allow_write` (optional): If true, this step writes data and requires `--execute` flag (default: false)

**Important**: Only `maestro` commands are allowed. Arbitrary shell commands are **not supported** for security and determinism.

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

### Example 4: Issues to WorkGraph Loop (Structured Format)

```yaml
kind: ops_run
name: Real-world loop - issues to workgraph execution
steps:
  # Repo discovery
  - kind: maestro
    args: ["repo", "resolve", "lite"]
    timeout_s: 120
    allow_write: false

  # Log scan from last run
  - kind: maestro
    args: ["log", "scan", "--last-run", "--kind", "build"]
    timeout_s: 60
    allow_write: false

  # Ingest issues from log scan
  - kind: maestro
    args: ["issues", "add", "--from-log", "<LAST_SCAN_ID>"]
    timeout_s: 60
    allow_write: true

  # Generate WorkGraph from issues
  - kind: maestro
    args: ["plan", "decompose", "--domain", "issues", "Bring repo to green build", "-e"]
    timeout_s: 180
    allow_write: true

  # Materialize WorkGraph
  - kind: maestro
    args: ["plan", "enact", "<LAST_WORKGRAPH_ID>"]
    timeout_s: 120
    allow_write: true

  # Execute WorkGraph (dry-run)
  - kind: maestro
    args: ["plan", "run", "<LAST_WORKGRAPH_ID>", "--dry-run", "-v", "--max-steps", "5"]
    timeout_s: 300
    allow_write: false
```

## Placeholders

Ops plans may reference outputs from previous steps with simple placeholders:

- `<LAST_RUN_ID>` - Current ops run ID (available immediately)
- `<LAST_SCAN_ID>` - Last log scan ID (from `log scan` output)
- `<LAST_WORKGRAPH_ID>` - Last WorkGraph ID (from `plan decompose` or `runbook resolve` output)
- `<LAST_WORKGRAPH_RUN_ID>` - Last WorkGraph run ID (from `plan run` output)

Placeholder notes:
- `<LAST_RUN_ID>` is available immediately (current ops run ID).
- `<LAST_SCAN_ID>` is filled from `log scan` output (`Scan created: <ID>`).
- `<LAST_WORKGRAPH_ID>` is filled from `plan decompose` or `runbook resolve` output (`WorkGraph ID: <ID>` or `WorkGraph materialized: <ID>`).
- `<LAST_WORKGRAPH_RUN_ID>` is filled from `plan run` output (`Run completed: <ID>`).
- If a placeholder is used before it is available, execution fails. In dry-run mode, unresolved placeholders remain unchanged.

### Metadata Linkage

Step outputs are automatically parsed for IDs and stored in run record metadata:
- `scan_id` - Extracted from log scan commands
- `workgraph_id` - Extracted from plan decompose/runbook resolve commands
- `workgraph_run_id` - Extracted from plan run commands

Metadata is stored in:
1. Individual step results (`steps.jsonl`)
2. Run-level metadata (`meta.json`) with keys like `last_scan_id`, `last_workgraph_id`, etc.

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

**Important**: Write steps (steps with `allow_write: true`) are skipped in normal mode unless `--execute` flag is passed.

### Dry-Run Mode

```bash
maestro ops run plan.yaml --dry-run
```

- Shows what would be executed without running
- Creates run record with `dry_run: true`
- Steps are logged but not executed

### Execute Mode (Allow Writes)

```bash
maestro ops run plan.yaml --execute
```

- Allows write steps to execute (steps with `allow_write: true`)
- Default posture: safe, read-only operations only
- Use `--execute` to enable steps that modify state (e.g., `issues add`, `plan enact`)

**Write Steps**:
- `issues add --from-log` - Ingests issues from log scans
- `issues triage` - Updates issue metadata
- `plan decompose` - Generates WorkGraphs (writes to `docs/maestro/plans/workgraphs/`)
- `plan enact` - Materializes WorkGraphs to Track/Phase/Task JSON files

**Read-Only Steps** (always execute):
- `repo resolve` - Discovers repository structure
- `log scan` - Scans logs for errors
- `plan run --dry-run` - Previews WorkGraph execution without running commands

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
