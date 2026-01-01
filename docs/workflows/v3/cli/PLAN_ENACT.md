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
```

## How It Works

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
- [maestro track list](./SIGNATURES.md#track-list) - View materialized tracks
