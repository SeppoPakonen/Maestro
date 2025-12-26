# cmd_resume.md - Resume Command Internal Workflow

## Synopsis
- Command: `resume`
- Aliases: `rs`
- No subcommands
- Example invocation: `maestro resume --session mysession.json`

## Purpose
Resumes a previously saved session, restoring the state and continuing from where work left off.

## Inputs
- CLI args: Session file path (--session), optional flags (dry-run, retry-interrupted, etc.)
- Config inputs: Session file (required via --session), AI configuration
- Required environment: Initialized repository with existing session and AI configuration

## State & Storage
- Reads: Session file, saved state from docs/
- Writes: Updates to session file, work logs, potentially code changes
- Requires `--session` for operation

## Internal Flow
1. Parse command from CLI
2. Identify command as 'resume'
3. Load session from specified file
4. Route to resume handler
5. Restore session state
6. Resume AI work session from last checkpoint
7. Update session state as work continues
8. Exit with appropriate code

## Decision Points
- Whether session file exists and is valid
- Whether session was interrupted and needs to be resumed from specific point
- Whether dry-run mode is enabled
- Whether to retry interrupted operations

## Failure Semantics
- Hard stops if session file is not provided or invalid
- Hard stops if session state is corrupted or inconsistent
- Returns non-zero exit code if resume operations fail

## Outputs
- Resume progress information to stdout
- AI responses during resumed work session
- Success/failure messages
- Error details if operations fail

## Tests / Fixtures
- No specific tests identified in the provided codebase
- Implementation in `maestro/main.py` (handle_resume_session function)