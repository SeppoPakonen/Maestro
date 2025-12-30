# EX-36: Ops Doctor + Run (Thin Slice)

**Scope**: Operations automation thin slice
**Tags**: ops, doctor, run, automation, health-check
**Status**: proposed
**Sprint**: P2 Sprint 4.7

## Goal

Demonstrate `maestro ops doctor` and `maestro ops run` commands for deterministic health checks and runbook execution.

## Context

This runbook showcases the operations automation layer introduced in P2 Sprint 4.7:

1. **`maestro ops doctor`** - Health scan that checks gates/blockers and suggests remediation
2. **`maestro ops run`** - Deterministic runbook executor (YAML-based, no AI, no arbitrary shell)

These commands enable:
- Pre-flight checks before work sessions
- Automated verification pipelines
- Reproducible multi-step workflows
- CI/CD integration points

## Prerequisites

- Repository initialized (`maestro init`)
- Git repository (for dirty tree checks)

## Steps

### 1. Run ops doctor (health check)

```bash
maestro ops doctor
```

**Expected**:
- Checks 6 health gates:
  - Repo lock status (stale/active)
  - Git status (dirty tree, detached HEAD, branch mismatch)
  - Repo truth readiness (model.json exists and valid)
  - Repo conf readiness (conf.json with targets)
  - Blocker issues (open blockers without linked in-progress tasks)
- Text output with recommended commands
- Exit code:
  - `0` = all OK or warnings only
  - `2` = fatal findings (blockers/errors)

**Stores**: None (read-only diagnostic)

**Gates**: None (diagnostic command)

---

### 2. Run ops doctor with JSON output

```bash
maestro ops doctor --format json
```

**Expected**:
- Same checks as above
- JSON-formatted output with findings array
- Each finding includes:
  - `id`, `severity`, `message`, `details`, `recommended_commands`
- Summary with counts (ok, warnings, errors, blockers)

**Stores**: None

**Gates**: None

---

### 3. Run ops doctor in strict mode

```bash
maestro ops doctor --strict
```

**Expected**:
- Warnings treated as errors
- Exit code `2` if any warnings present
- Useful for CI/CD pipelines requiring strict validation

**Stores**: None

**Gates**: None

---

### 4. Create an ops plan (YAML)

```bash
cat > /tmp/example_plan.yaml <<'EOF'
kind: ops_run
name: Example pipeline
steps:
  - maestro: "ops doctor --format json"
  - maestro: "ops list"
EOF
```

**Expected**:
- Valid ops plan YAML created

**Stores**: `/tmp/example_plan.yaml`

**Gates**: None

---

### 5. Run ops plan in dry-run mode

```bash
maestro ops run /tmp/example_plan.yaml --dry-run
```

**Expected**:
- Shows what would be executed without running
- Creates run record with `dry_run: true`
- All steps logged but not executed
- Run ID displayed (format: `YYYYMMDD_HHMMSS_ops_run_<hash>`)

**Stores**:
- `docs/maestro/ops/runs/<RUN_ID>/meta.json`
- `docs/maestro/ops/runs/<RUN_ID>/steps.jsonl`
- `docs/maestro/ops/runs/<RUN_ID>/summary.json`
- `docs/maestro/ops/index.json` (updated)

**Gates**: None (dry-run mode)

---

### 6. Run ops plan for real

```bash
maestro ops run /tmp/example_plan.yaml
```

**Expected**:
- Executes each step sequentially
- Captures stdout/stderr per step
- Creates full run record
- Stops on first failure (unless `--continue-on-error`)
- Exit codes:
  - `0` = all steps succeeded
  - `1` = one or more steps failed (continue-on-error mode)
  - `2` = stopped due to step failure
  - `3` = internal error (plan parsing, YAML invalid)

**Stores**:
- `docs/maestro/ops/runs/<RUN_ID>/meta.json`
- `docs/maestro/ops/runs/<RUN_ID>/steps.jsonl`
- `docs/maestro/ops/runs/<RUN_ID>/stdout.txt`
- `docs/maestro/ops/runs/<RUN_ID>/stderr.txt`
- `docs/maestro/ops/runs/<RUN_ID>/summary.json`
- `docs/maestro/ops/index.json` (updated)

**Gates**: None (respects individual step gates)

---

### 7. List ops runs

```bash
maestro ops list
```

**Expected**:
- Shows all ops runs (newest first)
- Displays: run_id, plan_name, started_at, exit_code
- Indicates success/failure with checkmark/X

**Stores**: None

**Gates**: None

---

### 8. Show ops run details

```bash
# Get run ID from ops list
RUN_ID=$(maestro ops list | grep "ops_run_" | head -1 | awk '{print $2}')

maestro ops show "$RUN_ID"
```

**Expected**:
- Shows full run details:
  - Meta (run_id, plan_name, timestamps, dry_run flag)
  - Summary (total/successful/failed steps, duration)
  - Step-by-step breakdown (command, exit code, duration)

**Stores**: None

**Gates**: None

---

### 9. Inspect run record files

```bash
ls -lh docs/maestro/ops/runs/
ls -lh docs/maestro/ops/runs/"$RUN_ID"/
cat docs/maestro/ops/runs/"$RUN_ID"/meta.json
cat docs/maestro/ops/runs/"$RUN_ID"/summary.json
```

**Expected**:
- All run record files exist
- JSON files are valid and human-readable
- stdout.txt and stderr.txt contain step outputs

**Stores**: None (read-only inspection)

**Gates**: None

---

## Validation

After completing all steps:

1. **Doctor checks ran** without errors
2. **Ops run executed** successfully (dry-run and real)
3. **Run records created** under `docs/maestro/ops/runs/`
4. **Index updated** at `docs/maestro/ops/index.json`
5. **List/show commands** work correctly

## Notes

- Ops plans only allow `maestro:` commands (no arbitrary shell for security)
- Run records are deterministic and reproducible
- Dry-run mode useful for testing and CI verification
- Doctor checks respect `MAESTRO_DOCS_ROOT` for testing in isolated environments

## See Also

- `docs/workflows/v3/cli/SIGNATURES.md` - Ops command signatures
- `docs/workflows/v3/cli/OPS_RUN_FORMAT.md` - Ops plan YAML format specification
- `docs/workflows/v3/cli/TREE.md` - CLI command tree
