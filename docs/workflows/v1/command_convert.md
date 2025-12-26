# Command: Convert

The `convert` command provides a comprehensive pipeline for converting code between different languages, frameworks, or platforms. It operates on a two-repo model where conversion planning occurs in the source repository but execution happens in a target repository.

## Subcommands

### `maestro convert new [pipeline_name]`
Creates a new conversion pipeline with the specified name.

**Implementation:**
- Function: `handle_convert_new()` in `maestro/commands/convert.py`
- Creates pipeline metadata in `.maestro/convert/`
- Uses `create_new_pipeline()` from `maestro.convert.convert_orchestrator`

### `maestro convert plan <pipeline_id>`
Generates a conversion plan based on source and target inventories, potentially involving AI-assisted planning.

**Implementation:**
- Function: `handle_convert_plan()` in `maestro/commands/convert.py`
- Uses `plan_conversion()` from `maestro.convert.planner`
- Generates plan JSON with tasks organized in phases (scaffold, file, sweep)
- Validates plan against schema and business rules

### `maestro convert run <pipeline_id>`
Executes the conversion pipeline tasks.

**Implementation:**
- Function: `handle_convert_run()` in `maestro/commands/convert.py`
- Uses `run_conversion_pipeline()` from `maestro.convert.execution_engine`
- Executes tasks in order: scaffold → file → sweep
- Includes semantic integrity checks
- Supports arbitration mode with multiple AI engines

### `maestro convert status <pipeline_id>`
Shows the status of a conversion pipeline.

**Implementation:**
- Function: `handle_convert_status()` in `maestro/commands/convert.py`
- Uses `get_pipeline_status()` from `maestro.ui_facade.convert`
- Displays pipeline status and stage information

### `maestro convert show <pipeline_id>`
Shows detailed information about a conversion pipeline.

**Implementation:**
- Function: `handle_convert_show()` in `maestro/commands/convert.py`
- Uses `get_pipeline_status()` from `maestro.ui_facade.convert`
- Displays detailed stage information and artifacts

### `maestro convert reset <pipeline_id>`
Resets the state of a conversion pipeline.

**Implementation:**
- Function: `handle_convert_reset()` in `maestro/commands/convert.py`
- Uses `reset_pipeline()` from `maestro.convert.convert_orchestrator`

### `maestro convert batch [subcommand]`
Handles batch operations for multiple pipelines.

**Subcommands:**
- `run` - Run batch conversion
- `status` - Get batch status
- `show` - Show batch details
- `report` - Generate batch report

## Pipeline Storage

Conversion pipelines are stored in the `.maestro/convert/` directory:

- **Plan location:** `.maestro/convert/plan/plan.json`
- **Inventories:** `.maestro/convert/inventory/`
- **Snapshots:** `.maestro/convert/snapshots/`
- **Inputs:** `.maestro/convert/inputs/`
- **Outputs:** `.maestro/convert/outputs/`
- **Diffs:** `.maestro/convert/diffs/`
- **Checkpoints:** `.maestro/convert/checkpoints/`
- **Arbitration:** `.maestro/convert/arbitration/`
- **Semantics:** `.maestro/convert/semantics/`
- **Memory:** `.maestro/convert/memory/`

## Cross-Repo Operations

The convert functionality supports cross-repository operations where:
1. Source repository provides the code to be converted
2. Target repository receives the converted code
3. Conversion planning occurs in the source repo
4. Conversion execution occurs in the target repo

## Safety Boundaries

The system implements several safety mechanisms:

- **Path validation:** Prevents directory traversal attacks
- **Write policies:** Controls how files are written to target (overwrite, merge, skip_if_exists, fail_if_exists)
- **Hash tracking:** Tracks file changes to detect unintended modifications
- **Semantic checks:** Validates that conversions preserve intended functionality
- **Inventory validation:** Ensures all source files are accounted for

## Failure Semantics

- **Hard stops:** Invalid plan JSON, missing AST, target repo creation failure
- **Task-level failures:** Individual tasks can fail without stopping the entire pipeline
- **Semantic violations:** Can block pipeline if equivalence is too low
- **Drift detection:** Can create checkpoints that require approval before continuing

## Session/Transcript Logging

Conversion operations create detailed logs in:
- `.maestro/convert/inputs/` - Prompts sent to AI engines
- `.maestro/convert/outputs/` - Raw outputs from AI engines
- `.maestro/convert/summaries/` - Structured task summaries
- `.maestro/convert/memory/` - Decision logs and glossary entries