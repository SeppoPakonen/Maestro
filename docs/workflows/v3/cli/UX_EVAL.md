# maestro ux eval

**Blindfold UX evaluator** for Maestro CLI discoverability.

## Purpose

The `maestro ux eval` command provides goal-driven evaluation of Maestro's CLI UX by:

1. **Discovering the command surface** using only `--help` text (no parser introspection)
2. **Generating attempt plans** from user goals using keyword matching
3. **Recording telemetry** of command discovery and execution
4. **Producing UX reports** with failure categorization and improvement suggestions

This is an **evaluation harness**, not another assistant. It measures **how discoverable the path to success is from help text alone**.

## Usage

```bash
maestro ux eval "<GOAL>" [OPTIONS]
```

### Arguments

- `<GOAL>` - Goal string to evaluate (e.g., "Create an actionable runbook for building the project")

### Options

- `--repo <PATH>` - Repository root path (default: current directory)
- `--execute` - Actually execute commands (default: dry-run preview only)
- `-v, --verbose` - Show decision summary and discovered commands count
- `-vv, --very-verbose` - Additionally show bounded help excerpts and reasoning trace
- `--json` - Output summary as JSON to stdout
- `--out <PATH>` - Output directory for report (default: docs/workflows/v3/reports/ux_eval_<timestamp>)

## Examples

### Basic Evaluation (Dry-Run)

```bash
maestro ux eval "Create an actionable runbook for building the project"
```

Discovers CLI surface via help, generates attempt plan, but **does not execute** commands (safe default).

### Verbose Mode

```bash
maestro ux eval "Make a green loop plan for build→scan→issues→fix" -v
```

Shows:
- Discovered command count
- Help calls made
- Decision summary

### Very Verbose Mode

```bash
maestro ux eval "Create a runbook" -vv
```

Additionally shows:
- Bounded help excerpts (first 500 chars per command)
- Reasoning trace for attempt plan
- Discovery progress

### Execute Mode

```bash
maestro ux eval "List all plans" --execute
```

Actually runs discovered commands (not dry-run). Use with caution!

### JSON Output

```bash
maestro ux eval "Create a plan" --json
```

Outputs machine-readable summary:

```json
{
  "eval_id": "ux_eval_20260102_143052",
  "goal": "Create a plan",
  "output_dir": "docs/workflows/v3/reports/ux_eval_20260102_143052",
  "discovered_commands": 45,
  "help_calls": 12,
  "total_attempts": 5,
  "successful_attempts": 1,
  "failed_attempts": 4,
  "dry_run": true
}
```

### Custom Output Directory

```bash
maestro ux eval "Build the project" --out custom/ux_reports/eval_001
```

## How It Works

### Step 1: Discover CLI Surface

Runs `MAESTRO_BIN --help` and recursively crawls subcommands:

- Calls `maestro --help` to discover top-level commands
- For each discovered command, calls `maestro <cmd> --help`
- Recursively discovers subcommands (bounded by budget)
- Extracts command names from help text patterns:
  - `{cmd1,cmd2,cmd3}` format
  - Lines starting with command names

**Budgets**:
- Max 80 command nodes
- Max 300KB total help text
- 5-second timeout per help call
- Max recursion depth: 4

### Step 2: Generate Attempt Plan

Takes the goal string and discovered surface, produces ranked attempts:

1. **Extract keywords** from goal (filter stop words)
2. **Score commands** based on keyword matches:
   - Command path match: +10 points
   - Subcommand match: +5 points
   - Help text match: +1 point
3. **Rank by score** (descending, ties broken by command name)
4. **Select top 10 attempts**

**Deterministic**: Same goal + same surface = same attempts (no randomness).

### Step 3: Execute Attempts

Runs each attempt (or dry-run):

- **Dry-run (default)**: Records attempt structure without executing
- **Execute mode**: Runs commands with 30-second timeout
- **Captures**:
  - Exit code
  - Duration (ms)
  - Stdout/stderr (bounded to 2000 chars each)
  - Timeout/unknown command flags

### Step 4: Generate UX Report

Produces markdown report with:

- **Goal** and discovered surface summary
- **Attempts timeline** (first 5 attempts)
- **Failure categorization**:
  - Timeouts
  - Unknown commands
  - Help ambiguity / unclear errors
  - Other failures
- **Suggested improvements** (ranked by priority):
  - Help structure
  - Performance
  - Discoverability
  - Onboarding
- **Next best command** to try

## What Gets Measured

### Discoverability Metrics

- **Command discovery rate**: How many commands found via help crawl
- **Help call count**: Number of `--help` invocations needed
- **Attempt success rate**: How many attempts succeeded
- **Failure categorization**: Types of failures encountered
- **Help/attempt ratio**: Efficiency of discovery

### UX Quality Indicators

- **High unknown command count** → Poor subcommand discovery in help
- **High timeout count** → Performance or async issues
- **High help/attempt ratio** → Unclear help text, requires multiple lookups
- **Zero successful attempts** → Missing examples or onboarding

## Safety Features

1. **Dry-run by default**: Commands not executed unless `--execute` is explicit
2. **Bounded output**: All outputs (help text, stdout, stderr) are truncated with markers
3. **No parser introspection**: Evaluator only uses strings learned from help text
4. **Timeouts enforced**: Commands and help calls have time limits
5. **Respects MAESTRO_DOCS_ROOT**: All writes go to configured docs directory

## Output Files

### Report Directory Structure

```
docs/workflows/v3/reports/ux_eval_<timestamp>/
├── ux_eval_<timestamp>.md        # Human-readable report
├── telemetry.json                # Telemetry summary
├── attempts.jsonl                # Detailed attempt records (one per line)
└── surface.json                  # Discovered command surface
└── surface.txt                   # Human-readable surface excerpts
```

### Telemetry JSON Schema

```json
{
  "eval_id": "string",
  "goal": "string",
  "total_attempts": "number",
  "successful_attempts": "number",
  "failed_attempts": "number",
  "help_call_count": "number",
  "timeout_count": "number",
  "unknown_command_count": "number"
}
```

### Attempts JSONL Schema

Each line is a JSON object:

```json
{
  "attempt_index": 0,
  "command_argv": ["maestro", "plan", "list"],
  "exit_code": 0,
  "duration_ms": 150,
  "stdout_excerpt": "...",
  "stderr_excerpt": "...",
  "timestamp": "2025-01-02T14:30:00",
  "timed_out": false
}
```

## Environment Variables

- **`MAESTRO_BIN`**: Path to maestro executable (default: inferred from sys.argv[0])
- **`MAESTRO_DOCS_ROOT`**: Override docs root for output (default: current directory)

## Use Cases

### Evaluate New Feature Discoverability

```bash
# After adding new "maestro plan sprint" command
maestro ux eval "Run a sprint on top 5 tasks" -vv
```

Check report to see if evaluator discovered the new command path.

### Measure Help Text Quality

```bash
# Test if goal keywords lead to correct commands
maestro ux eval "Create a runbook for repository analysis" --execute
```

If successful attempts are low, help text may need better keywords or structure.

### Regression Testing CLI UX

```bash
# Before and after help text changes
maestro ux eval "Decompose a goal into tasks" --json > before.json
# ... make help text changes ...
maestro ux eval "Decompose a goal into tasks" --json > after.json
diff before.json after.json
```

Compare discovered commands and success rates.

## Limitations

1. **No semantic understanding**: Evaluator uses keyword matching, not AI
2. **Help-dependent**: Only discovers what's visible in help text
3. **No interactive flows**: Cannot handle multi-step wizard-like commands
4. **Dry-run limitations**: Cannot test actual command behavior without `--execute`

## See Also

- [CLI Surface Contract](./CLI_SURFACE_CONTRACT.md) - Command surface guarantees
- [CLI Signatures](./SIGNATURES.md) - All command signatures
- [CLI Tree](./TREE.md) - Command hierarchy
