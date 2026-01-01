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
- `-v, --verbose`: Show prompt hash, engine, and validation summary
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