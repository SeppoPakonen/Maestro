# RUNBOOK RESOLVE: Freeform → JSON Runbook

## Overview

The `maestro runbook resolve` command transforms freeform natural language text into structured runbook JSON. This command serves as the primary "operational asset" creation tool, allowing teams to quickly convert requirements, tasks, or documentation into actionable runbooks.

## Purpose

- **Bootstrap**: Convert natural language requirements into structured runbooks
- **Iteration**: Create concrete artifacts teams can refine over time
- **Local State**: Store runbooks in repo-local storage (`docs/maestro/runbooks/`)
- **Deterministic**: Stable IDs and update semantics for consistent management

## Command Syntax

```bash
# Basic usage with freeform text
maestro runbook resolve "Create a runbook for building and scanning logs in BatchScriptShell"

# With verbose output showing prompt details
maestro runbook resolve -v "Build and test the application"

# Reading from stdin (useful for piping large inputs)
cat docs/commands/batch_script_help.md | maestro runbook resolve -e -v "Derive a runbook from these command docs"
```

## Flags

- `-e, --eval`: Read freeform input from stdin instead of positional argument
- `-v, --verbose`: Show prompt hash, engine, evidence summary, validation summary
- `-vv, --very-verbose`: Also print resolved AI prompt and pretty engine output (implies -v)
- `--help`: Show help text with examples

## Resolve vs Discuss

- **`resolve`**: Creates new runbooks from scratch using freeform text
  - Input: Natural language description
  - Output: New structured runbook JSON
  - Purpose: Bootstrap operational assets
- **`discuss`**: Refines existing runbooks through AI interaction
  - Input: Existing runbook + conversation
  - Output: Modified runbook
  - Purpose: Iterate and improve existing assets

## Repo Evidence Included

The resolve command includes contextual information from the repository:

- **CLI Surface**: Available commands and options (if `docs/maestro/cli_surface.json` exists)
- **Repo Model**: Package/assembly counts (if `docs/maestro/repo_model.json` exists)
- **Git Context**: Branch, uncommitted changes (if in a git repo)

## WorkGraph Fallback (Automatic Robustness)

When a runbook generation attempt produces invalid JSON or fails validation, `maestro runbook resolve` automatically falls back to creating a **WorkGraph** instead:

### Behavior

1. **Primary Attempt**: Generate structured runbook JSON using AI
2. **Validation**: Check for required fields (`title`, `steps`, etc.)
3. **On Failure**: Fall back to WorkGraph generation with structured Track/Phase/Task decomposition
4. **Guidance**: Provide `maestro plan enact` command to materialize the WorkGraph

### Why This Matters

- **Real Repositories**: Complex projects may require multi-phase work that doesn't fit simple runbook structure
- **Graceful Degradation**: Users always get actionable output (either runbook or work graph)
- **No Silent Failures**: Clear messaging explains when fallback occurs and what to do next

### Example Fallback Output

```bash
$ maestro runbook resolve -v "Add comprehensive test coverage and CI pipeline"

Runbook validation failed. Falling back to WorkGraph generation...
Validation errors: ['Missing required field: steps']
Collected 15 evidence items for WorkGraph

Runbook too big/ambiguous → created WorkGraph instead
WorkGraph ID: wg-20260101-a3f5b8c2
Domain: runbook
Phases: 3
Tasks: 12

Next step: Run the following command to materialize the plan:
  maestro plan enact wg-20260101-a3f5b8c2
```

### When Fallback Triggers

- Runbook has no `title` field
- Runbook has no `steps` or `steps` is empty
- Runbook validation fails for other schema reasons

See also: [maestro plan enact](./PLAN_ENACT.md) for WorkGraph materialization.

## JSON Schema Stability

Runbooks follow a strict schema with these required fields:

- `id`: Deterministic ID (format: `rb-{slug}-{hash}`)
- `title`: Human-readable title
- `goal`: Description of the runbook's purpose
- `steps`: Array of action objects, each with:
  - `cmd`: Command to execute
  - `expect`: Expected outcome
  - `notes`: Optional additional information

## Storage Contract

- **Location**: `docs/maestro/runbooks/`
- **Index**: `docs/maestro/runbooks/index.json` (stable list)
- **Files**: `docs/maestro/runbooks/items/{RUNBOOK_ID}.json` (canonical JSON)
- **ID Strategy**: `rb-{slug(title)}-{sha256(normalized_title)[:8]}`
- **Update Semantics**: Same title → same ID → update in place

## Examples

### Basic Resolve
```bash
maestro runbook resolve "Build the application and run tests"
```

### From Stdin with Verbose Output
```bash
cat requirements.txt | maestro runbook resolve -e -v "Create build runbook from requirements"
```

### Very Verbose Output (Debug AI Interaction)
```bash
maestro runbook resolve -vv "Create a runbook for building the application"
# This will show:
# - The full AI prompt sent to the engine
# - The raw AI response in a readable format
# - All regular verbose information (prompt hash, engine, etc.)
```

### Check Results
```bash
# List created runbooks
maestro runbook list

# Show specific runbook
maestro runbook show <RUNBOOK_ID>

# Show raw JSON
maestro runbook show <RUNBOOK_ID> --json
```

## Error Handling

- **Validation Failures**: Loud errors with specific field requirements
- **No Write on Failure**: Invalid runbooks are not saved
- **Stdin TTY Error**: Clear error when using `-e` without piped input
- **Missing Text**: Clear error when no text provided without `-e`

## Integration Points

- Works with existing `MAESTRO_DOCS_ROOT` environment variable
- Compatible with archive/restore lifecycle
- Follows canonical CLI patterns (list/show/add/edit/remove)
- Integrates with workflow creation (`maestro workflow create --from-runbook`)