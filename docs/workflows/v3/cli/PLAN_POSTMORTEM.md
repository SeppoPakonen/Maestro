# maestro plan postmortem

Analyze run failures and turn them into capital (log scan → issues → fix WorkGraph).

## Purpose

When `maestro plan sprint --execute` runs tasks and some fail (exit != 0 or timeout), the **postmortem** command provides automatic failure analysis:

1. **Collect failure artifacts** (stdout/stderr from failed tasks)
2. **Run deterministic log scan** to extract error patterns
3. **Ingest findings to issues** system (with automatic deduplication)
4. **Create fix WorkGraph** with `--domain issues`
5. **Print "next best command"** for immediate action

**Failure becomes capital.**

## Usage

```bash
maestro plan postmortem <RUN_ID> [OPTIONS]
```

## Arguments

- `<RUN_ID>` - Run ID to analyze (e.g., `run-20260102-1234abcd`)

## Options

- `--execute` - Actually write to log scan + issues (default: preview only)
- `--scan-kind run|build` - Log scan kind (default: `run`)
- `--issues` - Ingest findings to issues system (requires --execute)
- `--decompose` - Create WorkGraph for fixes (domain=issues, requires --execute)
- `-v, --verbose` - Show detailed output
- `-vv, --very-verbose` - Show very detailed output (AI prompts, full artifacts)
- `--json` - Output summary as JSON to stdout

## Default Behavior

**Postmortem is safe by default**:

- **Preview mode** (no --execute): Shows what would be done
- **Execute mode** (with --execute): Actually runs log scan, issues add, decompose

## How It Works

### Step 1: Load Run Artifacts

Postmortem searches for the run ID in `docs/maestro/plans/workgraphs/*/runs/<RUN_ID>/` and loads failure artifacts:

- `tasks/<TASK_ID>/raw_stdout.txt`
- `tasks/<TASK_ID>/raw_stderr.txt`
- `tasks/<TASK_ID>/meta.json` (exit_code, duration_ms, cmd, cwd, timestamp)

### Step 2: Concatenate Failure Logs

Combines all failure artifacts into a single log for analysis:

```
=== TASK: TASK-001 ===
Command: python test.py
Exit code: 1
Duration: 1500ms

--- stderr ---
Error: Something went wrong
Traceback:
  File test.py, line 42
    SyntaxError

--- stdout ---
Running tests...
```

### Step 3: Run Log Scan (Optional)

If `--issues` or `--decompose` is specified:

```bash
maestro log scan --source <concatenated_failures> --kind run
```

Deterministic scan extracts:
- Error patterns
- Stack traces
- File references

### Step 4: Ingest to Issues (Optional)

If `--issues` is specified:

```bash
maestro issues add --from-log <SCAN_ID>
```

Automatic deduplication prevents duplicate issues.

### Step 5: Create Fix WorkGraph (Optional)

If `--decompose` is specified:

```bash
maestro plan decompose --domain issues "Fix blockers from run <RUN_ID>" -e
```

Creates a new WorkGraph with tasks to fix identified issues.

## Examples

### Preview Mode (Default)

```bash
maestro plan postmortem run-20260102-1234abcd
```

Shows:
- List of failed tasks
- What would be scanned
- What issues would be created
- What WorkGraph would be generated

### Execute with Issues

```bash
maestro plan postmortem run-20260102-1234abcd --execute --issues
```

Runs:
1. Log scan of failure artifacts
2. Issues ingestion from scan results

### Execute with Issues + Decompose (Full Pipeline)

```bash
maestro plan postmortem run-20260102-1234abcd --execute --issues --decompose
```

Runs:
1. Log scan
2. Issues ingestion
3. WorkGraph creation for fixes

Outputs:
- New WorkGraph ID
- Next command: `maestro plan sprint <WORKGRAPH_ID> --top 5 --profile investor --execute`

### Very Verbose Mode

```bash
maestro plan postmortem run-20260102-1234abcd --execute --issues --decompose -vv
```

Shows:
- Full failure artifacts (stdout/stderr)
- AI prompts and responses (if decompose uses AI)
- Detailed progress for each step

### JSON Output

```bash
maestro plan postmortem run-20260102-1234abcd --execute --issues --json
```

Outputs machine-readable JSON summary:

```json
{
  "run_id": "run-20260102-1234abcd",
  "workgraph_id": "wg-test-001",
  "artifacts": 3,
  "scan_id": "scan-run-20260102",
  "issue_ids": ["ISS-001", "ISS-002", "ISS-003"],
  "workgraph_id_fixes": "wg-fixes-run-2026"
}
```

## Integration with Sprint

When `maestro plan sprint --execute` detects failures, it prints:

```
MAESTRO_SPRINT_POSTMORTEM_RUN_ID=run-20260102-1234abcd

Failures detected! Run postmortem to analyze:
  maestro plan postmortem run-20260102-1234abcd --execute --issues --decompose
```

Ops runners can capture the `MAESTRO_SPRINT_POSTMORTEM_RUN_ID` marker for automation.

## Machine-Readable Markers

Postmortem outputs single-line markers for ops parsing:

- **`MAESTRO_POSTMORTEM_RUN_ID=<run-id>`** - Run ID analyzed
- **`MAESTRO_POSTMORTEM_ARTIFACTS=<count>`** - Number of failure artifacts
- **`MAESTRO_POSTMORTEM_SCAN_ID=<scan-id>`** - Log scan ID (if ran)
- **`MAESTRO_POSTMORTEM_ISSUES=<issue-ids>`** - Issue IDs created (comma-separated)
- **`MAESTRO_POSTMORTEM_WORKGRAPH=<workgraph-id>`** - Fix WorkGraph ID (if created)

## Artifact Budgets

To prevent unbounded storage:

- **Max 200KB per stream** (stdout/stderr truncated if larger, with TRUNCATED marker)
- **Max 20 artifacts per run** (only first 20 failures saved)

Truncation is noted in `meta.json`:

```json
{
  "task_id": "TASK-001",
  "exit_code": 1,
  "stdout_truncated": true,
  "stderr_truncated": false,
  "stdout_bytes": 204800,
  "stderr_bytes": 1024
}
```

## Safety Features

1. **Preview default**: `--execute` must be explicit
2. **Bounded output**: No unbounded printing or storage
3. **Idempotent**: Re-running postmortem is safe (issues dedupe)
4. **No auto-execution**: Postmortem never auto-runs (only suggests)

## See Also

- [maestro plan sprint](./PLAN_SPRINT.md) - Portfolio sprint button
- [maestro plan decompose](./PLAN_DECOMPOSE.md) - Create WorkGraphs
- [maestro issues](./SIGNATURES.md#issues) - Issue management
- [maestro log scan](./SIGNATURES.md#log-scan) - Log scanning
