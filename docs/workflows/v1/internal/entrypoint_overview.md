# Maestro Entrypoint Overview

This document describes the internal structure of the Maestro CLI entrypoint and how commands are routed to their respective handlers.

## Entry Point Structure

The main entry point for Maestro is defined in `maestro.py`, which imports and calls the `main()` function from `maestro.main`.

## Command Routing Mechanism

1. **Argument Parsing**: The `create_main_parser()` function in `maestro/modules/cli_parser.py` creates the main argument parser with all subcommands and their aliases.

2. **Session Handling**: Most commands require a `--session` argument which is handled globally by the main parser.

3. **Command Dispatch**: The main function in `maestro/main.py` routes commands to their respective handler functions based on the parsed `args.command` value.

## Key Components

- **Parser Creation**: `maestro/modules/cli_parser.py`
- **Command Handlers**: Various modules in `maestro/commands/`
- **Session Management**: `maestro/session_model.py` and related modules
- **Configuration Loading**: `maestro/config.py`

## Global Options

- `--session`: Required for most commands to specify the session JSON file
- `--verbose`: Enables detailed debug output and file paths
- `--quiet`: Suppresses streaming AI output