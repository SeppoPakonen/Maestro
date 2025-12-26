# cmd_ai.md - AI Command Internal Workflow

## Synopsis
- Command: `ai`
- No aliases
- Subcommands: sync, qwen, gemini, codex, claude
- Example invocations:
  - `maestro ai qwen`
  - `maestro ai gemini`
  - `maestro ai sync`

## Purpose
Provides AI workflow helpers that interface with different AI engines (Qwen, Gemini, Codex, Claude).

## Inputs
- CLI args: Subcommands and their specific arguments for each AI engine
- Config inputs: AI configuration files, API keys
- Required environment: Initialized repository, valid AI credentials

## State & Storage
- Reads: AI configuration, session data (for some subcommands)
- Writes: AI interaction logs, potentially session updates
- Does not require `--session` for all operations

## Internal Flow
1. Parse command from CLI
2. Identify command as 'ai'
3. Parse subcommand and arguments
4. Load AI configuration
5. Route to appropriate AI subcommand handler
6. Execute AI operation (sync, qwen, gemini, etc.)
7. Process AI responses and update state as needed
8. Exit with appropriate code

## Decision Points
- Which AI subcommand was provided (qwen, gemini, codex, claude, sync)
- Whether AI configuration is properly set up
- Whether required API keys are available
- Whether session is needed for the specific operation

## Failure Semantics
- Hard stops if AI configuration is missing or invalid
- Returns non-zero exit code if AI operations fail
- Shows help and exits if required arguments are missing

## Outputs
- AI responses to stdout
- Progress information during sync operations
- Error messages if AI operations fail

## Tests / Fixtures
- No specific tests identified in the provided codebase
- Implementation in `maestro/commands/ai.py`