#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }

# EX-19: Managed Mode — Resume AI Session + Stacking with Sub-Work Sessions

echo "=== Managed Orchestration: Session Persistence and Stacking Discipline ==="
echo "Pipeline: Work session persists → AI session resumes → Subtasks spawn → Cookie validation"

echo ""
echo "=== Minimal Project Skeleton ==="
echo "my-project/"
echo "├── docs/"
echo "│   └── maestro/"
echo "│       ├── repo.json"
echo "│       ├── tasks/"
echo "│       │   ├── task-001.json (parent: Implement feature X)"
echo "│       │   └── task-002.json (subtask: Investigate Y)"
echo "│       └── work_sessions/"
echo "│           ├── wsession-parent-abc123.json"
echo "│           └── wsession-subtask-def456.json"
echo "└── src/"

echo ""
echo "=== Step 1: Configure Managed Stacking Mode ==="

run maestro settings set ai_stacking_mode managed  # TODO_CMD
# EXPECT: Settings updated
# STORES_WRITE: (settings file location TBD)
# GATES: (none)

echo ""
echo "[SETTINGS] Updated: ai_stacking_mode = managed"
echo "[SETTINGS] Managed mode enabled:"
echo "  - AI sessions persist via resume tokens"
echo "  - Work sessions persist across AI processes"
echo "  - Stacking spawns subtasks with session cookies"
echo "  - Breadcrumb calls validated with JSON contract"

echo ""
echo "=== Step 2: Start Parent Work Session ==="

run maestro work task task-001
# EXPECT: AI session begins, work session created
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: generate_wsession_id, generate_ai_session_id, launch_ai_with_cookie

echo ""
echo "[WORK] Starting work session for task: task-001 (Implement feature X)"
echo "[WORK] Work session ID: wsession-parent-abc123"
echo "[WORK] AI session ID: ai-session-r1-xyz789"
echo "[WORK] Cookie: wsession-parent-abc123"
echo ""
echo "AI: I'm starting work on task-001: Implement feature X."
echo "    Let me first understand the current codebase structure."
echo ""
echo "    [AI reads files, explores code...]"
echo ""
echo "    I notice this feature depends on understanding component Y."
echo "    Would you like me to spawn a subtask to investigate Y first?"
echo ""
echo "User: Yes, investigate Y."

echo ""
echo "Artifact: work_sessions/wsession-parent-abc123.json"
echo "{"
echo "  \"id\": \"wsession-parent-abc123\","
echo "  \"task_id\": \"task-001\","
echo "  \"ai_session_id\": \"ai-session-r1-xyz789\","
echo "  \"status\": \"active\","
echo "  \"created_at\": \"2025-01-26T10:00:00Z\","
echo "  \"breadcrumbs\": [],"
echo "  \"subtasks\": []"
echo "}"

echo ""
echo "=== Step 3: Spawn Subtask with Separate Session ==="

run maestro work spawn --from-task task-001 --title "Investigate component Y"  # TODO_CMD
# EXPECT: Subtask created, new AI session spawned
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# INTERNAL: create_subtask, generate_wsession_id, generate_ai_session_id, link_to_parent

echo ""
echo "[WORK] Spawning subtask from task-001"
echo "[WORK] Created task: task-002 (Investigate component Y)"
echo "[WORK] Work session ID: wsession-subtask-def456"
echo "[WORK] AI session ID: ai-session-r2-uvw456"
echo "[WORK] Cookie: wsession-subtask-def456"
echo "[WORK] Parent work session: wsession-parent-abc123"
echo ""
echo "--- NEW AI SESSION (R2) ---"
echo ""
echo "AI (subtask): I'm working on subtask task-002: Investigate component Y."
echo "              Cookie: wsession-subtask-def456"
echo ""
echo "              [AI investigates component Y...]"
echo ""
echo "              Component Y is a utility module that handles data validation."
echo "              It has 3 main functions: validate(), sanitize(), transform()."
echo ""
echo "              I'll record this finding as a breadcrumb."

echo ""
echo "Artifact: tasks/task-002.json"
echo "{"
echo "  \"id\": \"task-002\","
echo "  \"title\": \"Investigate component Y\","
echo "  \"status\": \"in_progress\","
echo "  \"parent_task\": \"task-001\","
echo "  \"created_at\": \"2025-01-26T10:05:00Z\""
echo "}"

echo ""
echo "Artifact: work_sessions/wsession-subtask-def456.json"
echo "{"
echo "  \"id\": \"wsession-subtask-def456\","
echo "  \"task_id\": \"task-002\","
echo "  \"parent_wsession_id\": \"wsession-parent-abc123\","
echo "  \"ai_session_id\": \"ai-session-r2-uvw456\","
echo "  \"status\": \"active\","
echo "  \"created_at\": \"2025-01-26T10:05:00Z\","
echo "  \"breadcrumbs\": []"
echo "}"

echo ""
echo "=== Step 4: Subtask AI Records Breadcrumb (with Cookie) ==="

run maestro wsession breadcrumb add --cookie wsession-subtask-def456 --message "Found 3 main functions in component Y: validate, sanitize, transform"  # TODO_CMD
# EXPECT: Breadcrumb added
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: JSON_CONTRACT_GATE
# INTERNAL: validate_cookie, parse_message, append_breadcrumb

echo ""
echo "[WSESSION] Breadcrumb added to wsession-subtask-def456"
echo "[WSESSION] Validation: Cookie matches active session ✓"
echo "[WSESSION] Validation: JSON contract satisfied ✓"
echo "[WSESSION] Breadcrumb ID: bc-001"
echo ""
echo "Breadcrumb recorded:"
echo "  \"Found 3 main functions in component Y: validate, sanitize, transform\""

echo ""
echo "Artifact: work_sessions/wsession-subtask-def456.json updated"
echo "{"
echo "  \"breadcrumbs\": ["
echo "    {"
echo "      \"id\": \"bc-001\","
echo "      \"message\": \"Found 3 main functions in component Y: validate, sanitize, transform\","
echo "      \"timestamp\": \"2025-01-26T10:08:00Z\","
echo "      \"ai_session_id\": \"ai-session-r2-uvw456\""
echo "    }"
echo "  ]"
echo "}"

echo ""
echo "=== Step 5: Subtask Completes, AI Process Exits ==="

echo ""
echo "AI (subtask): Investigation complete. Component Y provides data validation utilities."
echo "              Marking task-002 as complete."
echo ""
echo "User: /done"
echo ""
echo "[WORK SESSION] Task task-002 marked as completed."
echo "[WORK SESSION] Updated: ./docs/maestro/tasks/task-002.json"
echo "[WORK SESSION] Work session wsession-subtask-def456 closed."
echo "[WORK SESSION] Summary breadcrumb sent to parent: wsession-parent-abc123"
echo ""
echo "--- AI SESSION R2 TERMINATED ---"

echo ""
echo "Artifact: work_sessions/wsession-parent-abc123.json updated"
echo "{"
echo "  \"subtasks\": ["
echo "    {"
echo "      \"task_id\": \"task-002\","
echo "      \"wsession_id\": \"wsession-subtask-def456\","
echo "      \"status\": \"completed\","
echo "      \"summary\": \"Investigated component Y: provides validate, sanitize, transform functions\""
echo "    }"
echo "  ]"
echo "}"

echo ""
echo "=== Step 6: Resume Parent Work Session (New Process) ==="

run maestro work resume wsession-parent-abc123  # TODO_CMD
# EXPECT: AI session resumed with previous context
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: WORK_SESSION_EXISTS
# INTERNAL: load_wsession_metadata, resume_ai_session, reconstruct_context

echo ""
echo "[WORK] Resuming work session: wsession-parent-abc123"
echo "[WORK] Task: task-001 (Implement feature X)"
echo "[WORK] AI session: ai-session-r1-xyz789 (resuming...)"
echo "[WORK] Cookie: wsession-parent-abc123"
echo "[WORK] Subtasks completed: 1 (task-002)"
echo ""
echo "--- AI SESSION R1 RESUMED ---"
echo ""
echo "AI: Welcome back! I'm resuming work on task-001: Implement feature X."
echo "    Cookie: wsession-parent-abc123"
echo ""
echo "    I see that subtask task-002 (Investigate component Y) has been completed."
echo "    Summary: Component Y provides validate, sanitize, transform functions."
echo ""
echo "    I can now proceed with implementing feature X using component Y."
echo "    Shall I start writing the code?"
echo ""
echo "User: Yes, proceed."

echo ""
echo "=== Step 7: AI Attempts Breadcrumb with Wrong Cookie (Validation Failure) ==="

echo ""
echo "Scenario: AI session R1 (parent) mistakenly uses cookie B (subtask)"
echo ""
run maestro wsession breadcrumb add --cookie wsession-subtask-def456 --message "Implemented feature X"  # TODO_CMD
# EXPECT: Breadcrumb rejected
# GATES: JSON_CONTRACT_GATE (FAILED)

echo ""
echo "[WSESSION] ERROR: Cookie mismatch"
echo "[WSESSION] Expected cookie: wsession-parent-abc123 (active session)"
echo "[WSESSION] Received cookie: wsession-subtask-def456 (inactive/completed session)"
echo "[WSESSION] Breadcrumb rejected."
echo ""
echo "Error: Invalid cookie. Use correct work session cookie for current session."

echo ""
echo "AI: I apologize for the error. Let me use the correct cookie."
echo ""
run maestro wsession breadcrumb add --cookie wsession-parent-abc123 --message "Implemented feature X using component Y"  # TODO_CMD
# EXPECT: Breadcrumb accepted

echo ""
echo "[WSESSION] Breadcrumb added to wsession-parent-abc123 ✓"

echo ""
echo "=== Alternative Path: Resume with Stale AI Session ID ==="

run maestro work resume wsession-parent-abc123  # TODO_CMD
# EXPECT: Resume fails, new AI session created

echo ""
echo "[WORK] Resuming work session: wsession-parent-abc123"
echo "[WORK] AI session: ai-session-r1-xyz789"
echo "[WORK] Attempting resume... FAILED"
echo "[WORK] Error: AI session ai-session-r1-xyz789 no longer available (expired or deleted)"
echo ""
echo "[WORK] Fallback: Creating new AI session for work session"
echo "[WORK] New AI session ID: ai-session-r3-new123"
echo "[WORK] Cookie: wsession-parent-abc123 (unchanged)"
echo "[WORK] Loading work session context from breadcrumbs..."
echo ""
echo "--- NEW AI SESSION (R3) ---"
echo ""
echo "AI: I'm starting a new AI session for task-001: Implement feature X."
echo "    Cookie: wsession-parent-abc123"
echo ""
echo "    Previous AI session expired, but I can see the work session history:"
echo "    - Subtask task-002 completed (component Y investigated)"
echo "    - Breadcrumbs available from previous session"
echo ""
echo "    I'll continue from where the previous session left off."

echo ""
echo "=== Outcome A: Full Lifecycle with Subtask and Resume ==="
echo "Flow:"
echo "  1. Parent work session starts (task-001, cookie A, AI session R1)"
echo "  2. Subtask spawned (task-002, cookie B, AI session R2)"
echo "  3. Subtask records breadcrumbs, completes, AI process exits"
echo "  4. Parent work session resumes (AI session R1 restored, cookie A)"
echo "  5. AI continues with subtask results available"
echo "  6. Parent task completes"
echo ""
echo "Artifacts:"
echo "  - tasks/task-001.json (completed)"
echo "  - tasks/task-002.json (completed, linked to parent)"
echo "  - work_sessions/wsession-parent-abc123.json (closed, with subtask summary)"
echo "  - work_sessions/wsession-subtask-def456.json (closed, with breadcrumbs)"
echo ""
echo "Duration: ~30 minutes"

echo ""
echo "=== Outcome B: Cookie Mismatch Detected → AI Reprompted ==="
echo "Flow:"
echo "  1. AI session active with cookie A"
echo "  2. AI attempts breadcrumb with cookie B (wrong)"
echo "  3. JSON contract gate rejects breadcrumb"
echo "  4. Error returned to AI"
echo "  5. AI retries with correct cookie A"
echo "  6. Breadcrumb accepted"
echo ""
echo "Duration: ~1 minute (quick error recovery)"

echo ""
echo "=== Outcome C: Resume Fails → New AI Session Created ==="
echo "Flow:"
echo "  1. User attempts resume for work session (cookie A, AI session R1)"
echo "  2. AI session R1 no longer available (expired)"
echo "  3. Orchestrator creates new AI session R3"
echo "  4. Work session context loaded from breadcrumbs and metadata"
echo "  5. AI continues with new session but same work session ID"
echo ""
echo "Artifacts:"
echo "  - work_sessions/wsession-parent-abc123.json updated with new ai_session_id (R3)"
echo "  - Context preserved despite AI session change"
echo ""
echo "Duration: ~5 minutes (includes new AI session initialization)"

echo ""
echo "=== Key Insights ==="
echo "  - Managed mode requires explicit cookie in all breadcrumb calls"
echo "  - Work session persists across AI process boundaries (file-based state)"
echo "  - Resume tokens allow session continuity when possible"
echo "  - Subtasks inherit stacking context but get separate cookies"
echo "  - JSON contract gate enforces structured communication"
echo "  - Cookie validation prevents cross-session contamination"
echo "  - Resume failures trigger fallback to new AI session with context reconstruction"
