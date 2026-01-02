# maestro plan sprint

Orchestrate the complete portfolio workflow: recommend → enact → run loop.

## Purpose

After generating a WorkGraph with `maestro plan decompose`, you have a "big backlog soup" with no clear prioritization. The `maestro plan sprint` command solves this by automating the entire workflow:

1. **Recommend**: Score and select top N tasks (with dependency closure)
2. **Enact**: Materialize selected tasks to Track/Phase/Task files
3. **Run**: Execute tasks (default: dry-run preview)

This is the **"portfolio sprint button"** - select 5, do 5, measure impact.

## Usage

```bash
maestro plan sprint <WORKGRAPH_ID> --top N [OPTIONS]
```

## Arguments

- `<WORKGRAPH_ID>` - WorkGraph ID to run sprint on (e.g., `wg-20260101-a3f5b8c2`)

## Options

- `--top N` - Number of top tasks to select **(required)**
- `--profile investor|purpose|default` - Scoring profile (default: `default`)
- `--execute` - Actually execute commands (default: dry-run preview only)
- `--dry-run` - Preview only, do not execute commands (default: `true`)
- `--only-top` - Run only top tasks, not dependencies (default: `true`)
- `--skip TASK_ID,...` - Skip specified tasks (comma-separated)
- `--out DIR` - Output directory for Track/Phase/Task files (default: `docs/maestro`)
- `-v, --verbose` - Show detailed output
- `-vv, --very-verbose` - Show bounded ranked list with scores and per-task reasoning
- `--json` - Output summary as JSON to stdout

## Default Behavior

**Sprint is safe by default**:

- **Enact always writes** (materializes to Track/Phase/Task files)
- **Run is dry-run by default** (preview only, unless `--execute`)
- **--execute only runs safe tasks** (`safe_to_execute=true`)
- **--only-top is true** (run only top tasks, not dependencies)

## Examples

### Investor Loop (Top 5 High-ROI Tasks)

```bash
# Dry-run preview (safe default)
maestro plan sprint wg-20260101-a3f5b8c2 --top 5 --profile investor

# Actually execute
maestro plan sprint wg-20260101-a3f5b8c2 --top 5 --profile investor --execute
```

### Purpose Loop (Top 3 Purpose-Aligned Tasks)

```bash
# Purpose-driven sprint
maestro plan sprint wg-20260101-a3f5b8c2 --top 3 --profile purpose --execute
```

### Run All Selected Tasks (Top + Dependencies)

By default, `--only-top=true` means only top tasks run (dependencies are enacted but not run).

To run **all selected tasks** (top + dependencies):

```bash
maestro plan sprint wg-20260101-a3f5b8c2 --top 5 --profile investor --execute --only-top=false
```

### Skip Specific Tasks

```bash
maestro plan sprint wg-20260101-a3f5b8c2 --top 5 --profile investor --skip TASK-003,TASK-007
```

### Verbose Modes

```bash
# -v: Show detailed progress
maestro plan sprint wg-20260101-a3f5b8c2 --top 5 --profile investor -v

# -vv: Show top 10 ranked tasks with scores
maestro plan sprint wg-20260101-a3f5b8c2 --top 5 --profile investor -vv
```

## How It Works

### Step 1: Select Top N + Dependency Closure

1. Scores all tasks using the specified profile (`investor`, `purpose`, or `default`)
2. Selects top N tasks by score (ties broken by `task_id` ASC)
3. Computes transitive dependency closure (all tasks that top-N depend on)
4. Topologically sorts dependencies (dependencies first, then top tasks)

### Step 2: Enact Selected Tasks

Materializes selected tasks (top + dependencies) to Track/Phase/Task files:

- Creates or updates Track JSON
- Creates or updates Phase JSON
- Creates or updates Task JSON (with score annotations and `safe_to_execute` flags)
- **Idempotent**: Running twice updates existing items (no duplicates)

### Step 3: Run Selected Tasks

Executes tasks using the deterministic WorkGraph runner:

- **Default: dry-run** (preview only)
- **With --execute**: runs commands (only `safe_to_execute=true` tasks)
- **With --only-top (default)**: runs only top tasks (not dependencies)
- **With --skip**: excludes specified task IDs

### Step 4: Print Summary

Outputs both human-readable and machine-readable summaries:

- **Machine-readable markers** (for ops parsing):
  - `MAESTRO_SPRINT_TOP_IDS=TASK-003,TASK-001,TASK-007`
  - `MAESTRO_SPRINT_ENACTED=12`
  - `MAESTRO_SPRINT_RUN_ID=run-20260102-1234abcd`
- **Human-readable summary**:
  - Top tasks selected
  - Dependencies added
  - Tasks materialized
  - Run results (completed/failed/skipped)
  - Next steps

## Output Format

### Human-Readable Mode (default)

```
Selecting top 5 tasks with dependencies...

Top tasks selected (investor profile): TASK-003, TASK-001, TASK-007, TASK-012, TASK-005
Dependencies added: 4

Enacting 9 tasks...

Running only top 5 tasks (dependencies enacted but not run)...

SPRINT SUMMARY
MAESTRO_SPRINT_TOP_IDS=TASK-003,TASK-001,TASK-007,TASK-012,TASK-005
MAESTRO_SPRINT_ENACTED=9
MAESTRO_SPRINT_RUN_ID=run-20260102-1234abcd

Top tasks selected (investor profile): TASK-003, TASK-001, TASK-007, TASK-012, TASK-005
Dependencies added: 4
Materialized total: 9 tasks to TRK-001
Run ID: run-20260102-1234abcd
Tasks completed: 5
Tasks failed: 0
Tasks skipped: 0
Mode: DRY RUN (no commands executed)

NEXT STEPS
To execute: maestro plan sprint wg-20260101-a3f5b8c2 --top 5 --profile investor --execute
Run record: docs/maestro/plans/workgraphs/wg-20260101-a3f5b8c2/runs/run-20260102-1234abcd/
```

### JSON Mode (--json)

```json
{
  "workgraph_id": "wg-20260101-a3f5b8c2",
  "profile": "investor",
  "top_n": 5,
  "selection": {
    "top_task_ids": ["TASK-003", "TASK-001", "TASK-007", "TASK-012", "TASK-005"],
    "closure_task_ids": ["TASK-002", "TASK-004", "TASK-009", "TASK-011"],
    "total_selected": 9
  },
  "enact": {
    "track_id": "TRK-001",
    "tasks_created": 9,
    "tasks_updated": 0
  },
  "run": {
    "run_id": "run-20260102-1234abcd",
    "tasks_completed": 5,
    "tasks_failed": 0,
    "tasks_skipped": 0,
    "dry_run": true
  }
}
```

## Determinism Guarantees

Sprint is **fully deterministic**:

- Same WorkGraph + same profile + same N = **same selection**
- Tied scores resolved by `task_id` ASC (alphabetical)
- Topological sort is stable (`task_id` ASC tiebreaker)
- Dependency cycles trigger stable fallback with warning
- No AI required (uses existing deterministic scoring)

## Machine-Readable Markers

Sprint outputs single-line markers for ops parsing:

- **`MAESTRO_SPRINT_TOP_IDS=<comma-separated>`** - Selected top task IDs
- **`MAESTRO_SPRINT_ENACTED=<count>`** - Total tasks materialized
- **`MAESTRO_SPRINT_RUN_ID=<run-id>`** - Run record ID

These markers can be captured by ops runners for workflow automation.

## Bounded Output

- Top task IDs: shows first 5, then `"... and N more"`
- Very verbose (-vv): shows top 10 ranked tasks with scores
- Selection summary: max 10 IDs per list (top tasks, dependencies)

## Safety Features

1. **Dry-run default**: `--execute` must be explicit
2. **Safe-only execution**: only runs `safe_to_execute=true` tasks
3. **Idempotent enact**: no duplicates on re-run
4. **Bounded output**: no spam on large graphs
5. **Deterministic**: same input → same output (no randomness)

## Integration with Ops Plans

Sprint can be called from ops YAML structured steps:

```yaml
steps:
  - kind: maestro
    args:
      - plan
      - sprint
      - <WORKGRAPH_ID>
      - --top
      - "5"
      - --profile
      - investor
      - --execute
```

Ops runners can capture the `MAESTRO_SPRINT_*` markers for metadata tracking.

## See Also

- [maestro plan decompose](./PLAN_DECOMPOSE.md) - Create WorkGraphs
- [maestro plan score](./PLAN_SCORE.md) - Score and rank tasks
- [maestro plan recommend](./PLAN_SCORE.md) - Get top recommendations
- [maestro plan enact](./PLAN_ENACT.md) - Materialize WorkGraphs
- [maestro plan run](./SIGNATURES.md#plan-run) - Execute WorkGraphs
