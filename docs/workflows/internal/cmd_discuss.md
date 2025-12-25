# cmd_discuss.md - Discuss Command Internal Workflow

## Synopsis
- Command: `discuss`
- No aliases
- No subcommands
- Example invocation: `maestro discuss`

## Purpose
Starts an AI discussion using the current context, allowing users to interact with an AI about the project.

## Inputs
- CLI args: Optional arguments for discussion (prompt, etc.)
- Config inputs: Session file (required via --session), AI configuration
- Required environment: Initialized repository with existing session and AI configuration

## State & Storage
- Reads: Session file, project context data
- Writes: Discussion logs, updates to session if applicable
- Requires `--session` for operations

## Internal Flow
1. Parse command from CLI
2. Identify command as 'discuss'
3. Load session if required
4. Load AI configuration
5. Route to discuss handler
6. Initialize AI discussion interface
7. Process user input and AI responses
8. Update session/discussion logs as needed
9. Exit with appropriate code

## Decision Points
- Whether session file exists and is valid
- Whether AI configuration is properly set up
- Whether user wants to continue discussion or exit

## Failure Semantics
- Hard stops if session file is not provided or invalid
- Hard stops if AI configuration is missing or invalid
- Returns non-zero exit code if discussion fails to initialize

## Outputs
- Interactive discussion interface to stdout
- AI responses during the discussion
- Error messages if initialization fails

## Tests / Fixtures
- No specific tests identified in the provided codebase
- Implementation in `maestro/commands/discuss.py`