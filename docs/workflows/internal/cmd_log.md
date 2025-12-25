# cmd_log.md - Log Command Internal Workflow

## Synopsis
- Command: `log`
- Aliases: `lg`
- Subcommands: list, list-work, list-plan
- Example invocations:
  - `maestro log list`
  - `maestro log list-work`
  - `maestro log list-plan`

## Purpose
Manages log information for tracking activities, work sessions, and plan execution.

## Inputs
- CLI args: Subcommands and their specific arguments
- Config inputs: Session file (required via --session), log configuration
- Required environment: Initialized repository with existing session

## State & Storage
- Reads: Log files, session file, work logs, plan logs
- Writes: No direct writes (read-only operations)
- Requires `--session` for operations

## Internal Flow
1. Parse command from CLI
2. Identify command as 'log'
3. Parse subcommand and arguments
4. Load session if required
5. Route to appropriate log subcommand handler
6. Execute log operation (list, list-work, list-plan, etc.)
7. Exit with appropriate code

## Decision Points
- Which log subcommand was provided (list, list-work, list-plan)
- Whether session file exists and is valid
- Whether log files exist and are accessible

## Failure Semantics
- Hard stops if session file is not provided or invalid
- Returns non-zero exit code if log operations fail
- Shows help and exits if required arguments are missing

## Outputs
- Log information to stdout (for list operations)
- Success/failure messages
- Error details if operations fail

## Tests / Fixtures
- No specific tests identified in the provided codebase
- Implementation in `maestro/modules/cli_parser.py` (core subparsers)