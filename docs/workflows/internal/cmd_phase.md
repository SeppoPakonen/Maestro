# cmd_phase.md - Phase Command Internal Workflow

## Synopsis
- Command: `phase`
- Aliases: `ph`, `p`
- Subcommands: list, add, remove, show (assumed based on pattern)
- Example invocations:
  - `maestro phase list`
  - `maestro phase add "New phase"`
  - `maestro phase show 1`

## Purpose
Manages project phases which are organizational units within tracks that group related tasks.

## Inputs
- CLI args: Subcommands and their specific arguments (phase title, etc.)
- Config inputs: Session file (required via --session)
- Required environment: Initialized repository with existing session

## State & Storage
- Reads: Session file, phase data from docs/
- Writes: Updates to phase data in docs/, session file
- Requires `--session` for operations

## Internal Flow
1. Parse command from CLI
2. Identify command as 'phase'
3. Parse subcommand and arguments
4. Load session if required
5. Route to appropriate phase subcommand handler
6. Execute phase operation (add, list, remove, etc.)
7. Update session/phases as needed
8. Exit with appropriate code

## Decision Points
- Which subcommand was provided (add, list, remove, show, etc.)
- Whether session file exists and is valid
- Whether specified phase exists for operations like show/remove
- Whether required arguments are provided for each subcommand

## Failure Semantics
- Hard stops if session file is not provided or invalid
- Returns non-zero exit code if phase operations fail
- Shows help and exits if required arguments are missing

## Outputs
- Phase information to stdout (for list/show operations)
- Success/failure messages
- Error details if operations fail

## Tests / Fixtures
- No specific tests identified in the provided codebase
- Implementation in `maestro/commands/phase.py`