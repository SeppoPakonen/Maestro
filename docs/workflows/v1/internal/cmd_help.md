# cmd_help.md - Help Command Internal Workflow

## Synopsis
- Command: `help` 
- Aliases: `h`
- No subcommands
- Example invocation: `maestro help` or `maestro h`

## Purpose
Displays help information for all available Maestro commands and their usage.

## Inputs
- No CLI arguments required
- No config inputs
- No required environment

## State & Storage
- Does not read or write any state
- Does not require `--session`
- Does not interact with repository or session files

## Internal Flow
1. Parse command from CLI
2. Identify command as 'help'
3. Print help information using the main parser's help formatter
4. Exit with code 0

## Decision Points
- No decision points - the command always executes successfully

## Failure Semantics
- No failure conditions - always displays help and exits with code 0

## Outputs
- Prints formatted help text to stdout
- Includes styled output with color coding
- Shows all available commands and their aliases
- Displays global options

## Tests / Fixtures
- No specific tests identified in the provided codebase
- Functionality is built into argparse library