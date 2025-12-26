# cmd_plan.md - Plan Command Internal Workflow

## Synopsis
- Command: `plan`
- Aliases: `pl`
- Subcommands: add, list, remove, show, add-item, remove-item, ops, discuss, explore
- Example invocations: 
  - `maestro plan list`
  - `maestro plan add "New plan"`
  - `maestro plan show 1`

## Purpose
Manages project plans including creation, listing, modification, and discussion of plans.

## Inputs
- CLI args: Subcommands and their specific arguments (plan title, item text, etc.)
- Config inputs: Session file (required via --session)
- Required environment: Initialized repository with existing session

## State & Storage
- Reads: Session file, plan data from docs/
- Writes: Updates to plan data in docs/, session file
- Requires `--session` for most operations

## Internal Flow
1. Parse command from CLI
2. Identify command as 'plan'
3. Parse subcommand and arguments
4. Load session if required
5. Route to appropriate plan subcommand handler
6. Execute plan operation (add, list, remove, etc.)
7. Update session/plans as needed
8. Exit with appropriate code

## Decision Points
- Which subcommand was provided (add, list, remove, show, etc.)
- Whether session file exists and is valid
- Whether specified plan exists for operations like show/remove
- Whether required arguments are provided for each subcommand

## Failure Semantics
- Hard stops if session file is not provided or invalid
- Returns non-zero exit code if plan operations fail
- Shows help and exits if required arguments are missing

## Outputs
- Plan information to stdout (for list/show operations)
- Success/failure messages
- Error details if operations fail

## Tests / Fixtures
- No specific tests identified in the provided codebase
- Implementation in `maestro/commands/plan.py` and `maestro/plan_ops/commands.py`