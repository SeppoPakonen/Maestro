# Maestro UX Blindfold Audit with Qwen

## Purpose

The qwen-driven blindfold UX audit harness evaluates Maestro's CLI discoverability using **only `--help` text and command outputs**. This is a meta-evaluation tool that helps identify UX friction by testing whether a user (represented by the `qwen` LLM) can successfully discover and use Maestro commands without any argparse internals or source code access.

**Key Principle**: Qwen only sees what a real user would see - help pages and command results. This tests whether Maestro's help text is sufficient for discovery.

## How It Works

1. **Goal Input**: You provide a high-level goal (e.g., "Create an actionable runbook for building and testing this repo")
2. **Qwen Planning**: The qwen LLM generates a sequence of actions (help requests, command runs) to achieve the goal
3. **Execution**: The harness executes each action and feeds results back to track progress
4. **Analysis**: Qwen identifies friction points and generates improvement suggestions
5. **Artifacts**: Detailed transcript, telemetry, and human-readable report are saved

## Protocol

Qwen emits NDJSON (newline-delimited JSON) with these action types:

- `{"action":"help","argv":["maestro","--help"]}` - Request a help page
- `{"action":"run","argv":["maestro","track","list"]}` - Run a command
- `{"action":"note","text":"exploring commands"}` - Optional commentary
- `{"action":"done","result":{...}}` - Final summary with improvement suggestions

## Safety Rules

### Safe Mode (Default)

By default, the harness runs in **safe mode** which:
- Blocks commands with write verbs: `add`, `enact`, `run`, `resolve`, `prune`, `archive`, `restore`, `delete`, `remove`, `link`, `commit`
- Blocks commands with write flags: `--execute`, `--write`, `--apply`
- Records blocked attempts as friction points
- Only allows read operations

### Execute Mode (--execute)

When `--execute` is provided:
- Write commands are allowed
- `MAESTRO_DOCS_ROOT` is forced to a sandboxed directory: `<repo>/docs/maestro`
- Writes outside this directory are blocked by Maestro itself
- Use with caution - only on test repositories

## How to Run

### Basic Usage

```bash
cd <target_repo>
tools/ux_blindfold/qwen_coach.sh --goal "Your goal here"
```

### With Custom Maestro Binary

```bash
tools/ux_blindfold/qwen_coach.sh \
  --goal "Create a runbook" \
  --maestro-bin "/path/to/maestro"
```

### In Execute Mode (Caution!)

```bash
tools/ux_blindfold/qwen_coach.sh \
  --goal "Generate and save a runbook" \
  --execute
```

### Example Goals

**Goal 1: Runbook Discovery**
```bash
tools/ux_blindfold/qwen_coach.sh \
  --goal "Create an actionable runbook for building and testing this repo"
```

**Goal 2: Plan Creation**
```bash
tools/ux_blindfold/qwen_coach.sh \
  --goal "Make a green loop plan from build failures"
```

**Goal 3: List Operations**
```bash
tools/ux_blindfold/qwen_coach.sh \
  --goal "List existing runbooks and show the newest one"
```

**Goal 4: Track Exploration**
```bash
tools/ux_blindfold/qwen_coach.sh \
  --goal "Explore available tracks and show their current status"
```

## Budgets and Limits

The harness enforces these limits to ensure deterministic, bounded execution:

- **Max help calls**: 10
- **Max steps**: 12 (configurable via `--max-steps`)
- **Max output per command**: 4000 chars (truncated deterministically)
- **Max total transcript**: 120k chars
- **Timeouts**:
  - Help requests: 5 seconds
  - Run commands: 20 seconds (configurable via `MAESTRO_UX_QWEN_RUN_TIMEOUT`)

## Output Artifacts

All artifacts are saved to:
```
docs/workflows/v3/reports/ux_blindfold/<UTC_TIMESTAMP>_<shortsha>/
```

### Files Generated

1. **`report.md`** - Human-friendly summary with:
   - Execution summary (successes, failures, blocked writes)
   - Failure breakdown by type
   - Friction points identified by qwen
   - Prioritized improvement suggestions

2. **`transcript.jsonl`** - Full event log (NDJSON format):
   - Every help request and result
   - Every command execution and output
   - Blocked write attempts
   - Qwen notes and final result

3. **`telemetry.json`** - Aggregate statistics:
   - Counts (help calls, run attempts, successes, failures)
   - Timing data
   - Budget usage

4. **`qwen_prompt.txt`** - Exact prompt sent to qwen including:
   - Goal
   - Protocol definition
   - Safety rules
   - Initial help surface

5. **`surface_seed.txt`** - Top-level Maestro help output used as initial context

## Interpreting Results

### Success Indicators

- **High success rate**: Most commands return 0 exit code
- **Few blocked writes**: Goal achieved with mostly read operations
- **Low friction**: Few friction points reported by qwen
- **Quick discovery**: Commands found within help budget

### Friction Indicators

- **Many unknown commands**: Help text doesn't surface available commands
- **Blocked writes in safe mode**: Goal requires writes but isn't achievable read-only
- **High failure rate**: Commands fail due to syntax errors or missing arguments
- **Help budget exhausted**: Too many help pages needed for discovery
- **Timeouts**: Commands hang or take too long

### Improvement Suggestions

Qwen provides prioritized suggestions with:
- **Priority**: P0 (critical), P1 (high), P2 (medium)
- **Area**: help text, command discovery, error messages, etc.
- **Proposed Change**: Specific UX improvement
- **Expected Impact**: How it reduces friction
- **Evidence**: Link to transcript events

## Troubleshooting

### Error: qwen binary not found

**Solution**: Install qwen or add it to PATH
```bash
which qwen  # Check if qwen is installed
export PATH="$PATH:/path/to/qwen"  # Add to PATH if needed
```

### Error: Command timed out

**Cause**: Command took longer than timeout limit

**Solutions**:
- Increase timeout: `export MAESTRO_UX_QWEN_RUN_TIMEOUT=60`
- Simplify goal to reduce command complexity
- Check if Maestro command is hanging

### Error: Help budget exceeded

**Cause**: Qwen needed more than 10 help pages

**Solution**: Increase budget by modifying `MAX_HELP_CALLS` in `qwen_driver.py`, or simplify goal

### Warning: Noisy output in transcript

**Cause**: Commands produce excessive stdout/stderr

**Solution**: This is expected - output is truncated to 4000 chars per command. Check `transcript.jsonl` for full details (up to truncation point).

### Error: Write blocked in safe mode

**Cause**: Goal requires write operations but `--execute` not provided

**Solutions**:
- Run in execute mode: `--execute` (caution: only on test repos)
- Rephrase goal to be read-only (e.g., "Show how to create a runbook" instead of "Create a runbook")

## Example Session

```bash
$ cd ~/Dev/BatchScriptShell

$ tools/ux_blindfold/qwen_coach.sh --goal "Create an actionable runbook for building and testing this repo"

Starting qwen-driven blindfold UX audit...
Goal: Create an actionable runbook for building and testing this repo
Repo: /home/user/Dev/BatchScriptShell
Execute mode: No (safe)

Running qwen...
Qwen generated 8 actions
Executing actions...
Saving artifacts...

============================================================
AUDIT COMPLETE
============================================================
Report: docs/workflows/v3/reports/ux_blindfold/20260103T123045Z_a3f5b8c2/report.md

Steps executed: 8
Successes: 5
Failures: 1
Blocked writes: 2

Top 3 Recommendations:
  1. [P1] help text: Add example of resolve command with -- separator
  2. [P2] command discovery: Include subcommand examples in top-level help
  3. [P2] error messages: Clarify when -- separator is required for freeform input
```

## Best Practices

1. **Start with read-only goals**: Test discovery before testing execution
2. **Use specific goals**: "List tracks and show the first one" is better than "Explore tracks"
3. **Run on test repos**: Never run with `--execute` on production repositories
4. **Review artifacts**: Check `transcript.jsonl` for detailed execution flow
5. **Iterate**: Use improvement suggestions to fix help text, then re-run audit

## Integration with Development Workflow

### After Adding New Commands

```bash
# Test that new command is discoverable
tools/ux_blindfold/qwen_coach.sh --goal "Use the new <command> feature"
```

### Before Releasing

```bash
# Audit common user journeys
tools/ux_blindfold/qwen_coach.sh --goal "Create a runbook for a Python project"
tools/ux_blindfold/qwen_coach.sh --goal "Set up a new track with phases and tasks"
```

### When Help Text Changes

```bash
# Verify discoverability improvements
tools/ux_blindfold/qwen_coach.sh --goal "Original difficult goal"
# Compare report.md friction points before/after help text changes
```

## Advanced Usage

### Custom Maestro Binary

```bash
# Test development version
tools/ux_blindfold/qwen_coach.sh \
  --goal "..." \
  --maestro-bin "python /path/to/dev/maestro.py"
```

### Custom Qwen Binary

```bash
# Use specific qwen version
python tools/ux_blindfold/qwen_driver.py \
  --goal "..." \
  --qwen-bin "/opt/qwen-2.5/bin/qwen"
```

### Different Repository

```bash
tools/ux_blindfold/qwen_coach.sh \
  --goal "..." \
  --repo "/path/to/other/repo"
```

### Increase Step Limit

```bash
python tools/ux_blindfold/qwen_driver.py \
  --goal "Complex multi-step task" \
  --max-steps 20
```

## Limitations

1. **Single-shot planning**: Qwen emits entire action sequence upfront (no multi-turn feedback loop in v1)
2. **No interactive commands**: Commands requiring stdin are not supported
3. **No file inspection**: Qwen cannot read generated files (only command outputs)
4. **Timeout constraints**: Long-running commands (>20s default) will timeout

## See Also

- [UX Evaluation](./SIGNATURES.md#ux-eval) - Automated UX testing framework
- [UX Postmortem](./SIGNATURES.md#ux-postmortem) - Friction analysis from real sessions
- [Runbook Resolve](./RUNBOOK_RESOLVE.md) - AI-powered runbook generation
- [TREE.md](./TREE.md) - Full CLI command tree
