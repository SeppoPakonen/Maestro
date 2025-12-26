# EX-19: Managed Mode — Resume AI Session Across Processes + Stacking with Sub-Work Sessions

**Scope**: Managed orchestration with session persistence and stacking discipline
**Build System**: N/A (orchestration mechanics)
**Languages**: N/A
**Outcome**: Demonstrate that in managed mode: (1) AI sessions persist across process restarts via resume tokens, (2) work sessions persist across multiple AI sessions, (3) stacking spawns subtasks with their own work-session and ai-session IDs (cookie discipline), (4) breadcrumb calls are validated with JSON contract gate

---

## Scenario Summary

Developer configures Maestro to use **managed AI stacking mode**. They start work on a parent task "Implement feature X". During the work session, the orchestrator spawns a subtask "Investigate Y" which requires its own AI session and work session. The parent AI process exits, but the work session persists. When the developer resumes, the AI session is restored using a resume token. The subtask completes and its results are summarized back into the parent work session via breadcrumb linking.

This demonstrates **managed mode orchestration with session continuity and stacking discipline**.

---

## Preconditions

- Maestro initialized in a repository
- AI stacking mode set to `managed` (not `handsoff`)
- At least one task exists for the parent work session
- Developer has access to AI engine with resume capability (e.g., Claude with conversation resume)

---

## Minimal Project Skeleton

```
my-project/
├── docs/
│   └── maestro/
│       ├── repo.json
│       ├── tasks/
│       │   ├── task-001.json (parent task: "Implement feature X")
│       │   └── task-002.json (spawned subtask: "Investigate Y", created during work session)
│       └── work_sessions/
│           ├── wsession-parent-abc123.json
│           └── wsession-subtask-def456.json
└── src/
    └── (code files)
```

**task-001.json** (parent task):
```json
{
  "id": "task-001",
  "title": "Implement feature X",
  "description": "Add new feature X to the application",
  "status": "in_progress",
  "created_at": "2025-01-26T09:00:00Z"
}
```

---

## Runbook Steps

### Step 1: Configure Managed Stacking Mode

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro settings set ai_stacking_mode managed` | Enable managed orchestration | Settings updated |

**System Output**:
```
[SETTINGS] Updated: ai_stacking_mode = managed
[SETTINGS] Managed mode enabled:
  - AI sessions persist via resume tokens
  - Work sessions persist across AI processes
  - Stacking spawns subtasks with session cookies
  - Breadcrumb calls validated with JSON contract
```

**Gates**: (none - settings change)
**Stores write**: (settings file, location TBD)

### Step 2: Start Parent Work Session

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro work task task-001` | Start work on parent task | AI session begins, work session created |

**Internal**:
- Generate `work_session_id` (cookie A): `wsession-parent-abc123`
- Generate `ai_session_id` (resume token R1): `ai-session-r1-xyz789`
- Create work session metadata file
- Launch AI with initial prompt including cookie A

**System Output**:
```
[WORK] Starting work session for task: task-001 (Implement feature X)
[WORK] Work session ID: wsession-parent-abc123
[WORK] AI session ID: ai-session-r1-xyz789
[WORK] Cookie: wsession-parent-abc123

AI: I'm starting work on task-001: Implement feature X.
    Let me first understand the current codebase structure.

    [AI reads files, explores code...]

    I notice this feature depends on understanding component Y.
    Would you like me to spawn a subtask to investigate Y first?

User: Yes, investigate Y.
```

**Gates**: REPOCONF_GATE (work session requires repo configuration)
**Stores write**: REPO_TRUTH_DOCS_MAESTRO (`work_sessions/wsession-parent-abc123.json`)
**Stores read**: REPO_TRUTH_DOCS_MAESTRO (`tasks/task-001.json`)

**Artifact** (`work_sessions/wsession-parent-abc123.json`):
```json
{
  "id": "wsession-parent-abc123",
  "task_id": "task-001",
  "ai_session_id": "ai-session-r1-xyz789",
  "status": "active",
  "created_at": "2025-01-26T10:00:00Z",
  "breadcrumbs": [],
  "subtasks": []
}
```

### Step 3: Spawn Subtask with Separate Session

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro work spawn --from-task task-001 --title "Investigate component Y"` | Create subtask and work session | Subtask created, new AI session spawned |

**Alternative** (if spawn is AI-initiated):
- AI calls internal orchestrator API to spawn subtask
- Orchestrator creates task-002, generates cookie B, launches new AI session

**Internal**:
- Create `task-002` with title "Investigate component Y"
- Link `task-002` to parent `task-001` (parent_task field)
- Generate `work_session_id` (cookie B): `wsession-subtask-def456`
- Generate `ai_session_id` (resume token R2): `ai-session-r2-uvw456`
- Launch new AI session with cookie B
- Update parent work session to record subtask link

**System Output**:
```
[WORK] Spawning subtask from task-001
[WORK] Created task: task-002 (Investigate component Y)
[WORK] Work session ID: wsession-subtask-def456
[WORK] AI session ID: ai-session-r2-uvw456
[WORK] Cookie: wsession-subtask-def456
[WORK] Parent work session: wsession-parent-abc123

--- NEW AI SESSION (R2) ---

AI (subtask): I'm working on subtask task-002: Investigate component Y.
              Cookie: wsession-subtask-def456

              [AI investigates component Y...]

              Component Y is a utility module that handles data validation.
              It has 3 main functions: validate(), sanitize(), transform().

              I'll record this finding as a breadcrumb.
```

**Gates**: (subtask creation requires parent work session active)
**Stores write**: REPO_TRUTH_DOCS_MAESTRO (`tasks/task-002.json`, `work_sessions/wsession-subtask-def456.json`)

**Artifact** (`tasks/task-002.json`):
```json
{
  "id": "task-002",
  "title": "Investigate component Y",
  "description": "Analyze component Y to understand its structure and API",
  "status": "in_progress",
  "parent_task": "task-001",
  "created_at": "2025-01-26T10:05:00Z"
}
```

**Artifact** (`work_sessions/wsession-subtask-def456.json`):
```json
{
  "id": "wsession-subtask-def456",
  "task_id": "task-002",
  "parent_wsession_id": "wsession-parent-abc123",
  "ai_session_id": "ai-session-r2-uvw456",
  "status": "active",
  "created_at": "2025-01-26T10:05:00Z",
  "breadcrumbs": []
}
```

### Step 4: Subtask AI Records Breadcrumb (with Cookie)

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro wsession breadcrumb add --cookie wsession-subtask-def456 --message "Found 3 main functions in component Y: validate, sanitize, transform"` | Record finding in work session | Breadcrumb added |

**Internal**:
- Validate cookie matches active work session (wsession-subtask-def456)
- Parse message (must be valid JSON or structured text)
- Append breadcrumb to work session metadata
- **JSON contract gate**: Validate breadcrumb structure

**System Output**:
```
[WSESSION] Breadcrumb added to wsession-subtask-def456
[WSESSION] Validation: Cookie matches active session ✓
[WSESSION] Validation: JSON contract satisfied ✓
[WSESSION] Breadcrumb ID: bc-001

Breadcrumb recorded:
  "Found 3 main functions in component Y: validate, sanitize, transform"
```

**Gates**: JSON_CONTRACT_GATE (breadcrumb must be valid structured data)
**Stores write**: REPO_TRUTH_DOCS_MAESTRO (`work_sessions/wsession-subtask-def456.json` updated)

**Artifact** (`work_sessions/wsession-subtask-def456.json` updated):
```json
{
  "id": "wsession-subtask-def456",
  "breadcrumbs": [
    {
      "id": "bc-001",
      "message": "Found 3 main functions in component Y: validate, sanitize, transform",
      "timestamp": "2025-01-26T10:08:00Z",
      "ai_session_id": "ai-session-r2-uvw456"
    }
  ]
}
```

### Step 5: Subtask Completes, AI Process Exits

| Command | Intent | Expected |
|---------|--------|----------|
| AI completes investigation, user ends session | Mark subtask complete, exit AI process | Work session persists |

**AI Output**:
```
AI (subtask): Investigation complete. Component Y provides data validation utilities.
              Marking task-002 as complete.

User: /done

[WORK SESSION] Task task-002 marked as completed.
[WORK SESSION] Updated: ./docs/maestro/tasks/task-002.json
[WORK SESSION] Work session wsession-subtask-def456 closed.
[WORK SESSION] Summary breadcrumb sent to parent: wsession-parent-abc123

--- AI SESSION R2 TERMINATED ---
```

**Gates**: (task completion always allowed)
**Stores write**: REPO_TRUTH_DOCS_MAESTRO (`tasks/task-002.json`, `work_sessions/wsession-subtask-def456.json`, `work_sessions/wsession-parent-abc123.json`)

**Artifact** (`work_sessions/wsession-parent-abc123.json` updated):
```json
{
  "id": "wsession-parent-abc123",
  "subtasks": [
    {
      "task_id": "task-002",
      "wsession_id": "wsession-subtask-def456",
      "status": "completed",
      "summary": "Investigated component Y: provides validate, sanitize, transform functions"
    }
  ]
}
```

### Step 6: Resume Parent Work Session (New Process)

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro work resume wsession-parent-abc123` | Restore parent work session | AI session resumed with previous context |

**Alternative** (engine-specific resume):
- Claude: `maestro work task task-001 --resume ai-session-r1-xyz789`
- Generic: orchestrator loads work session metadata and reconstructs prompt

**Internal**:
- Read `work_sessions/wsession-parent-abc123.json`
- Find `ai_session_id`: `ai-session-r1-xyz789`
- Resume AI session using engine-specific resume mechanism
- Include work session context in prompt:
  - Original task: task-001
  - Cookie: wsession-parent-abc123
  - Completed subtasks: task-002 (summary available)
  - Breadcrumbs from parent and subtasks

**System Output**:
```
[WORK] Resuming work session: wsession-parent-abc123
[WORK] Task: task-001 (Implement feature X)
[WORK] AI session: ai-session-r1-xyz789 (resuming...)
[WORK] Cookie: wsession-parent-abc123
[WORK] Subtasks completed: 1 (task-002)

--- AI SESSION R1 RESUMED ---

AI: Welcome back! I'm resuming work on task-001: Implement feature X.
    Cookie: wsession-parent-abc123

    I see that subtask task-002 (Investigate component Y) has been completed.
    Summary: Component Y provides validate, sanitize, transform functions.

    I can now proceed with implementing feature X using component Y.
    Shall I start writing the code?

User: Yes, proceed.
```

**Gates**: WORK_SESSION_EXISTS (resume requires valid work session ID)
**Stores read**: REPO_TRUTH_DOCS_MAESTRO (`work_sessions/wsession-parent-abc123.json`, `tasks/task-001.json`, `tasks/task-002.json`)

### Step 7: AI Attempts Breadcrumb with Wrong Cookie (Validation Failure)

| Command | Intent | Expected |
|---------|--------|----------|
| AI mistakenly uses wrong cookie in breadcrumb call | Breadcrumb rejected | AI reprompted with correct cookie |

**Scenario**: AI session R1 (parent) attempts to use cookie B (subtask) by mistake

**AI Call (incorrect)**:
```
maestro wsession breadcrumb add --cookie wsession-subtask-def456 --message "Implemented feature X"
```

**System Output**:
```
[WSESSION] ERROR: Cookie mismatch
[WSESSION] Expected cookie: wsession-parent-abc123 (active session)
[WSESSION] Received cookie: wsession-subtask-def456 (inactive/completed session)
[WSESSION] Breadcrumb rejected.

Error: Invalid cookie. Use correct work session cookie for current session.
```

**AI Response (after error)**:
```
AI: I apologize for the error. Let me use the correct cookie.

    [Retries with correct cookie...]

    maestro wsession breadcrumb add --cookie wsession-parent-abc123 --message "Implemented feature X using component Y"

[WSESSION] Breadcrumb added to wsession-parent-abc123 ✓
```

**Gates**: JSON_CONTRACT_GATE (cookie validation)
**Stores write**: (none - first call rejected, second call writes breadcrumb)

---

## Alternative Path: Resume with Stale AI Session ID

### Step 6b: AI Session No Longer Available (Resume Fails)

**Scenario**: User tries to resume, but AI session R1 expired (e.g., Claude conversation deleted)

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro work resume wsession-parent-abc123` | Restore work session | Resume fails, new AI session created |

**System Output**:
```
[WORK] Resuming work session: wsession-parent-abc123
[WORK] AI session: ai-session-r1-xyz789
[WORK] Attempting resume... FAILED
[WORK] Error: AI session ai-session-r1-xyz789 no longer available (expired or deleted)

[WORK] Fallback: Creating new AI session for work session
[WORK] New AI session ID: ai-session-r3-new123
[WORK] Cookie: wsession-parent-abc123 (unchanged)
[WORK] Loading work session context from breadcrumbs...

--- NEW AI SESSION (R3) ---

AI: I'm starting a new AI session for task-001: Implement feature X.
    Cookie: wsession-parent-abc123

    Previous AI session expired, but I can see the work session history:
    - Subtask task-002 completed (component Y investigated)
    - Breadcrumbs available from previous session

    I'll continue from where the previous session left off.
```

**Gates**: (resume failure triggers fallback)
**Stores write**: REPO_TRUTH_DOCS_MAESTRO (`work_sessions/wsession-parent-abc123.json` updated with new AI session ID)

---

## AI Perspective (Heuristic)

**What AI notices**:
- Managed mode requires explicit cookie in all breadcrumb calls (discipline)
- Work session persists across AI process boundaries (file-based state)
- Resume tokens allow session continuity when possible
- Subtasks inherit stacking context but get separate cookies
- JSON contract gate enforces structured communication (not free-form)

**What AI tries**:
- Include cookie in every breadcrumb call (prompt template enforcement)
- Construct breadcrumb messages as structured JSON or well-formed text
- Link subtask findings back to parent via summary breadcrumbs
- Resume using engine-specific mechanisms (Claude resume ID, ChatGPT conversation ID, etc.)
- Handle resume failures gracefully by reconstructing context from breadcrumbs

**Where AI tends to hallucinate**:
- May forget to include cookie (assumes orchestrator infers from context)
- May confuse work session ID with task ID (different concepts)
- May assume resume always succeeds (engine may reject stale IDs)
- May not account for cookie validation errors (assumes breadcrumb always succeeds)
- May assume breadcrumbs are free-form text (JSON contract gate requires structure)
- May forget that subtasks need their own work sessions (not shared with parent)

---

## Outcomes

### Outcome A: Full Lifecycle with Subtask and Resume

**Flow** (as shown in main runbook):
1. Parent work session starts (task-001, cookie A, AI session R1)
2. Subtask spawned (task-002, cookie B, AI session R2)
3. Subtask records breadcrumbs, completes, AI process exits
4. Parent work session resumes (AI session R1 restored, cookie A)
5. AI continues with subtask results available
6. Parent task completes

**Artifacts**:
- `tasks/task-001.json` (completed)
- `tasks/task-002.json` (completed, linked to parent)
- `work_sessions/wsession-parent-abc123.json` (closed, with subtask summary)
- `work_sessions/wsession-subtask-def456.json` (closed, with breadcrumbs)

**Duration**: ~30 minutes (includes subtask investigation and resume)

### Outcome B: Cookie Mismatch Detected → AI Reprompted

**Flow**:
1. AI session active with cookie A
2. AI attempts breadcrumb with cookie B (wrong)
3. JSON contract gate rejects breadcrumb
4. Error returned to AI
5. AI retries with correct cookie A
6. Breadcrumb accepted

**Artifacts**:
- No breadcrumb created from first (incorrect) call
- Breadcrumb created from second (correct) call

**Duration**: ~1 minute (quick error recovery)

### Outcome C: Resume Fails → New AI Session Created

**Flow** (alternative path):
1. User attempts resume for work session (cookie A, AI session R1)
2. AI session R1 no longer available (expired)
3. Orchestrator creates new AI session R3
4. Work session context loaded from breadcrumbs and metadata
5. AI continues with new session but same work session ID

**Artifacts**:
- `work_sessions/wsession-parent-abc123.json` updated with new `ai_session_id` (R3)
- Context preserved despite AI session change

**Duration**: ~5 minutes (includes new AI session initialization)

---

## Acceptance Gate Behavior

**JSON_CONTRACT_GATE**:
- All breadcrumb calls must include valid `--cookie` matching active work session
- Breadcrumb `--message` must be structured (JSON or well-formed text)
- Rejects calls with mismatched or missing cookies
- Ensures session discipline in managed mode

**WORK_SESSION_EXISTS gate**:
- Resume requires valid work session ID
- Work session must be in `active` or `paused` status (not `closed`)

---

## CLI Gaps / TODOs

```yaml
cli_gaps:
  - "TODO_CMD: maestro settings set ai_stacking_mode managed"
  - "TODO_CMD: maestro work spawn --from-task <task-id> --title <title>"
  - "TODO_CMD: maestro work resume <wsession-id>"
  - "TODO_CMD: maestro wsession breadcrumb add --cookie <cookie> --message <message>"
  - "TODO_CMD: maestro wsession breadcrumb list --cookie <cookie>"
  - "How AI session resume is engine-specific (Claude, ChatGPT, local LLM)"
  - "Whether work sessions can be paused/resumed without AI (metadata only)"
  - "Policy for work session expiration (stale sessions)"
  - "How subtask completion triggers summary breadcrumb to parent"
  - "Whether managed mode requires special AI engine capabilities (resume support)"
  - "Format for breadcrumb messages (structured JSON vs plain text)"
  - "How cookie validation is enforced in AI prompts (template discipline)"
```

---

## Trace Block (YAML)

```yaml
trace:
  - user: "maestro settings set ai_stacking_mode managed"
    intent: "Enable managed orchestration with session persistence"
    gates: []
    stores_write: []  # Settings file location TBD
    stores_read: []
    internal: ["update_settings"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro work task task-001"
    intent: "Start parent work session with AI session and cookie"
    gates: ["REPOCONF_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    stores_read: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["generate_wsession_id", "generate_ai_session_id", "launch_ai_with_cookie"]
    cli_confidence: "medium"  # work task exists, but session mechanics uncertain

  - user: "maestro work spawn --from-task task-001 --title 'Investigate component Y'"
    intent: "Spawn subtask with separate work session and AI session"
    gates: []
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    stores_read: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["create_subtask", "generate_wsession_id", "generate_ai_session_id", "link_to_parent"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro wsession breadcrumb add --cookie wsession-subtask-def456 --message '...'"
    intent: "Record finding in work session with cookie validation"
    gates: ["JSON_CONTRACT_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    stores_read: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["validate_cookie", "parse_message", "append_breadcrumb"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro work resume wsession-parent-abc123"
    intent: "Restore parent work session with AI session resume"
    gates: ["WORK_SESSION_EXISTS"]
    stores_write: []
    stores_read: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["load_wsession_metadata", "resume_ai_session", "reconstruct_context"]
    cli_confidence: "low"  # TODO_CMD
```

---

**Related:** Managed orchestration, session persistence, AI resume, stacking discipline, cookie validation, JSON contract gate
**Status:** Proposed
