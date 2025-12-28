# EX-32: Log Scan → Issue → Task → Work (Observability Pipeline)

**Scope**: Scan build/run logs, create issues with stable fingerprints, link to tasks, enforce work gates
**Outcome**: Build errors block work until addressed; pipeline is deterministic and idempotent

---

## Preconditions

- Repo initialized with `maestro init`
- Test fixture exists: `tests/fixtures/logs/build_error.log`
- JSON-based storage under `docs/maestro/`

## Gates / IDs / Stores

- Gates: `BLOCKED_BY_ISSUES`
- IDs: `<SCAN_ID>`, `ISSUE-001`, `ISSUE-002`
- Stores: `docs/maestro/log_scans/`, `docs/maestro/issues/`, `docs/phases/`

---

## Runbook Steps

| Step | Command | Intent | Expected | Gates | Stores |
|------|---------|--------|----------|-------|--------|
| 1 | `maestro log scan --source tests/fixtures/logs/build_error.log --kind build` | Scan build log for errors | Scan created with findings | - | `docs/maestro/log_scans/` |
| 2 | `maestro log list` | List all scans | Shows created scan | - | `docs/maestro/log_scans/` |
| 3 | `maestro log show <SCAN_ID>` | Show scan details | Displays findings with fingerprints | - | `docs/maestro/log_scans/` |
| 4 | `maestro issues add --from-log <SCAN_ID>` | Ingest findings into issues | Creates ISSUE-001, ISSUE-002 (deduped by fingerprint) | - | `docs/maestro/issues/` |
| 5 | `maestro issues list --severity blocker --status open` | List blocker issues | Shows created issues | - | `docs/maestro/issues/` |
| 6 | `maestro work task <TASK_ID>` | Attempt to start work | **BLOCKED** by gate | `BLOCKED_BY_ISSUES` | `docs/maestro/issues/` |
| 7 | `maestro issues triage --auto` | Auto-triage issues | Assigns severity, suggests actions | - | `docs/maestro/issues/` |
| 8 | `maestro issues link-task ISSUE-001 TASK-123` | Link issue to task | Bidirectional link created | - | `docs/maestro/issues/`, `docs/phases/` |
| 9 | `maestro work task <TASK_ID>` | Start work with linked task | Gate cleared (or downgraded to warning) | - | `docs/maestro/issues/` |
| 10 | `maestro issues resolve ISSUE-001 --reason "Fixed in commit abc123"` | Resolve issue | Issue marked as resolved | - | `docs/maestro/issues/` |
| 11 | `maestro work task <TASK_ID> --ignore-gates` | Override gate | Work starts despite blockers | - | - |

---

## AI Perspective (Heuristic)

- Same log scanned twice produces same fingerprints → deduplication works
- Fingerprints are stable across environments (normalized paths, timestamps)
- Blocker issues must be addressed before work starts (enforced by gates)
- Gate override is available but should be used sparingly
- Link issues to tasks to show progress and clear gates

---

## Outcomes

### Outcome A: Happy Path (Blocker Linked to Task)

- Build log scanned → findings extracted
- Issues created with stable fingerprints
- Issue linked to task → gate cleared
- Work proceeds normally

### Outcome B: Gate Blocks Work

- Blocker issue exists without linked task
- `maestro work` command exits with error code 1
- Clear actionable message shows:
  - Which issues are blocking
  - Commands to triage/link/resolve
  - Override option (`--ignore-gates`)

### Outcome C: Idempotent Ingestion

- Same log scanned twice creates single scan but updates existing issue
- Fingerprint deduplication prevents duplicate issues
- `last_seen` and `occurrences` updated on re-ingestion

---

## CLI Gaps / TODOs

- None (all commands implemented)

---

## Trace (YAML)

```yaml
trace:
  example: EX-32
  steps:
    - step: scan_build_log
      command: "maestro log scan --source tests/fixtures/logs/build_error.log --kind build"
      gates: []
      stores: [LOG_SCANS]
    - step: list_scans
      command: "maestro log list"
      gates: []
      stores: [LOG_SCANS]
    - step: show_scan
      command: "maestro log show <SCAN_ID>"
      gates: []
      stores: [LOG_SCANS]
    - step: ingest_findings
      command: "maestro issues add --from-log <SCAN_ID>"
      gates: []
      stores: [ISSUES]
    - step: list_blockers
      command: "maestro issues list --severity blocker --status open"
      gates: []
      stores: [ISSUES]
    - step: work_blocked
      command: "maestro work task <TASK_ID>"
      gates: [BLOCKED_BY_ISSUES]
      stores: [ISSUES]
    - step: triage_issues
      command: "maestro issues triage --auto"
      gates: []
      stores: [ISSUES]
    - step: link_issue_task
      command: "maestro issues link-task ISSUE-001 TASK-123"
      gates: []
      stores: [ISSUES, TASKS]
    - step: work_proceed
      command: "maestro work task <TASK_ID>"
      gates: []
      stores: [ISSUES]
    - step: resolve_issue
      command: "maestro issues resolve ISSUE-001 --reason 'Fixed in commit abc123'"
      gates: []
      stores: [ISSUES]
    - step: override_gate
      command: "maestro work task <TASK_ID> --ignore-gates"
      gates: []
      stores: []
  stores_considered:
    - LOG_SCANS
    - ISSUES
    - TASKS
cli_gaps: []
```

---

## Example Session Output

```console
$ maestro log scan --source tests/fixtures/logs/build_error.log --kind build
Scan created: 20250128_120000_build

$ maestro issues add --from-log 20250128_120000_build
Ingesting findings from scan: 20250128_120000_build
  Created ISSUE-001: 'bar' was not declared in this scope
  Created ISSUE-002: undefined reference to 'initialize()'
  Created ISSUE-003: expected ';' before '}' token

Summary:
  Created: 3 issues
  Updated: 0 issues

$ maestro issues list --severity blocker --status open
ISSUE-001  blocker  open  'bar' was not declared in this scope
ISSUE-002  blocker  open  undefined reference to 'initialize()'
ISSUE-003  blocker  open  expected ';' before '}' token

$ maestro work task TASK-123
╔══════════════════════════════════════════════════════════════════════════╗
║ GATE: BLOCKED_BY_ISSUES                                                  ║
╚══════════════════════════════════════════════════════════════════════════╝

The following blocker issues must be addressed before work can proceed:

  ISSUE-001: 'bar' was not declared in this scope
    Severity: blocker
    First seen: 2025-01-28T12:00:00
    Last seen: 2025-01-28T12:00:00
    Occurrences: 1

  ISSUE-002: undefined reference to 'initialize()'
    Severity: blocker
    First seen: 2025-01-28T12:00:00
    Last seen: 2025-01-28T12:00:00
    Occurrences: 1

  ISSUE-003: expected ';' before '}' token
    Severity: blocker
    First seen: 2025-01-28T12:00:00
    Last seen: 2025-01-28T12:00:00
    Occurrences: 1

Recommended actions:
  1. Triage and link issues to tasks:
     maestro issues link-task ISSUE-001 TASK-XXX
     maestro issues link-task ISSUE-002 TASK-XXX
     maestro issues link-task ISSUE-003 TASK-XXX

  2. Or mark as resolved if already fixed:
     maestro issues resolve ISSUE-001 --reason "Fixed in commit abc123"

  3. Or bypass gates (use with caution):
     maestro work --ignore-gates

For more details:
  maestro issues list --severity blocker --status open
  maestro issues show ISSUE-001

$ maestro issues link-task ISSUE-001 TASK-123
Linked ISSUE-001 to TASK-123

$ maestro work task TASK-123
# Work proceeds normally (gate cleared or downgraded)
```

---

## Determinism Verification

To verify fingerprint stability:

```bash
# Scan same log twice
maestro log scan --source tests/fixtures/logs/build_error.log --kind build
SCAN1=$(maestro log list | grep build | head -1 | awk '{print $1}')

maestro log scan --source tests/fixtures/logs/build_error.log --kind build
SCAN2=$(maestro log list | grep build | head -1 | awk '{print $1}')

# Show both scans
maestro log show $SCAN1 > /tmp/scan1.txt
maestro log show $SCAN2 > /tmp/scan2.txt

# Compare fingerprints (should be identical)
diff <(grep fingerprint /tmp/scan1.txt | sort) <(grep fingerprint /tmp/scan2.txt | sort)
# Expected: no diff
```
