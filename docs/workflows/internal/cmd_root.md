# cmd_root.md - Root Command Internal Workflow

## Synopsis
- Command: `root`
- No aliases
- Subcommands: set, get, refine, discuss, show
- Example invocations:
  - `maestro root get`
  - `maestro root set "New root task"`
  - `maestro root discuss`

## Purpose
Manages the root task which represents the primary objective or goal of the project.

## Inputs
- CLI args: Subcommands and their specific arguments (task text, etc.)
- Config inputs: Session file (required via --session), root task configuration
- Required environment: Initialized repository with existing session

## State & Storage
- Reads: Session file, root task data from docs/
- Writes: Updates to root task data in docs/, session file
- Requires `--session` for operations

## Internal Flow
1. Parse command from CLI
2. Identify command as 'root'
3. Parse subcommand and arguments
4. Load session if required
5. Route to appropriate root subcommand handler
6. Execute root task operation (set, get, refine, etc.)
7. Update session/root task as needed
8. Exit with appropriate code

## Decision Points
- Which root subcommand was provided (set, get, refine, discuss, show)
- Whether session file exists and is valid
- Whether root task exists and is accessible

## Failure Semantics
- Hard stops if session file is not provided or invalid
- Returns non-zero exit code if root task operations fail
- Shows help and exits if required arguments are missing

## Outputs
- Root task information to stdout (for get/show operations)
- Success/failure messages
- Error details if operations fail

## Tests / Fixtures
- No specific tests identified in the provided codebase
- Implementation in `maestro/modules/cli_parser.py` (core subparsers)