# maestro plan enact

Materialize a WorkGraph plan into Track/Phase/Task files.

## Usage

```bash
maestro plan enact <WORKGRAPH_ID> [OPTIONS]
```

## Arguments

- `<WORKGRAPH_ID>` - WorkGraph ID to materialize (e.g., `wg-20260101-a3f5b8c2`)

## Options

- `--json` - Output summary as JSON to stdout
- `--out DIR` - Output directory for files (default: `docs/maestro`)
- `--dry-run` - Preview what would be created/updated without writing files
- `--name "Track Title"` - Override track name (default: uses WorkGraph track name)
- `-v, --verbose` - Show detailed output
- `--top N` - Materialize only top N tasks (by profile score) + their dependencies
- `--profile investor|purpose|default` - Scoring profile for --top selection (default: default)

## Examples

```bash
# Basic materialization
maestro plan enact wg-20260101-a3f5b8c2

# Dry run (preview only)
maestro plan enact wg-20260101-a3f5b8c2 --dry-run

# Override track name
maestro plan enact wg-20260101-a3f5b8c2 --name "My Custom Track"

# Custom output directory
maestro plan enact wg-20260101-a3f5b8c2 --out custom/path

# JSON output for scripting
maestro plan enact wg-20260101-a3f5b8c2 --json

# Portfolio enact (top-N with dependency closure)
maestro plan enact wg-20260101-a3f5b8c2 --top 5 --profile investor

# Top 3 purpose-aligned tasks + dependencies
maestro plan enact wg-20260101-a3f5b8c2 --top 3 --profile purpose
```

## Portfolio Enact (--top Mode)

When `--top N` is specified, enact materializes only the top-N highest-scoring tasks **plus their transitive dependencies**, creating a focused portfolio of work.

### How It Works

1. **Scores all tasks** using the specified profile (investor/purpose/default)
2. **Selects top N** by score (ties broken by task_id ASC for determinism)
3. **Computes dependency closure** - finds all tasks that the top-N depend on
4. **Topologically sorts** dependencies (dependencies first, then top tasks)
5. **Materializes selected tasks** with score annotations in task descriptions

### Example Output

```
Top tasks selected (investor profile): TASK-003, TASK-001, TASK-007
Dependencies added: TASK-002, TASK-005
Materialized total: 5 tasks
```

### Determinism Guarantees

- Same WorkGraph + same profile + same N = same selection
- Tied scores resolved by task_id (alphabetical)
- Topological sort is stable (task_id ASC)
- Dependency cycles trigger stable fallback with warning

### Task Metadata

Selected tasks include extra metadata in their descriptions:
- **Score**: Task's priority score (e.g., `+8.0`)
- **Rationale**: Scoring breakdown (impact, effort, risk, purpose)
- **Safe to Execute**: Safety flag (✓ Safe or ⚠ Unsafe)

## How It Works (Full Enact)

1. **Reads WorkGraph** from `docs/maestro/plans/workgraphs/{id}.json`
2. **Converts structure**:
   - WorkGraph.track → Track JSON
   - WorkGraph.phases → Phase JSON
   - WorkGraph.phases[].tasks → Task JSON
3. **Materializes** to `docs/maestro/{tracks,phases,tasks}/`
4. **Updates index** at `docs/maestro/index.json`

## Idempotency

Running `maestro plan enact` twice with the same WorkGraph ID is safe:
- Existing items are updated, not duplicated
- New items are created
- Stable filenames based on IDs

## File Structure

```
docs/maestro/
├── index.json
├── tracks/
│   └── TRK-001.json
├── phases/
│   └── PH-001.json
└── tasks/
    └── TASK-001.json
```

## See Also

- [maestro plan decompose](./PLAN_DECOMPOSE.md) - Create WorkGraphs
- [maestro plan score](./PLAN_SCORE.md) - Score and rank WorkGraph tasks
- [maestro plan recommend](./PLAN_SCORE.md) - Get top recommendations
- [maestro track list](./SIGNATURES.md#track-list) - View materialized tracks
