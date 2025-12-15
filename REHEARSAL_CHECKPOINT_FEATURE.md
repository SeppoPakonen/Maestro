# Maestro - Human Checkpoints & Rehearsal Mode Documentation

## Overview

The Human Checkpoints & Semantic Rehearsal Mode feature introduces two key capabilities to Maestro:

1. **Checkpoints** - Explicit pause points that require human approval during conversion execution
2. **Rehearsal Mode** - Full conversion simulation with no writes to target directory for safe preview

These features enable a "trust, but verify" approach to AI-driven conversions, allowing humans to review and approve significant changes before they're actually applied.

## Features

### 1. Checkpoint System

#### Plan-Level Checkpoints
Checkpoints can be defined explicitly in conversion plans:

```json
{
  "checkpoints": [
    {
      "checkpoint_id": "CP-02",
      "after_tasks": ["f_012", "f_013"],
      "label": "Core data structures converted",
      "requires": ["semantic_ok", "build_pass"],
      "auto_continue": false,
      "status": "pending"
    }
  ]
}
```

#### Automatic Checkpoints in Rehearsal Mode
When generating plans with `--rehearse`, Maestro automatically inserts checkpoints:

- After scaffold tasks
- After every 5 file conversion tasks (configurable)
- After final sweep tasks

#### Checkpoint Statuses
- `pending` - Waiting for human approval
- `approved` - Approved by human
- `rejected` - Rejected by human, stops execution
- `completed` - Completed or overridden
- `skipped` - Skipped based on conditions

### 2. Rehearsal Mode

Rehearsal mode runs the complete conversion pipeline with all normal logic (planning, arbitration, semantic checks, summaries, drift detection) but with zero writes to the target directory.

**Key Rules:**
- No writes to target directory
- All normal logic still runs (planning, arbitration, semantic checks, etc.)
- File outputs stored only as rehearsal artifacts
- All diff previews generated
- Complete simulation of the conversion process

### 3. Promotion Command

The `promote` command allows reusing rehearsal results for real execution:

```bash
maestro convert promote <rehearsal_run_id> <source_path> <target_path>
```

This reuses:
- Plan and task decisions
- Arbitration winners
- Semantic acceptances
- Conversion memory state

## Commands

### Plan Command
```bash
# Generate plan with rehearsal checkpoints
maestro convert plan <source> <target> --rehearse
```

### Run Command
```bash
# Execute in rehearsal mode (no writes to target)
maestro convert run <source> <target> --rehearse

# Execute normal conversion
maestro convert run <source> <target>
```

### Rehearsal Promotion
```bash
# Promote rehearsal results to real execution
maestro convert promote <rehearsal_run_id> <source> <target>
```

### Checkpoint Management
```bash
# Approve a checkpoint to continue execution
maestro convert checkpoint approve CP-001 --note "Looks good, continuing"

# Reject a checkpoint and stop execution
maestro convert checkpoint reject CP-001 --note "Issues found, stopping"

# Override a checkpoint and continue with risk acceptance
maestro convert checkpoint override CP-001 --note "Accepting risk for now"

# List all checkpoints in current plan
maestro convert checkpoint list

# Show details of a specific checkpoint
maestro convert checkpoint show CP-001
```

## Checkpoint Requirements

Checkpoints can specify requirements that must be met before continuing:

- `semantic_ok` - All semantic checks must pass
- `build_pass` - Build command must succeed

## Artifacts

### Rehearsal Artifacts
Stored under `.maestro/convert/rehearsal/<run_id>/`

- Plan with decisions and results
- Conversion memory state
- Task outputs in rehearsal target directory

### Checkpoint Artifacts
Stored under `.maestro/convert/checkpoints/<checkpoint_id>/`

- `summary.json` - Detailed checkpoint summary with:
  - Tasks completed since last checkpoint
  - Semantic summary deltas
  - Open issues added
  - Top risks
  - Timestamp information

## Integration with Existing Features

### With Arbitration
- Arbitration logic still runs in rehearsal mode
- Results are preserved for promotion

### With Semantic Integrity
- All semantic checks still run in rehearsal
- Results are preserved and can be accepted/rejected
- Rehearsal mode allows semantic review before real changes

### With Conversion Memory
- All decisions and conventions still apply in rehearsal
- Memory state is preserved for promotion

## Workflows

### Rehearsal Workflow
1. Generate plan with rehearsal checkpoints: `maestro convert plan source target --rehearse`
2. Run rehearsal: `maestro convert run source target --rehearse`
3. Review artifacts and checkpoints as needed
4. Promote when satisfied: `maestro convert promote <run_id> source target`

### Checkpoint Workflow
1. Execution pauses at checkpoints requiring approval
2. Run `maestro convert checkpoint list` to see status
3. Run `maestro convert checkpoint show <id>` for details
4. Approve/reject/override as needed
5. Execution continues after approval

## Benefits

- **Safety**: Zero-risk preview of AI conversion
- **Transparency**: Clear visibility into what AI will do
- **Control**: Human approval at meaningful milestones
- **Efficiency**: Cache expensive AI operations for later promotion
- **Confidence**: Gradual verification builds trust in the system