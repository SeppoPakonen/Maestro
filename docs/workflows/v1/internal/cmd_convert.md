# cmd_convert.md - Convert Command Internal Workflow

## Synopsis
- Command: `convert`
- Aliases: `c`
- Subcommands: new, plan, run, status, show, reset, batch
- Example invocations:
  - `maestro convert new pipeline1`
  - `maestro convert run pipeline1`
  - `maestro convert batch run`

## Purpose
Provides format conversion tools and pipelines to transform data between different formats or systems.

## Inputs
- CLI args: Subcommands and their specific arguments (pipeline names, etc.)
- Config inputs: Conversion pipeline configurations
- Required environment: Initialized repository with conversion configurations

## State & Storage
- Reads: Conversion pipeline configurations, source data
- Writes: Converted data, pipeline status, logs
- Does not require `--session`

## Internal Flow
1. Parse command from CLI
2. Identify command as 'convert'
3. Parse subcommand and arguments
4. Route to appropriate convert subcommand handler
5. Execute conversion operation (new pipeline, run, status, etc.)
6. Update pipeline status/logs as needed
7. Exit with appropriate code

## Decision Points
- Which convert subcommand was provided (new, plan, run, status, show, reset, batch)
- Whether pipeline configuration exists
- Whether source data is available for conversion

## Failure Semantics
- Returns non-zero exit code if conversion operations fail
- Shows help and exits if required arguments are missing
- May hard stop if pipeline configuration is invalid

## Outputs
- Conversion progress and results to stdout
- Pipeline status information
- Success/failure messages
- Error details if operations fail

## Tests / Fixtures
- No specific tests identified in the provided codebase
- Implementation in `maestro/commands/convert.py`