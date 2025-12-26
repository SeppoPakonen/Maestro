# cmd_issues.md - Issues Command Internal Workflow

## Synopsis
- Command: `issues`
- No aliases
- Subcommands: list, add, remove, show, resolve (assumed based on command name)
- Example invocations:
  - `maestro issues list`
  - `maestro issues add "New issue"`

## Purpose
Provides issue tracking commands to manage project issues and bugs.

## Inputs
- CLI args: Subcommands and their specific arguments
- Config inputs: Session file (required via --session), issue tracking configuration
- Required environment: Initialized repository with existing session

## State & Storage
- Reads: Issue data from docs/, session file
- Writes: Updates to issue data in docs/, session file
- Requires `--session` for operations

## Internal Flow
1. Parse command from CLI
2. Identify command as 'issues'
3. Parse subcommand and arguments
4. Load session if required
5. Route to appropriate issues subcommand handler
6. Execute issue operation (add, list, resolve, etc.)
7. Update session/issues as needed
8. Exit with appropriate code

## Decision Points
- Which subcommand was provided (list, add, remove, show, resolve, etc.)
- Whether session file exists and is valid
- Whether issue data exists and is accessible
- Whether required arguments are provided for each subcommand

## Failure Semantics
- Hard stops if session file is not provided or invalid
- Returns non-zero exit code if issue operations fail
- Shows help and exits if required arguments are missing

## Outputs
- Issue information to stdout (for list/show operations)
- Success/failure messages
- Error details if operations fail

## Tests / Fixtures
- No specific tests identified in the provided codebase
- Implementation in `maestro/commands/issues.py`