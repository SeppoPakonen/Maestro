# cmd_session.md - Session Command Internal Workflow

## Synopsis
- Command: `session`
- Aliases: `s`
- Subcommands: new, list, set, get, remove, details, breadcrumbs, timeline, stats
- Example invocations:
  - `maestro session list`
  - `maestro session new mysession`
  - `maestro session set mysession`

## Purpose
Provides legacy session management functionality for creating, listing, and managing Maestro sessions.

## Inputs
- CLI args: Subcommands and their specific arguments (session names, etc.)
- Config inputs: Session configuration, session files
- Required environment: Initialized repository

## State & Storage
- Reads: Session files, session metadata
- Writes: Session files, session metadata, active session state
- Does not require `--session` for most operations

## Internal Flow
1. Parse command from CLI
2. Identify command as 'session'
3. Parse subcommand and arguments
4. Route to appropriate session subcommand handler
5. Execute session operation (new, list, set, etc.)
6. Update session state as needed
7. Exit with appropriate code

## Decision Points
- Which session subcommand was provided (new, list, set, get, remove, etc.)
- Whether specified session exists
- Whether user has permissions to modify sessions

## Failure Semantics
- Returns non-zero exit code if session operations fail
- Shows help and exits if required arguments are missing
- May hard stop if session file is corrupted

## Outputs
- Session information to stdout (for list/get operations)
- Success/failure messages
- Error details if operations fail

## Tests / Fixtures
- No specific tests identified in the provided codebase
- Implementation in `maestro/modules/cli_parser.py` (core subparsers) and related session functions