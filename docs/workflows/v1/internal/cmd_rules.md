# cmd_rules.md - Rules Command Internal Workflow

## Synopsis
- Command: `rules`
- Aliases: `r`
- Subcommands: list, edit
- Example invocations:
  - `maestro rules list`
  - `maestro rules edit`

## Purpose
Manages project rules which define constraints, guidelines, or automation rules for the project.

## Inputs
- CLI args: Subcommands and their specific arguments
- Config inputs: Session file (required via --session), rules configuration
- Required environment: Initialized repository with existing session

## State & Storage
- Reads: Rules configuration files, session file
- Writes: Updates to rules configuration files, session file
- Requires `--session` for operations

## Internal Flow
1. Parse command from CLI
2. Identify command as 'rules'
3. Parse subcommand and arguments
4. Load session if required
5. Route to appropriate rules subcommand handler
6. Execute rules operation (list, edit, etc.)
7. Update session/rules as needed
8. Exit with appropriate code

## Decision Points
- Which rules subcommand was provided (list, edit, etc.)
- Whether session file exists and is valid
- Whether rules configuration exists and is accessible

## Failure Semantics
- Hard stops if session file is not provided or invalid
- Returns non-zero exit code if rules operations fail
- Shows help and exits if required arguments are missing

## Outputs
- Rules information to stdout (for list operations)
- Success/failure messages
- Error details if operations fail

## Tests / Fixtures
- No specific tests identified in the provided codebase
- Implementation in `maestro/modules/cli_parser.py` (core subparsers)