# Maestro Internal Workflow Documentation

This directory contains code-grounded internal behavior documentation for the Maestro CLI. Each document describes how commands work internally, including their control flow, state management, and dependencies.

## Purpose

This documentation serves as a reference for understanding how Maestro commands work internally. It maps CLI invocations to actual code paths, showing the internal control flow, decision points, and side effects.

## Diagram Style Rules

All PlantUML diagrams in this directory follow these conventions:

- Use swimlanes for different system components
- Include `!include _shared.puml` for consistent styling
- Use predefined macros for common operations
- Show decision points with clear branching logic
- Highlight side effects (reads/writes to state)

## Command Aliases

Maestro supports command aliases for brevity. The following mappings apply:

- `h` → `help`
- `pl` → `plan`
- `tr`/`t` → `track`
- `ph`/`p` → `phase`
- `ta` → `task`
- `cfg`/`config` → `settings`
- `wk` → `work`
- `ws` → `wsession`
- `u` → `understand`
- `c` → `convert`
- `s` → `session`
- `r` → `rules`
- `lg` → `log`
- `rs` → `resume`

## Key Locations

- **Entrypoint**: `maestro/main.py`
- **Argument Parser**: `maestro/modules/cli_parser.py`
- **Command Handlers**: `maestro/commands/`
- **Session Management**: `maestro/session_model.py`
- **Configuration**: `maestro/config.py`

## Documentation Structure

Each command has three associated files:
- `cmd_<command>.md`: Detailed internal workflow description
- `cmd_<command>.puml`: PlantUML diagram source code
- `cmd_<command>.png`: Rendered diagram image

## Global Options

All commands support these global options:

- `--session`: Path to session JSON file (required for most commands)
- `--verbose`: Show detailed debug output, engine commands, and file paths
- `--quiet`: Suppress streaming AI output and extra messages