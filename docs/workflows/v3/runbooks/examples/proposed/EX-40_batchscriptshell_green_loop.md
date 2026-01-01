# EX-40: BatchScriptShell Green Loop

**Category**: Real-World Integration
**Domain**: Build → Issues → WorkGraph → Execution
**Introduced**: P2 Sprint 4.13
**Status**: Proposed

## Goal

Demonstrate the complete "green loop" workflow on a real repository (BatchScriptShell):

```
build/test → log scan → issues ingest → plan decompose (domain=issues) → plan enact → plan run
```

This runbook shows how to take a repository from broken build to automatically-generated fix plan.

## Prerequisites

1. **BatchScriptShell repository** cloned at `~/Dev/BatchScriptShell`
   - Git repo: https://github.com/username/BatchScriptShell
   - Has Makefile for building
   - May have build errors or warnings

2. **Maestro installed** with ops run support (P2 Sprint 4.12+)

3. **Python environment** with all Maestro dependencies

## Workflow Overview

### Phase 1: Build and Capture

Build the repository and capture output for analysis:

```bash
cd ~/Dev/BatchScriptShell
maestro make clean
maestro make 2>&1 | tee build.log
```

### Phase 2: Scan Build Output

Scan the build log for errors and warnings:

```bash
maestro log scan --source build.log --kind build
# Outputs: Scan created: scan-20260101-abc123
```

### Phase 3: Ingest Issues

Convert log scan findings into trackable issues:

```bash
maestro issues add --from-log scan-20260101-abc123
maestro issues list --status open
```

### Phase 4: Generate WorkGraph from Issues

Use AI to decompose the issues into a structured work plan:

```bash
maestro plan decompose --domain issues "Bring BatchScriptShell to green build" -e
# Outputs: WorkGraph created: wg-20260101-def456
```

### Phase 5: Materialize WorkGraph

Convert the WorkGraph into Track/Phase/Task structure:

```bash
maestro plan enact wg-20260101-def456
# Creates: Track, Phases, Tasks in docs/maestro/
```

### Phase 6: Execute Plan (Dry-Run)

Preview what the plan would do without actually executing:

```bash
maestro plan run wg-20260101-def456 --dry-run -v --max-steps 5
```

### Phase 7: Execute Plan (Actual)

**WARNING**: Only run this if tasks are marked `safe_to_execute: true`

```bash
maestro plan run wg-20260101-def456 --execute -v --max-steps 5
```

## Automated Version (Ops Plan)

The entire workflow can be run automatically using an ops plan:

```bash
cd ~/Dev/BatchScriptShell

# Dry-run mode (safe by default)
maestro ops run tests/fixtures/ops_plans/plan_batchscriptshell_build.yaml

# With write operations enabled
maestro ops run tests/fixtures/ops_plans/plan_batchscriptshell_build.yaml --execute

# With continue-on-error
maestro ops run tests/fixtures/ops_plans/plan_batchscriptshell_build.yaml --execute --continue-on-error
```

## Ops Plan Structure

The ops plan (`plan_batchscriptshell_build.yaml`) chains these steps:

```yaml
kind: ops_run
name: BatchScriptShell green loop
steps:
  # 1. Discover repo
  - kind: maestro
    args: ["repo", "resolve"]
    timeout_s: 120
    allow_write: false

  # 2. Clean and build
  - kind: maestro
    args: ["make", "clean"]
    timeout_s: 60
    allow_write: true

  - kind: maestro
    args: ["make"]
    timeout_s: 300
    allow_write: true

  # 3. Scan build output
  - kind: maestro
    args: ["log", "scan", "--last-run", "--kind", "build"]
    timeout_s: 60
    allow_write: false

  # 4. Ingest issues
  - kind: maestro
    args: ["issues", "add", "--from-log", "<LAST_SCAN_ID>"]
    timeout_s: 60
    allow_write: true

  # 5. Triage issues
  - kind: maestro
    args: ["issues", "triage", "--auto"]
    timeout_s: 60
    allow_write: true

  # 6. Generate WorkGraph
  - kind: maestro
    args: ["plan", "decompose", "--domain", "issues", "Bring BatchScriptShell to green build", "-e"]
    timeout_s: 180
    allow_write: true

  # 7. Materialize to Track/Phase/Task
  - kind: maestro
    args: ["plan", "enact", "<LAST_WORKGRAPH_ID>"]
    timeout_s: 120
    allow_write: true

  # 8. Execute (dry-run by default)
  - kind: maestro
    args: ["plan", "run", "<LAST_WORKGRAPH_ID>", "--dry-run", "-v", "--max-steps", "5"]
    timeout_s: 300
    allow_write: false
```

## Safety Features

### 1. Safe-by-Default Execution

- **Default**: All write steps are skipped unless `--execute` flag is passed
- **Write steps**: `make clean`, `make`, `issues add`, `plan decompose`, `plan enact`
- **Read steps**: `repo resolve`, `log scan`, `plan run --dry-run`

### 2. Task-Level Safety

WorkGraph tasks must be explicitly marked `safe_to_execute: true` to run in execute mode:

```json
{
  "id": "TASK-001",
  "title": "Fix compilation error in main.c",
  "safe_to_execute": true,
  "definition_of_done": [
    {
      "kind": "command",
      "cmd": "gcc -c main.c",
      "expect": "exit 0"
    }
  ]
}
```

Tasks not marked safe will be logged as `SKIPPED_UNSAFE` during execution.

### 3. Isolated Testing

Use `MAESTRO_DOCS_ROOT` for isolated testing:

```bash
export MAESTRO_DOCS_ROOT=/tmp/maestro-test
maestro ops run plan.yaml --dry-run
# All artifacts go to /tmp/maestro-test/docs/maestro/
```

## Artifacts Created

After running the full loop, you'll have:

```
docs/maestro/
├── ops/runs/<RUN_ID>/
│   ├── meta.json         # Run metadata
│   ├── steps.jsonl       # Step-by-step log
│   ├── summary.json      # Run summary
│   ├── stdout.txt        # Aggregated stdout
│   └── stderr.txt        # Aggregated stderr
├── log_scans/<SCAN_ID>/
│   ├── meta.json         # Scan metadata
│   └── findings.jsonl    # Error/warning findings
├── issues/
│   ├── index.json        # Issue index
│   └── <ISSUE_ID>.json   # Individual issues
├── plans/workgraphs/
│   └── <WG_ID>.json      # WorkGraph plan
├── tracks/
│   └── <TRACK_ID>.json   # Track (from enact)
├── phases/
│   └── <PHASE_ID>.json   # Phases (from enact)
└── tasks/
    └── <TASK_ID>.json    # Tasks (from enact)
```

## Metadata Linkage

The ops run record links all artifacts via metadata:

```json
{
  "run_id": "ops_run_20260101_120000_abc123",
  "plan_name": "BatchScriptShell green loop",
  "exit_code": 0,
  "metadata": {
    "last_scan_id": "scan-20260101-abc123",
    "last_workgraph_id": "wg-20260101-def456",
    "last_workgraph_run_id": "wr-20260101-120500-ghi789"
  }
}
```

This enables traceability from build → issues → plan → execution.

## Troubleshooting

### Issue: "WorkGraph not found"

```bash
# List available workgraphs
ls docs/maestro/plans/workgraphs/

# Use the full ID from the list
maestro plan enact wg-20260101-abc123
```

### Issue: "Tasks are skipped as SKIPPED_UNSAFE"

This is expected if tasks don't have `safe_to_execute: true`. To enable execution:

1. Review the generated WorkGraph
2. Manually edit the WorkGraph JSON to add `"safe_to_execute": true` to trusted tasks
3. Re-run with `--execute` flag

### Issue: "Build fails during ops run"

Use `--continue-on-error` to complete remaining steps:

```bash
maestro ops run plan.yaml --execute --continue-on-error
```

The run record will show which step failed.

## Variations

### 1. Incremental Loop (Resume from Existing Issues)

Skip build and scan if you already have issues:

```yaml
steps:
  # Start from existing issues
  - kind: maestro
    args: ["issues", "list", "--status", "open"]
    allow_write: false

  - kind: maestro
    args: ["plan", "decompose", "--domain", "issues", "Fix open issues", "-e"]
    allow_write: true
  # ... rest of workflow
```

### 2. Manual Build + Automated Analysis

Run build manually, then use ops plan for analysis only:

```bash
# Manual build
cd ~/Dev/BatchScriptShell
make clean && make 2>&1 | tee build.log

# Automated analysis
maestro ops run plan_analyze_only.yaml --execute
```

### 3. Target Specific Issues

Use `--only` flag to execute only specific tasks:

```bash
maestro plan run wg-20260101-abc123 --execute --only TASK-001,TASK-002
```

## See Also

- [OPS_RUN_FORMAT.md](../../cli/OPS_RUN_FORMAT.md) - Ops plan YAML specification
- [PLAN_ENACT.md](../../cli/PLAN_ENACT.md) - WorkGraph materialization
- [EX-32](./EX-32_ops_doctor_plus_run_thin_slice.sh) - Ops run basics
- [EX-36](./EX-36_ops_doctor_plus_run_thin_slice.sh) - Ops doctor + run integration

## Implementation Notes

- **Introduced**: P2 Sprint 4.13
- **Dependencies**: ops run (4.12), plan enact (4.10), domain=issues evidence (4.12)
- **Test Coverage**: `tests/test_ops_run_maestro_steps.py`, smoke test in `tools/smoke/batchscriptshell_green_loop.sh`
- **Repo Hygiene**: No hardcoded paths in Maestro code; all repo-specific paths in ops plans
