# cmd_ops.md - Ops Command Internal Workflow

## Synopsis
- Command: `ops`
- No aliases
- Subcommands: validate, preview, apply
- Example invocations:
  - `maestro ops validate operations.json`
  - `maestro ops preview operations.json`
  - `maestro ops apply operations.json`

## Purpose
Provides project operations automation to validate, preview, and apply JSON-based project operations.

## Inputs
- CLI args: Subcommands and their specific arguments (JSON file path, etc.)
- Config inputs: Session file (required via --session), operations JSON file
- Required environment: Initialized repository with existing session

## State & Storage
- Reads: Operations JSON file, session file, project state
- Writes: Updates to project files (for apply operation), operation logs
- Requires `--session` for operations

## Internal Flow
1. Parse command from CLI
2. Identify command as 'ops'
3. Parse subcommand and arguments (JSON file path)
4. Load session if required
5. Route to appropriate ops subcommand handler
6. Execute ops operation (validate, preview, apply)
7. Update project state as needed (for apply operation)
8. Exit with appropriate code

## Decision Points
- Which ops subcommand was provided (validate, preview, apply)
- Whether session file exists and is valid
- Whether operations JSON file exists and is valid
- Whether operations are safe to apply (for apply operation)

## Failure Semantics
- Hard stops if session file is not provided or invalid
- Hard stops if operations JSON file is invalid
- Returns non-zero exit code if ops operations fail
- Shows help and exits if required arguments are missing

## Outputs
- Validation results to stdout (for validate operation)
- Preview of changes to stdout (for preview operation)
- Success/failure messages
- Error details if operations fail

## Tests / Fixtures
- No specific tests identified in the provided codebase
- Implementation in `maestro/modules/cli_parser.py` (core subparsers) and `maestro/project_ops/commands.py`