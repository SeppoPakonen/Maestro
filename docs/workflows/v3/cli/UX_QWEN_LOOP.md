

# Qwen Blindfold UX Evaluation Loop

**A meta-evaluation tool that tests Maestro CLI discoverability using real qwen in an iterative loop.**

## What is This?

This is a **development tool** (not a user-facing feature) that helps evaluate and improve Maestro's UX by simulating a new user who only has access to help text and command outputs.

Unlike the single-shot planning harness ([UX_BLINDFOLD_QWEN.md](./UX_BLINDFOLD_QWEN.md)), this runner executes qwen **step-by-step**:
1. Qwen sees help text or command output
2. Qwen decides the next command to run
3. Runner executes the command
4. Qwen sees the result and decides the next step
5. Repeat until goal is accomplished or qwen gets stuck

This iterative approach more closely simulates real user exploration patterns.

## Purpose

- **UX Discovery Testing**: Identify where users get stuck based on help text alone
- **Friction Detection**: Automatically find repeated commands, help loops, and unclear error messages
- **ROI Optimization**: From an "investor" perspective, measure steps-to-success
- **Actionable Reports**: Generate concrete UX fix recommendations based on failure patterns

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Qwen Blindfold Loop Runner                              │
│                                                           │
│  1. Start with: maestro --help                           │
│  2. Qwen reads output → decides next command             │
│  3. Runner executes command (with safety checks)         │
│  4. Qwen sees result → decides next command              │
│  5. Repeat until done/stuck/max_steps                    │
│                                                           │
│  Stuck Detection:                                        │
│  - Repeated commands without progress                    │
│  - Help loops (>70% help calls in recent window)         │
│  - Repeated timeouts or errors                           │
│  - No progress markers (IDs/files) for N steps           │
│                                                           │
│  Output:                                                 │
│  - docs/maestro/ux_eval/<EVAL_ID>/attempts.jsonl        │
│  - docs/maestro/ux_eval/<EVAL_ID>/telemetry.json        │
│  - docs/maestro/ux_eval/<EVAL_ID>/report.md             │
│  - docs/maestro/ux_eval/<EVAL_ID>/surface.txt           │
└─────────────────────────────────────────────────────────┘
```

### Goal-Only Contract

The runner provides qwen with:
- **Goal** (single sentence, e.g., "Create a runbook for building this repo")
- **Last command output** (stdout/stderr/exit code)
- **Constraints** (safety rules, output format)

The runner does **NOT** provide:
- Command suggestions or hints
- List of available subcommands
- Source code or internal documentation

This ensures the evaluation tests **discoverability from help text alone**.

### Safety Policy

**Safe Mode (default)**:
- Only allows `maestro` commands and safe shell reads (`ls`, `cat`, `pwd`, etc.)
- Rejects write operations, network calls, and arbitrary code execution
- Rejections are logged as stuck signals

**Execute Mode** (`--execute` flag):
- Allows write operations
- Should only be used on test repositories or with explicit permission
- Loud warning when enabled

**Allowlist Override** (`--allow-any-command`):
- Removes all safety restrictions
- **DANGER**: Only use in isolated test environments
- Explicit opt-in required

## Usage

### Basic Invocation

```bash
python tools/ux_qwen_loop/run.py \
    --maestro-bin "python /path/to/maestro.py" \
    --repo-root ~/Dev/MyRepo \
    --goal "Create a runbook for building and testing this repo"
```

### With Execute Mode and Postmortem

```bash
python tools/ux_qwen_loop/run.py \
    --maestro-bin "./maestro.py" \
    --repo-root ~/Dev/MyRepo \
    --goal "List all available tracks" \
    --execute \
    --postmortem \
    --profile investor \
    -v
```

### Using the Smoke Script

```bash
# Safe mode (read-only)
tools/smoke/qwen_blindfold_maestro.sh

# Execute mode with postmortem
tools/smoke/qwen_blindfold_maestro.sh --execute

# Custom repo
tools/smoke/qwen_blindfold_maestro.sh --repo ~/Dev/MyProject
```

## Command-Line Options

### Required

- `--maestro-bin CMD` - Path or command to run maestro (e.g., `"./maestro.py"` or `"python -m maestro"`)
- `--repo-root PATH` - Repository root directory (working directory for commands)
- `--goal "..."` - Single-sentence goal for qwen to accomplish

### Optional

- `--qwen-bin CMD` - Qwen binary name or path (default: `qwen`)
- `--max-steps N` - Maximum number of steps (default: `30`)
- `--timeout-help-s N` - Timeout for help commands in seconds (default: `8`)
- `--timeout-cmd-s N` - Timeout for other commands in seconds (default: `60`)
- `--execute` - Allow write operations (default: safe mode blocks writes)
- `--postmortem` - Run `maestro ux postmortem` after evaluation
- `--profile NAME` - Profile for postmortem (default: `investor`)
- `--allow-any-command` - **DANGER**: Allow any command (removes safety)
- `-v` - Verbose output (show progress)
- `-vv` - Very verbose (include qwen prompts and responses, bounded to 2000 chars each)

## Output Artifacts

All artifacts are saved to: `docs/maestro/ux_eval/<EVAL_ID>/`

### EVAL_ID Format

`ux_qwen_YYYYMMDD_HHMMSS_<shortsha>`

Where:
- `YYYYMMDD_HHMMSS` - Timestamp when evaluation started
- `<shortsha>` - First 8 chars of SHA256(goal + repo_root)

This format is:
- **Deterministic**: Same goal + repo → same shortsha
- **Unique per run**: Timestamp ensures different runs don't collide
- **Compatible**: Works with `maestro ux postmortem`

### Files

#### `attempts.jsonl`

Newline-delimited JSON with one event per step:

```json
{
  "step": 1,
  "command": "maestro --help",
  "note": "Starting with top-level help",
  "exit_code": 0,
  "stdout": "Maestro - Task management...",
  "stderr": "",
  "duration": 0.05,
  "timeout": false,
  "rejected": false,
  "rejection_reason": null
}
```

#### `telemetry.json`

Aggregate statistics:

```json
{
  "eval_id": "ux_qwen_20260103_120000_a1b2c3d4",
  "goal": "Create a runbook for building this repo",
  "repo_root": "/home/user/Dev/MyRepo",
  "maestro_bin": "./maestro.py",
  "max_steps": 30,
  "execute": false,
  "start_time": "2026-01-03T12:00:00+00:00",
  "end_time": "2026-01-03T12:05:32+00:00",
  "total_steps": 12,
  "help_calls": 8,
  "run_calls": 4,
  "successes": 10,
  "failures": 2,
  "timeouts": 0,
  "stuck_reason": "help_loop: 8/10 steps are help calls"
}
```

#### `surface.txt`

Top-level help output from `maestro --help` (bounded to prevent huge files).

#### `report.md`

Human-friendly markdown report with:
- **Summary**: Steps, successes, failures, stuck reason
- **Stuck Diagnosis**: Why qwen got stuck (if applicable)
- **Recommended UX Fixes**: Extracted from failure patterns with priority, evidence, proposed change, and expected impact
- **Transcript**: Last 20 steps with commands, outputs, and timings

## Interpreting Results

### Success Indicators

- **Goal accomplished**: `stuck_reason: "done_by_qwen"`
- **Low step count**: Fewer steps = better discoverability
- **High success ratio**: `successes / total_steps > 0.8`
- **Low help ratio**: `help_calls / total_steps < 0.5`

### Friction Indicators

- **Stuck reason is not "done_by_qwen"**: UX issue detected
- **High help ratio**: Commands not discoverable from help text
- **Repeated commands**: User confused about what went wrong
- **Timeouts**: Long-running commands with no progress feedback
- **No progress for N steps**: Success not clearly communicated

### UX Fix Recommendations

The report automatically extracts UX recommendations based on patterns:

| Pattern | Recommendation |
|---------|----------------|
| Repeated command ≥2 times | Improve error message or add usage example |
| Help ratio >50% | Add command suggestions or "next steps" to help text |
| Timeouts >0 | Add progress bars, streaming output, or async execution |
| No progress for N steps | Print clear success messages with IDs or file paths |
| Repeated errors ≥3 | Add input validation with specific error messages |

Each recommendation includes:
- **Priority**: P0 (critical), P1 (high), P2 (medium)
- **Evidence**: Which steps triggered this recommendation
- **Proposed Change**: Specific UX improvement
- **Expected Impact**: How this will help users

## Integration with Maestro UX Postmortem

The artifact format is compatible with `maestro ux postmortem`, enabling automatic issue creation and workgraph generation:

### Manual Integration

```bash
# 1. Run qwen evaluation
python tools/ux_qwen_loop/run.py \
    --maestro-bin "./maestro.py" \
    --repo-root ~/Dev/MyRepo \
    --goal "Create a runbook" \
    --execute

# Note the EVAL_ID from output (e.g., ux_qwen_20260103_120000_a1b2c3d4)

# 2. Run postmortem manually
maestro ux postmortem ux_qwen_20260103_120000_a1b2c3d4 \
    --issues --decompose --profile investor --execute

# 3. Enact the workgraph
maestro plan enact <WG_ID> --profile investor
```

### Automatic Integration

Use `--postmortem` flag to chain automatically:

```bash
python tools/ux_qwen_loop/run.py \
    --maestro-bin "./maestro.py" \
    --repo-root ~/Dev/MyRepo \
    --goal "Create a runbook" \
    --execute \
    --postmortem \
    --profile investor
```

This will:
1. Run qwen evaluation
2. Export artifacts
3. Automatically run `maestro ux postmortem <EVAL_ID> --issues --decompose --profile investor --execute`
4. Print next steps for enacting the workgraph

## Investor Framing

From an **investor perspective**, this tool answers:

**"How many steps does it take for a new user to accomplish X?"**

- **Fewer steps** = Higher ROI (faster time-to-value)
- **Stuck signals** = Lost users (abandonment risk)
- **Help loops** = Wasted time (opportunity cost)

The `--profile investor` flag optimizes for:
- **High-priority fixes** (P0/P1) that reduce steps-to-success
- **Clear ROI** in recommendations ("reduce confusion" → "faster task completion")
- **Evidence-based** (every recommendation tied to specific transcript steps)

## Stuck Detection

### Mechanisms

The runner uses **deterministic** stuck detection with these signals:

1. **Repeated Command** (≥2 times without progress)
   - Command normalized (env vars stripped, -h → --help, multiple spaces collapsed)
   - Progress = new IDs detected (wg-*, RUN-*, TRK-*, etc.) or new files in docs/maestro

2. **Help Loop** (>70% of last 10 steps are help calls)
   - Indicates difficulty discovering the right command
   - Tunable threshold and window size

3. **Repeated Timeout** (same command times out ≥2 times)
   - Indicates performance issue or missing progress feedback

4. **Repeated Error** (same error pattern ≥3 times)
   - Error patterns: unknown_command, invalid_argument, not_found, permission_denied, exit codes
   - Indicates unclear error messages or input validation

5. **No Progress** (≥8 steps without new IDs or files)
   - Indicates unclear success indicators
   - Tunable step threshold

### Customization

You can adjust stuck detection thresholds by modifying `StuckDetector` initialization in `run.py`:

```python
self.stuck_detector = StuckDetector(
    max_repeated=2,           # Repeated command threshold
    help_loop_threshold=0.7,  # 70% help ratio
    help_loop_window=10,      # Window size for help ratio
    no_progress_steps=8       # Steps before "no progress" stuck
)
```

## Troubleshooting

### Qwen Not Found

```
Error: qwen is not installed or not in PATH
```

**Solution**: Install qwen:
```bash
pip install qwen-cli  # Or your qwen installation method
```

### Safe Mode Rejections

```
Command rejected by safety policy: curl http://example.com
```

**Cause**: Safe mode blocks non-allowlisted commands.

**Solutions**:
1. Run with `--execute` to allow maestro write operations
2. Run with `--allow-any-command` to disable safety (use with caution)
3. Add the command to `SAFE_COMMANDS` allowlist if it's genuinely safe

### Qwen Produces Invalid JSON

```
Failed to parse qwen output (no valid JSON with next_command or done)
```

**Cause**: Qwen didn't follow the stream-json protocol.

**Solutions**:
1. Check `-vv` output to see what qwen actually produced
2. Verify qwen version supports `-o stream-json`
3. Tune the qwen prompt (edit `build_initial_prompt()` in `run.py`)

### Postmortem Command Not Found

```
Error running postmortem: command not found: maestro
```

**Cause**: `--maestro-bin` path not correct for postmortem chaining.

**Solution**: Use full path to maestro:
```bash
--maestro-bin "python /full/path/to/maestro.py"
```

### Output Directory Permission Error

```
PermissionError: [Errno 13] Permission denied: '/path/to/docs/maestro/ux_eval'
```

**Cause**: No write permission to repo's docs/ directory.

**Fallback**: Runner will try these locations in order:
1. `<repo>/docs/maestro/ux_eval/`
2. `<repo>/ux_eval/`
3. `<cwd>/ux_eval/`
4. `/tmp/maestro_ux_eval/`

Check the summary output to see where artifacts were saved.

## Best Practices

### 1. Start with Safe Mode

Always run without `--execute` first to verify qwen behavior:

```bash
python tools/ux_qwen_loop/run.py \
    --maestro-bin "./maestro.py" \
    --repo-root ~/Dev/MyRepo \
    --goal "List all runbooks" \
    -v
```

Review the report, then re-run with `--execute` if needed.

### 2. Use Verbose Flags for Debugging

- `-v`: See step-by-step progress
- `-vv`: See exact prompts and qwen responses (bounded to 2000 chars)

### 3. Keep Goals Focused

Good goals:
- "List all available runbooks"
- "Create a runbook for building this repo"
- "Show details of track TRK-001"

Avoid vague goals:
- "Explore the tool" (no clear done condition)
- "Do everything" (too broad)

### 4. Review Recommendations Systematically

The report generates UX recommendations ranked by priority:
- **P0**: Critical friction (users likely to abandon)
- **P1**: High-impact improvements (major UX gains)
- **P2**: Medium-impact improvements (polish)

Start with P0, verify with real users, iterate.

### 5. Compare Across Iterations

Re-run the same goal after UX improvements to measure impact:

```bash
# Before fixes
python tools/ux_qwen_loop/run.py ... --goal "Create a runbook" > before.txt

# After fixes
python tools/ux_qwen_loop/run.py ... --goal "Create a runbook" > after.txt

# Compare step counts
grep "Total steps:" before.txt after.txt
```

Lower step count = UX improvement validated.

## Limitations

1. **Qwen Dependency**: Requires qwen CLI installed and accessible
2. **Not a Replacement for User Testing**: This simulates exploration, but real users have different mental models
3. **Prompt Sensitivity**: Results depend on qwen prompt quality and model version
4. **Bounded Output**: Commands with huge output (>2000 chars) are truncated
5. **No Interactive Commands**: Cannot handle commands that require stdin (e.g., interactive prompts)
6. **Single Goal Focus**: Each run tests one goal in isolation

## Advanced Usage

### Custom Qwen Binary

Use a different qwen installation:

```bash
python tools/ux_qwen_loop/run.py \
    --qwen-bin "/custom/path/to/qwen" \
    ...
```

### Custom Step Limits

For complex goals, increase max steps:

```bash
python tools/ux_qwen_loop/run.py \
    --max-steps 50 \
    ...
```

For quick tests, decrease:

```bash
python tools/ux_qwen_loop/run.py \
    --max-steps 10 \
    ...
```

### Custom Timeouts

For slow commands or slow systems:

```bash
python tools/ux_qwen_loop/run.py \
    --timeout-help-s 15 \
    --timeout-cmd-s 120 \
    ...
```

## Development

### Running Tests

All tests are deterministic and don't require qwen:

```bash
cd /path/to/Maestro
pytest tests/test_ux_qwen_loop_runner.py -v
```

Tests use stub scripts in `tests/fixtures/`:
- `stub_qwen.py`: Deterministic qwen responses
- `stub_maestro.py`: Canned maestro outputs

### Adding New Stuck Detectors

Edit `tools/ux_qwen_loop/stuck.py` and add a new check in `StuckDetector.update()`:

```python
def update(self, step_event: Dict[str, Any]) -> Optional[str]:
    # ... existing checks ...

    # New check: detect if user is trying same thing with slight variations
    if self._is_command_variant_spam(normalized_cmd):
        return 'command_variant_spam: trying similar commands repeatedly'

    return None
```

### Adding New UX Recommendations

Edit `tools/ux_qwen_loop/export.py` and add pattern matching in `extract_ux_recommendations()`:

```python
# Recommendation N: New pattern
if some_pattern_detected:
    recommendations.append({
        'title': 'Clear title',
        'priority': 'P1',
        'evidence': 'What triggered this',
        'change': 'Specific improvement',
        'impact': 'How it helps users'
    })
```

## See Also

- [UX_BLINDFOLD_QWEN.md](./UX_BLINDFOLD_QWEN.md) - Single-shot planning harness
- [UX Postmortem](./SIGNATURES.md#ux-postmortem) - Convert evaluation artifacts into issues/workgraphs
- [INVARIANTS.md](./INVARIANTS.md) - UX evaluation invariants and quality gates
