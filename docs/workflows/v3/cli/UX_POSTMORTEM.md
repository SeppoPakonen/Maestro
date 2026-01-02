# maestro ux postmortem

**Convert UX eval findings into actionable issues and WorkGraph** for fixing CLI discoverability problems.

## Purpose

The `maestro ux postmortem` command closes the loop on UX evaluation by:

1. **Loading UX eval artifacts** (telemetry, attempts, surface, report)
2. **Building a synthetic log** from failed attempts and friction signals
3. **Running log scan** to extract structured findings
4. **Creating issues** from findings (deduped by fingerprints)
5. **Optionally decomposing into WorkGraph** for portfolio sprint planning

This is the "autopipeline v1" that turns **UX friction into capital**: every discoverability failure becomes traceable, actionable work.

## Usage

```bash
maestro ux postmortem <EVAL_ID> [OPTIONS]
```

### Arguments

- `<EVAL_ID>` - UX eval ID to process (e.g., `ux_eval_20260102_143052`)

### Options

- `--execute` - Actually run pipeline (default: preview only)
- `--issues` - Create issues from findings (requires `--execute`)
- `--decompose` - Create WorkGraph for fixes (requires `--execute` and `--issues`)
- `--profile {investor|purpose|default}` - WorkGraph profile for decompose (default: `default`)
- `-v, --verbose` - Show detailed output
- `-vv, --very-verbose` - Show all pipeline commands and outputs
- `--json` - Output summary as JSON to stdout

## Examples

### Basic Preview (Safe, No Writes)

```bash
maestro ux postmortem ux_eval_20260102_143052
```

Shows what would be done without executing commands or writing files (safe default).

### Execute Log Scan Only

```bash
maestro ux postmortem ux_eval_20260102_143052 --execute
```

Creates synthetic log and runs log scan, but doesn't create issues.

### Execute Full Pipeline (Log Scan + Issues)

```bash
maestro ux postmortem ux_eval_20260102_143052 --execute --issues
```

Creates synthetic log, runs log scan, and creates issues from findings.

### Execute with WorkGraph Decompose

```bash
maestro ux postmortem ux_eval_20260102_143052 --execute --issues --decompose --profile investor
```

Full pipeline: log scan → issues → WorkGraph with investor profile (prioritizes ROI).

### Verbose Mode

```bash
maestro ux postmortem ux_eval_20260102_143052 --execute --issues -v
```

Shows detailed output with step-by-step progress.

### Very Verbose Mode

```bash
maestro ux postmortem ux_eval_20260102_143052 --execute --issues --decompose -vv
```

Shows all subprocess commands, inputs, and outputs (bounded to 500 chars).

### JSON Output

```bash
maestro ux postmortem ux_eval_20260102_143052 --execute --issues --json
```

Outputs machine-readable summary:

```json
{
  "eval_id": "ux_eval_20260102_143052",
  "mode": "execute",
  "create_issues": true,
  "decompose": false,
  "profile": "default",
  "log_file": "docs/maestro/ux_eval/ux_eval_20260102_143052/ux_postmortem/ux_log.txt",
  "scan_id": "SCAN-20260102-abc123",
  "issues_created": ["ISSUE-001", "ISSUE-002"],
  "workgraph_id": null
}
```

## How It Works

### Step 1: Load UX Eval Artifacts

Loads from `docs/maestro/ux_eval/<EVAL_ID>/`:
- `telemetry.json` - Eval summary
- `attempts.jsonl` - Command attempt records
- `surface.json` - Discovered CLI surface
- `<EVAL_ID>.md` - UX evaluation report

### Step 2: Build Synthetic Log

Creates a deterministic synthetic log shaped for the existing log scanner:

- **Tool markers**: `tool: plan decompose` (for log scanner)
- **Error lines**: `error: Command timed out` (for finding extraction)
- **Status markers**: `status: TIMEOUT`, `status: UNKNOWN_COMMAND`, `status: FAILED`
- **UX friction signals**:
  - `signal: high_unknown_command_rate` → Poor subcommand discovery
  - `signal: command_timeouts` → Performance issues
  - `signal: high_help_to_attempt_ratio` → Unclear help text
  - `signal: zero_successful_attempts` → Missing examples/onboarding
- **Bounded excerpts**: stdout/stderr limited to 500 chars, first 10 lines
- **Failure summary**: Categorizes timeouts, unknown commands, other failures

**Determinism**: Same eval ID → same log content (character-for-character).

### Step 3: Run Log Scan (If Execute Mode)

```bash
maestro log scan --source <ux_log.txt> --kind run
```

Extracts structured findings from synthetic log. Returns scan ID for issue creation.

### Step 4: Create Issues (If --issues)

```bash
maestro issues add --from-log <SCAN_ID>
```

Creates issues from scan findings. Issues are:
- **Deduped by fingerprints**: Re-running postmortem won't duplicate issues
- **Categorized by friction type**: Help text, performance, onboarding
- **Prioritized by impact**: High unknown command rate → P1 issue

### Step 5: Decompose into WorkGraph (If --decompose)

```bash
maestro plan decompose --domain issues --profile <PROFILE> -e
```

Input: `"Improve CLI discoverability for goal: <ORIGINAL_GOAL>\n\nFocus on fixing help text, subcommand discovery, and onboarding."`

Creates a WorkGraph with:
- **Tracks/Phases/Tasks** for fixing UX issues
- **Definition of Done** tied to issue closures
- **Evidence pack** from repo discovery

**Profiles**:
- `investor`: Prioritizes time-to-first-success, ROI metrics
- `purpose`: Prioritizes clarity, user intent alignment
- `default`: Balanced approach

### Step 6: Record Metadata

Saves to `docs/maestro/ux_eval/<EVAL_ID>/ux_postmortem/`:
- `ux_log.txt` - Synthetic log
- `postmortem.json` - Full metadata record
- `scan_id.txt` - Scan ID (if executed)
- `issues_created.json` - Issue IDs + fingerprints (if executed)
- `workgraph_id.txt` - WorkGraph ID (if executed)

### Step 7: Emit Machine-Readable Markers

Preview mode:
```
MAESTRO_UX_EVAL_ID=ux_eval_20260102_143052
```

Execute mode:
```
MAESTRO_UX_EVAL_ID=ux_eval_20260102_143052
MAESTRO_UX_POSTMORTEM_SCAN_ID=SCAN-20260102-abc123
MAESTRO_UX_POSTMORTEM_ISSUES=2
MAESTRO_UX_POSTMORTEM_WORKGRAPH_ID=wg-20260102-def456
```

## What Gets Measured

### Friction Signal Detection

- **High unknown command rate**: (unknown_count / total_attempts) > 0.3 → Poor subcommand discovery
- **Command timeouts**: Any timeout → Performance or async issues
- **High help/attempt ratio**: (help_calls / attempts) > 3 → Unclear help text
- **Zero successful attempts**: All attempts failed → Missing examples/onboarding

### Issue Prioritization Heuristics

- **P1 (High)**: Zero successful attempts, high unknown command rate
- **P2 (Medium)**: Command timeouts, high help/attempt ratio
- **P3 (Low)**: Occasional failures, minor friction

## Safety Features

1. **Preview by default**: Commands not executed unless `--execute` is explicit
2. **Deterministic log**: Same eval → same synthetic log (no randomness)
3. **Bounded output**: All excerpts truncated with markers (no unbounded storage)
4. **Idempotent**: Re-running doesn't duplicate issues (fingerprint-based dedup)
5. **Respects MAESTRO_DOCS_ROOT**: All writes go to configured docs directory
6. **No CLI parser introspection**: Uses only stored artifacts and subprocess calls

## Output Files

### Postmortem Directory Structure

```
docs/maestro/ux_eval/<EVAL_ID>/ux_postmortem/
├── ux_log.txt              # Synthetic log (deterministic)
├── postmortem.json         # Full metadata record
├── scan_id.txt             # Scan ID (if executed)
├── issues_created.json     # Issue IDs + fingerprints (if executed)
└── workgraph_id.txt        # WorkGraph ID (if executed)
```

### Postmortem JSON Schema

```json
{
  "eval_id": "string",
  "timestamp": "ISO8601",
  "mode": "execute",
  "log_file": "path/to/ux_log.txt",
  "scan_id": "SCAN-...",
  "issues_created": ["ISSUE-001", "ISSUE-002"],
  "workgraph_id": "wg-...",
  "profile": "investor"
}
```

## Environment Variables

- **`MAESTRO_DOCS_ROOT`**: Override docs root for output (default: current directory)

## Use Cases

### Close the Loop After UX Eval

```bash
# Step 1: Run UX eval
maestro ux eval "Create a runbook for building the project" --execute

# Step 2: Review report
maestro ux show ux_eval_20260102_143052

# Step 3: Run postmortem (preview first)
maestro ux postmortem ux_eval_20260102_143052

# Step 4: Execute pipeline
maestro ux postmortem ux_eval_20260102_143052 --execute --issues --decompose --profile investor

# Step 5: Materialize WorkGraph
maestro plan enact wg-20260102-def456
```

### Track UX Debt Over Time

```bash
# Run postmortem on multiple evals
for eval_id in $(maestro ux list --json | jq -r '.evals[].eval_id'); do
  maestro ux postmortem $eval_id --execute --issues --json >> ux_debt_log.jsonl
done

# Analyze trends
jq -r '[.eval_id, .issues_created | length] | @csv' ux_debt_log.jsonl
```

### Sprint Planning from UX Findings

```bash
# Generate WorkGraph with investor profile
maestro ux postmortem ux_eval_20260102_143052 --execute --issues --decompose --profile investor

# Materialize into Track/Phase/Task
maestro plan enact wg-20260102-def456

# Run sprint on top 5 tasks
maestro plan sprint wg-20260102-def456 --top 5 --profile investor
```

## Limitations

1. **No semantic understanding**: Friction signals use keyword matching and heuristics, not AI
2. **Depends on log scanner**: Issue quality depends on log scan extraction accuracy
3. **Execute mode requires real commands**: Cannot fully test execute mode without maestro CLI installed
4. **Single eval at a time**: Does not aggregate findings across multiple evals (yet)

## Integration with Existing Maestro Commands

### Upstream Commands

- `maestro ux eval` - Runs UX evaluation (prerequisite)
- `maestro ux list` - Lists available evals
- `maestro ux show` - Shows eval summary

### Downstream Commands

- `maestro log scan` - Scans synthetic log (called by postmortem)
- `maestro issues add` - Creates issues from scan (called by postmortem)
- `maestro plan decompose` - Creates WorkGraph (called by postmortem)
- `maestro plan enact` - Materializes WorkGraph into Track/Phase/Task
- `maestro plan sprint` - Runs sprint on WorkGraph tasks

## Next Steps After Postmortem

1. **Review issues**: `maestro issues list`
2. **Materialize WorkGraph**: `maestro plan enact <WG_ID>`
3. **Run sprint**: `maestro plan sprint <WG_ID> --top 5`
4. **Close issues as fixed**: `maestro issues state <ISSUE_ID> resolved`
5. **Re-run UX eval**: Verify improvements with new eval

## See Also

- [UX Eval](./UX_EVAL.md) - Blindfold UX evaluator (prerequisite)
- [CLI Signatures](./SIGNATURES.md) - All command signatures
- [CLI Tree](./TREE.md) - Command hierarchy
- [CLI Invariants](./INVARIANTS.md) - UX postmortem invariants
