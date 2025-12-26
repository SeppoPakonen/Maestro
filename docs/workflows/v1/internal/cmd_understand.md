# cmd_understand.md - Understand Command Internal Workflow

## Synopsis
- Command: `understand`
- Aliases: `u`
- Subcommands: dump
- Example invocations:
  - `maestro understand dump`
  - `maestro u dump --output-path ./analysis.json`

## Purpose
Provides project understanding commands to analyze and document the structure and content of the project.

## Inputs
- CLI args: Subcommands and their specific arguments (output path, check flag, etc.)
- Config inputs: None required
- Required environment: Initialized repository

## State & Storage
- Reads: Project files, repository structure
- Writes: Analysis output files, potentially to specified output path
- Does not require `--session`

## Internal Flow
1. Parse command from CLI
2. Identify command as 'understand'
3. Parse subcommand and arguments
4. Route to appropriate understand subcommand handler
5. Execute understanding operation (dump project analysis)
6. Write analysis results as needed
7. Exit with appropriate code

## Decision Points
- Which understand subcommand was provided (dump, etc.)
- Whether output path is specified and accessible
- Whether check flag is provided for validation

## Failure Semantics
- Returns non-zero exit code if understanding operations fail
- Shows help and exits if required arguments are missing

## Outputs
- Project analysis to specified output path or stdout
- Success/failure messages
- Error details if operations fail

## Tests / Fixtures
- No specific tests identified in the provided codebase
- Implementation in `maestro/commands/understand.py`