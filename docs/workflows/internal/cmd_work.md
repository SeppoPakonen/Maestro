# cmd_work.md - Work Command Internal Workflow

## Synopsis
- Command: `work`
- Aliases: `wk`
- Subcommands: any, track, phase, issue, task, discuss, analyze, fix
- Example invocations:
  - `maestro work any`
  - `maestro work track 1`
  - `maestro work discuss`

## Purpose
Manages AI work sessions that perform various development tasks using AI assistance.

## Inputs
- CLI args: Subcommands and their specific arguments (track/phase/task IDs, etc.)
- Config inputs: Session file (required via --session), AI configuration
- Required environment: Initialized repository with existing session and AI configuration

## State & Storage
- Reads: Session file, project context data, task/track/phase information
- Writes: Work session logs, updates to session, task status, code changes
- Requires `--session` for operations

## Internal Flow
1. Parse command from CLI
2. Identify command as 'work'
3. Parse subcommand and arguments
4. Load session if required
5. Route to appropriate work subcommand handler
6. Initialize work session with AI
7. Execute work operation (any, track, phase, etc.)
8. Update session/work logs as needed
9. Exit with appropriate code

## Decision Points
- Which work subcommand was provided (any, track, phase, issue, task, etc.)
- Whether session file exists and is valid
- Whether AI configuration is properly set up
- Whether specified track/phase/task exists

## Failure Semantics
- Hard stops if session file is not provided or invalid
- Hard stops if AI configuration is missing or invalid
- Returns non-zero exit code if work operations fail
- Shows help and exits if required arguments are missing

## Outputs
- Work progress information to stdout
- AI responses during work sessions
- Success/failure messages
- Error details if operations fail

## Tests / Fixtures
- No specific tests identified in the provided codebase
- Implementation in `maestro/commands/work.py`