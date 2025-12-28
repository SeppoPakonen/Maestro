# Observability Pipeline Design

## Overview

The Maestro observability pipeline transforms build/run failures and warnings into actionable work items with automatic prioritization. This ensures critical issues (e.g., build breaks) block progress until resolved or explicitly overridden.

**Pipeline Flow:**

```
Log Output → Scan → Findings → Issues → Tasks → Work Prioritization
```

## Stage 1: Log Scan

**Command:** `maestro log scan [--source <PATH>] [--last-run] [--kind {build|run|any}]`

**Purpose:** Capture and analyze build/run output or log files.

**Storage:** `docs/maestro/log_scans/<SCAN_ID>/`
- `meta.json` — scan metadata (timestamp, source path, command context, cwd)
- `raw.txt` — raw log snapshot (copied for immutability)
- `findings.json` — extracted findings with stable fingerprints

**Scan ID:** Timestamp-based unique identifier (e.g., `20250101_120030_build`)

**Output:** Structured findings with:
- `kind` — finding type (error, warning, info, crash)
- `severity` — initial severity assessment (blocker, critical, warning, info)
- `fingerprint` — stable hash for deduplication
- `message` — normalized error message
- `file`, `line` — source location (if available)
- `tool` — originating tool (gcc, clang, pytest, etc.)

### Fingerprint Generation

**Goal:** Same error → same fingerprint → same issue (deduplication across scans)

**Algorithm:**
1. Normalize message:
   - Remove absolute paths → relative paths or basenames
   - Collapse line-specific numbers if too noisy (configurable)
   - Strip timestamps, PIDs, thread IDs
   - Normalize whitespace
2. Construct fingerprint components:
   - Required: normalized message
   - Optional: tool name (gcc, clang, pytest)
   - Optional: file basename (not full path)
3. Hash: `sha256(message + tool + file_basename)`

**Example:**
```
Original: /home/user/project/src/foo.cpp:42: error: undefined reference to 'bar()'
Normalized: src/foo.cpp:42: error: undefined reference to 'bar()'
Components: message="undefined reference to 'bar()'", tool="gcc", file="foo.cpp"
Fingerprint: sha256("undefined reference to 'bar()' | gcc | foo.cpp")
```

## Stage 2: Findings → Issues

**Command:** `maestro issues add --from-log <SCAN_ID|PATH>`

**Purpose:** Ingest findings from scans into persistent issues with deduplication.

**Storage:** `docs/maestro/issues/<ISSUE_ID>.json`

**Issue Structure:**
```json
{
  "issue_id": "ISSUE-001",
  "fingerprint": "abc123...",
  "severity": "blocker",
  "status": "open",
  "message": "undefined reference to 'bar()'",
  "first_seen": "2025-01-01T12:00:30Z",
  "last_seen": "2025-01-01T14:30:00Z",
  "occurrences": [
    {"scan_id": "20250101_120030_build", "timestamp": "2025-01-01T12:00:30Z"},
    {"scan_id": "20250101_143000_build", "timestamp": "2025-01-01T14:30:00Z"}
  ],
  "linked_tasks": ["TASK-042"],
  "tool": "gcc",
  "file": "src/foo.cpp",
  "line": 42
}
```

**Deduplication Logic:**
- Check if issue with same fingerprint exists
- If exists → update `last_seen`, append occurrence, keep existing issue_id
- If new → create new issue with next available issue_id

## Stage 3: Triage and Task Linking

**Command:** `maestro issues triage [--auto] [--severity-first]`

**Purpose:** Assign severity, prioritize, and optionally propose/create tasks.

**Severity Levels:**
- **blocker** — Build breaks, crashes, critical failures (gates work)
- **critical** — Serious bugs, data corruption, security issues
- **warning** — Non-critical issues, code quality, deprecations
- **info** — Informational messages, performance hints

**Auto-triage Rules:**
- Build errors → blocker
- Runtime crashes → critical
- Compiler warnings → warning
- Linter messages → info

**Task Proposal:**
- If blocker issue has no linked task → propose task creation
- Task title: "Fix: {issue message}"
- Task priority: high (derived from severity)
- Auto-queue option: create task immediately with `--auto-create-tasks`

**Command:** `maestro issues link-task <ISSUE_ID> <TASK_ID>`

**Purpose:** Bidirectional linking between issues and tasks.

**Storage:**
- Issue: `linked_tasks: ["TASK-042"]`
- Task: `linked_issues: ["ISSUE-001"]` (stored in task JSON)

## Stage 4: Work Gates and Prioritization

**Gate:** `BLOCKED_BY_BUILD_ERRORS`

**Trigger Condition:**
- At least one blocker severity issue exists
- Issue status is `open` (not `resolved` or `ignored`)
- No linked task is currently `in_progress`

**Work Start Behavior:**
```bash
$ maestro work start task TASK-100
Error: Work is blocked by active gates:
  - BLOCKED_BY_BUILD_ERRORS (2 blocker issues)

Active blocker issues:
  - ISSUE-001: undefined reference to 'bar()' (last seen: 2 minutes ago)
  - ISSUE-005: segmentation fault in foo.cpp:42 (last seen: 5 minutes ago)

Options:
  1. Fix blocker issues first
  2. Link a task to blockers: maestro issues link-task ISSUE-001 TASK-100
  3. Override gate: maestro work start task TASK-100 --override gate:BLOCKED_BY_BUILD_ERRORS
  4. Ignore all gates: maestro work start task TASK-100 --ignore-gates
```

**Gate Status Command:**
```bash
$ maestro work gate status
Active Gates:
  ✗ BLOCKED_BY_BUILD_ERRORS (2 blocker issues, no in-progress linked tasks)

Blockers:
  - ISSUE-001: undefined reference to 'bar()' [no linked task]
  - ISSUE-005: segmentation fault in foo.cpp:42 [linked to TASK-042: pending]

Recommendations:
  - Start task TASK-042 to address ISSUE-005
  - Create task for ISSUE-001 or link to existing task
```

**Task Prioritization:**
- Blocker-linked tasks are surfaced first in `maestro work` queue
- Within priority levels, blocker-linked tasks have precedence
- Use `--ignore-priority` to override automatic prioritization

## Stage 5: Issue Resolution

**Resolve Command:** `maestro issues resolve <ISSUE_ID> [--reason <REASON>]`
- Mark issue as resolved (status: `resolved`)
- Issue no longer gates work
- Keep in history for analytics

**Ignore Command:** `maestro issues ignore <ISSUE_ID> [--reason <REASON>]`
- Mark issue as ignored (status: `ignored`)
- Issue no longer gates work
- Useful for false positives or accepted technical debt

**Re-occurrence:**
- If resolved/ignored issue fingerprint appears in new scan → status reverts to `open`
- Notification: "ISSUE-001 has re-occurred (was resolved 3 days ago)"

## Data Flow Example

**Scenario:** Build fails with linker error

1. **Scan:**
   ```bash
   $ maestro make 2>&1 | tee build.log
   [build fails]
   $ maestro log scan --source build.log --kind build
   Scan created: 20250101_120030_build
   Found 3 findings: 1 error, 2 warnings
   ```

2. **Ingest:**
   ```bash
   $ maestro issues add --from-log 20250101_120030_build
   Created ISSUE-001 (blocker): undefined reference to 'bar()'
   Updated ISSUE-003 (warning): unused variable 'x' (occurrence count: 5)
   Created ISSUE-004 (warning): implicit conversion from int to float
   ```

3. **Triage:**
   ```bash
   $ maestro issues triage --auto
   ISSUE-001 severity: blocker (build error)
   No linked task found. Recommend: maestro task add "Fix linker error in foo.cpp"
   ```

4. **Work Gate:**
   ```bash
   $ maestro work start task TASK-050
   Error: BLOCKED_BY_BUILD_ERRORS (1 blocker issue)

   $ maestro issues link-task ISSUE-001 TASK-042
   Linked ISSUE-001 to TASK-042

   $ maestro work start task TASK-042
   Starting work on TASK-042 (priority: high, blocker-linked)
   Work session: WORK-2025-001
   ```

5. **Resolve:**
   ```bash
   [fix implemented]
   $ maestro make
   [build succeeds]

   $ maestro issues resolve ISSUE-001 --reason "Fixed missing symbol definition"
   ISSUE-001 marked as resolved

   $ maestro work gate status
   No active gates. All clear to proceed.
   ```

## Storage Layout

```
docs/maestro/
├── log_scans/
│   ├── 20250101_120030_build/
│   │   ├── meta.json
│   │   ├── raw.txt
│   │   └── findings.json
│   └── 20250101_143000_build/
│       ├── meta.json
│       ├── raw.txt
│       └── findings.json
├── issues/
│   ├── ISSUE-001.json
│   ├── ISSUE-002.json
│   └── index.json  (optional: fingerprint → issue_id lookup)
└── tasks/
    ├── TASK-042.json  (contains linked_issues)
    └── ...
```

## Design Principles

1. **Determinism:** Same input → same fingerprint → same issue
2. **Immutability:** Scans are append-only; never modified after creation
3. **Idempotency:** Same log ingested twice → no duplicate issues
4. **Traceability:** Full audit trail from finding → issue → task → work
5. **Fail-safe:** Blocker issues must be explicitly acknowledged or overridden
6. **Minimalism:** Start with build errors; extend to runtime, tests, linters

## Future Extensions

- Auto-scan on build completion (hook into `maestro make`)
- Real-time log streaming and immediate finding extraction
- Issue patterns and root cause clustering
- Integration with external issue trackers (GitHub Issues, Jira)
- ML-based severity prediction and duplicate detection
- Historical analytics and trend reporting
