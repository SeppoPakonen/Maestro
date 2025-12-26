# EX-07: `maestro work` ↔ `maestro wsession` — Cookie, Breadcrumbs, IPC Mailbox, Multi-Process

**Scope**: Work session IPC mechanics
**Build System**: N/A (session management)
**Languages**: N/A (conceptual)
**Outcome**: Document how work sessions use file-based IPC with cookies for AI-to-Maestro communication, allowing multi-process workflows and resume

---

## Scenario Summary

Developer starts a work session on a task using `maestro work task task-001`. Maestro creates a session cookie and provides it to the AI in the system prompt. During the work session, AI makes progress and calls `maestro wsession breadcrumb` with the cookie to update progress. User can close and resume the session later. All state is file-based IPC in `$HOME/.maestro/ipc/<session-id>/`.

This demonstrates **file-based IPC for AI↔Maestro communication** without requiring AI to mutate repo truth directly.

---

## Preconditions

- Maestro initialized (`./docs/maestro/**` exists)
- At least one task exists (e.g., `task-001`)
- AI engine available

---

## Work Session Architecture

### File-Based IPC Mailbox

**Location**: `$HOME/.maestro/ipc/<session-id>/`

**Files**:
```
$HOME/.maestro/ipc/<session-id>/
├── cookie              # Session cookie (secret token)
├── breadcrumbs.json    # Progress updates from AI
├── context.json        # Task/phase/track context snapshot
└── mutations.log       # Optional: log of repo truth mutations (if enabled)
```

### Session Lifecycle

1. **Create**: `maestro work task task-001` → generates session ID and cookie
2. **Active**: AI uses cookie to append breadcrumbs
3. **Resume**: `maestro work --resume <session-id>` → reload context, continue
4. **Close**: Explicit close or timeout → archive session

---

## Runbook Steps

### Step 1: Start Work Session

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro work task task-001` | Start AI-assisted work on task | Work session created, AI context loaded |

**Internal**:
- Generate session ID: `ws-<timestamp>-<random>`
- Create IPC mailbox: `$HOME/.maestro/ipc/ws-20250126-abc123/`
- Generate cookie: `cookie-<random-hex>` (e.g., `cookie-7f3a9b2e`)
- Write cookie file: `$HOME/.maestro/ipc/ws-20250126-abc123/cookie`
- Load task context (task, phase, track, workflow, runbook)
- Write context snapshot: `$HOME/.maestro/ipc/ws-20250126-abc123/context.json`
- Include cookie in AI system prompt

**Gates**: REPOCONF_GATE
**Stores write**: IPC_MAILBOX, REPO_TRUTH_DOCS_MAESTRO (marks task in_progress)
**Stores read**: REPO_TRUTH_DOCS_MAESTRO

### Step 2: AI Receives Cookie in Prompt

**System Prompt (excerpt)**:
```
You are helping with task-001: "Implement login endpoint"

Context:
- Phase: phase-001 "P1: Core Features"
- Track: track-001 "Sprint 1"
- Workflow: workflow-001 (if linked)

Work Session:
- Session ID: ws-20250126-abc123
- Cookie: cookie-7f3a9b2e

You may update progress by calling:
maestro wsession breadcrumb ws-20250126-abc123 --cookie cookie-7f3a9b2e --status "Your progress message"
```

### Step 3: AI Makes Progress and Updates Breadcrumbs

| AI Action | Intent | Expected |
|-----------|--------|----------|
| `maestro wsession breadcrumb ws-20250126-abc123 --cookie cookie-7f3a9b2e --status "Analyzing codebase..."` | Report progress | Breadcrumb appended to IPC mailbox |

**Internal**:
- Validate cookie matches session
- Append breadcrumb to `$HOME/.maestro/ipc/ws-20250126-abc123/breadcrumbs.json`:
  ```json
  {
    "timestamp": "2025-01-26T14:32:01Z",
    "status": "Analyzing codebase...",
    "metadata": {}
  }
  ```

**Gates**: (cookie validation only)
**Stores write**: IPC_MAILBOX

### Step 4: AI Continues, Adds More Breadcrumbs

| AI Action | Intent | Expected |
|-----------|--------|----------|
| `maestro wsession breadcrumb ws-20250126-abc123 --cookie cookie-7f3a9b2e --status "Implementing password hashing..."` | Update progress | Another breadcrumb appended |

**Breadcrumbs accumulate in `breadcrumbs.json`** (array of progress updates).

### Step 5: User Checks Progress (Optional)

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro wsession show ws-20250126-abc123` | View session breadcrumbs | Displays all breadcrumbs |

**Output**:
```
Work Session: ws-20250126-abc123
Task: task-001 "Implement login endpoint"

Breadcrumbs:
  [14:32:01] Analyzing codebase...
  [14:35:12] Implementing password hashing...
```

### Step 6: User Closes Session

| Command | Intent | Expected |
|---------|--------|----------|
| AI session ends (user types `/done` or exits) | Finalize session | Session state preserved |

**Internal**:
- Session remains in IPC mailbox for resume
- Cookie still valid for future appends

### Step 7: Resume Session Later

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro work --resume ws-20250126-abc123` | Continue previous work session | AI context restored, breadcrumbs visible |

**Internal**:
- Load `context.json` and `breadcrumbs.json`
- Provide AI with full history
- Same cookie still valid

**Gates**: REPOCONF_GATE
**Stores read**: IPC_MAILBOX, REPO_TRUTH_DOCS_MAESTRO

---

## Cookie Validation Mechanism

**Conceptual function**: `validate_cookie(session_id, provided_cookie)`

**Steps**:
1. Read expected cookie from `$HOME/.maestro/ipc/<session-id>/cookie`
2. Compare with `provided_cookie`
3. If match: allow breadcrumb append
4. If mismatch: reject with error "Invalid cookie for session"

**Purpose**: Prevent unauthorized breadcrumb writes from random processes.

---

## IPC Mailbox Polling (Conceptual)

**Use case**: External tools or UI monitors can poll IPC mailbox to display live progress.

**Conceptual function**: `poll_breadcrumbs(session_id, last_timestamp=None)`

**Steps**:
1. Read `$HOME/.maestro/ipc/<session-id>/breadcrumbs.json`
2. Filter breadcrumbs newer than `last_timestamp`
3. Return new breadcrumbs

**Example**: Web UI polls every 2 seconds, displays latest AI status.

---

## Optional: Mutation Mode (Advanced)

**Concept**: By default, AI cannot mutate repo truth during work session. But **mutation mode** (opt-in) allows AI to directly write to `./docs/maestro/**`.

**Flag** (hypothetical): `maestro work task task-001 --allow-mutations`

**Behavior**:
- AI can call: `maestro task update task-001 --status completed`
- Changes written to `./docs/maestro/tasks/task-001.json`
- Logged in `mutations.log`

**Risk**: AI can corrupt repo truth if buggy. Default is **no mutations**, only breadcrumbs.

---

## AI Perspective (Heuristic)

**What AI notices**:
- Work session cookie in system prompt → use it for breadcrumb updates
- Cookie is required → breadcrumb calls without cookie will fail
- Session can span multiple invocations → resume preserves context

**What AI tries**:
- Call `maestro wsession breadcrumb` periodically to report progress
- Include meaningful status messages (not just "working...")
- If cookie missing or wrong: retry or ask user

**Where AI tends to hallucinate**:
- May forget to include `--cookie` flag → breadcrumb rejected
- May assume breadcrumbs automatically update task status (they don't - that requires mutation mode or user action)
- May call `maestro wsession breadcrumb` with wrong session ID

---

## Outcomes

### Outcome A: Success — Breadcrumbs Accumulated, Session Resumed

**Flow**:
1. User starts work session: `maestro work task task-001`
2. AI receives cookie in prompt
3. AI makes progress, calls `maestro wsession breadcrumb` 5 times
4. User exits
5. Later: user runs `maestro work --resume ws-20250126-abc123`
6. AI context restored with all 5 breadcrumbs visible

**Artifacts**:
- IPC mailbox: `$HOME/.maestro/ipc/ws-20250126-abc123/`
- Breadcrumbs: 5 entries in `breadcrumbs.json`
- Cookie still valid

### Outcome B: Cookie Missing → Breadcrumb Rejected

**Flow**:
1. AI tries to call: `maestro wsession breadcrumb ws-20250126-abc123 --status "Progress..."`
2. Cookie flag missing
3. System rejects: "ERROR: Cookie required for breadcrumb update"
4. AI retries with `--cookie cookie-7f3a9b2e`
5. Breadcrumb accepted

### Outcome C: Cookie Mismatch → Unauthorized

**Flow**:
1. AI (or malicious process) calls: `maestro wsession breadcrumb ws-20250126-abc123 --cookie wrong-cookie --status "Hacked"`
2. System validates: expected `cookie-7f3a9b2e`, got `wrong-cookie`
3. Reject: "ERROR: Invalid cookie for session ws-20250126-abc123"
4. No breadcrumb written

### Outcome D: Stale Mailbox → User Resolves by Resuming

**Flow**:
1. Work session created yesterday, left idle
2. User forgot about it
3. Later: user runs `maestro work task task-001` again
4. System detects existing session: "Session ws-20250126-abc123 already active. Resume? (Y/n)"
5. User chooses to resume or create new session

---

## Multi-Process Allowed

**Key feature**: Work sessions are **file-based**, so multiple processes can interact with the same session mailbox.

**Example**:
- Process 1 (AI): Writes breadcrumbs via `maestro wsession breadcrumb`
- Process 2 (User CLI): Reads breadcrumbs via `maestro wsession show`
- Process 3 (Web UI): Polls `breadcrumbs.json` for live updates

**No locking required** for read-only operations. Append operations are safe (OS-level atomic file appends).

---

## CLI Gaps / TODOs

```yaml
cli_gaps:
  - "TODO_CMD: maestro work task <task-id>"
  - "TODO_CMD: maestro work --resume <session-id>"
  - "TODO_CMD: maestro wsession breadcrumb <session> --cookie <cookie> --status <msg>"
  - "TODO_CMD: maestro wsession show <session>"
  - "TODO_CMD: maestro work task <id> --allow-mutations (mutation mode flag)"
  - "TODO_CMD: how session IDs are generated"
  - "TODO_CMD: cookie format and security properties"
```

---

## Trace Block (YAML)

```yaml
trace:
  - user: "maestro work task task-001"
    intent: "Start AI-assisted work session on task"
    gates: ["REPOCONF_GATE"]
    stores_write: ["IPC_MAILBOX", "REPO_TRUTH_DOCS_MAESTRO"]
    stores_read: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["generate_session_id", "generate_cookie", "create_ipc_mailbox"]
    cli_confidence: "low"  # TODO_CMD

  - ai: "maestro wsession breadcrumb ws-20250126-abc123 --cookie cookie-7f3a9b2e --status 'Analyzing codebase...'"
    intent: "AI reports progress via breadcrumb"
    gates: ["COOKIE_VALIDATION"]
    stores_write: ["IPC_MAILBOX"]
    internal: ["validate_cookie", "append_breadcrumb"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro work --resume ws-20250126-abc123"
    intent: "Resume previous work session"
    gates: ["REPOCONF_GATE"]
    stores_read: ["IPC_MAILBOX", "REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["load_session_context", "load_breadcrumbs"]
    cli_confidence: "low"  # TODO_CMD
```

---

**Related:** Work session IPC, file-based communication, cookie auth, multi-process safety
**Status:** Proposed
