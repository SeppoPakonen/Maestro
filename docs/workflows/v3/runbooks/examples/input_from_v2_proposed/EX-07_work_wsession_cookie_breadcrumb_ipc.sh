#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }
MAESTRO_BIN="${MAESTRO_BIN:-maestro}"

# EX-07: `maestro work` ↔ `maestro wsession` — Cookie, Breadcrumbs, IPC Mailbox, Multi-Process

echo "=== Work Session Architecture: File-Based IPC ==="
echo "Location: \$HOME/.maestro/ipc/<session-id>/"
echo "Files:"
echo "  - cookie              # Session cookie (secret token)"
echo "  - breadcrumbs.json    # Progress updates from AI"
echo "  - context.json        # Task/phase/track context snapshot"
echo "  - mutations.log       # Optional: repo truth mutations (if enabled)"

echo ""
echo "=== Step 1: Start Work Session ==="

run "$MAESTRO_BIN" work task task-001
# EXPECT: Work session created, AI context loaded
# STORES_WRITE: IPC_MAILBOX, REPO_TRUTH_DOCS_MAESTRO (task → in_progress)
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: generate_session_id, generate_cookie, create_ipc_mailbox

echo ""
echo "[WORK SESSION] Session ID: ws-20250126-abc123"
echo "[WORK SESSION] Cookie: cookie-7f3a9b2e"
echo "[WORK SESSION] IPC Mailbox: \$HOME/.maestro/ipc/ws-20250126-abc123/"
echo ""
echo "Creating IPC mailbox files:"
echo "  - \$HOME/.maestro/ipc/ws-20250126-abc123/cookie (written)"
echo "  - \$HOME/.maestro/ipc/ws-20250126-abc123/context.json (written)"
echo "  - \$HOME/.maestro/ipc/ws-20250126-abc123/breadcrumbs.json (initialized as [])"
echo ""
echo "Loading task context:"
echo "  - Task: task-001 'Implement login endpoint'"
echo "  - Phase: phase-001 'P1: Core Features'"
echo "  - Track: track-001 'Sprint 1'"
echo ""
echo "Marking task task-001 as in_progress..."

echo ""
echo "=== Step 2: AI Receives Cookie in Prompt ==="

echo ""
echo "System Prompt (excerpt sent to AI):"
echo "---"
echo "You are helping with task-001: 'Implement login endpoint'"
echo ""
echo "Context:"
echo "- Phase: phase-001 'P1: Core Features'"
echo "- Track: track-001 'Sprint 1'"
echo ""
echo "Work Session:"
echo "- Session ID: ws-20250126-abc123"
echo "- Cookie: cookie-7f3a9b2e"
echo ""
echo "You may update progress by calling:"
echo "maestro wsession breadcrumb add --cookie cookie-7f3a9b2e --prompt \"Your progress message\""
echo "---"

echo ""
echo "=== Step 3: AI Makes Progress and Updates Breadcrumbs ==="

run "$MAESTRO_BIN" wsession breadcrumb add --cookie cookie-7f3a9b2e --prompt "Analyzing codebase..."
# EXPECT: Breadcrumb appended to IPC mailbox
# STORES_WRITE: IPC_MAILBOX
# GATES: COOKIE_VALIDATION
# INTERNAL: validate_cookie, append_breadcrumb

echo ""
echo "[WSESSION] Validating cookie... OK"
echo "[WSESSION] Appending breadcrumb to \$HOME/.maestro/ipc/ws-20250126-abc123/breadcrumbs.json"
echo ""
echo "Breadcrumb written:"
echo "{"
echo "  \"timestamp\": \"2025-01-26T14:32:01Z\","
echo "  \"status\": \"Analyzing codebase...\","
echo "  \"metadata\": {}"
echo "}"

echo ""
echo "=== Step 4: AI Continues, Adds More Breadcrumbs ==="

run "$MAESTRO_BIN" wsession breadcrumb add --cookie cookie-7f3a9b2e --prompt "Implementing password hashing..."
# EXPECT: Another breadcrumb appended
# STORES_WRITE: IPC_MAILBOX
# GATES: COOKIE_VALIDATION

echo ""
echo "[WSESSION] Breadcrumb appended: 'Implementing password hashing...'"

run "$MAESTRO_BIN" wsession breadcrumb add --cookie cookie-7f3a9b2e --prompt "Writing unit tests..."
echo ""
echo "[WSESSION] Breadcrumb appended: 'Writing unit tests...'"

echo ""
echo "Current breadcrumbs count: 3"

echo ""
echo "=== Step 5: User Checks Progress (Optional) ==="

run "$MAESTRO_BIN" wsession show ws-20250126-abc123
# EXPECT: Displays all breadcrumbs
# STORES_READ: IPC_MAILBOX
# GATES: (none)

echo ""
echo "Work Session: ws-20250126-abc123"
echo "Task: task-001 'Implement login endpoint'"
echo ""
echo "Breadcrumbs:"
echo "  [14:32:01] Analyzing codebase..."
echo "  [14:35:12] Implementing password hashing..."
echo "  [14:38:45] Writing unit tests..."

echo ""
echo "=== Step 6: User Closes Session ==="

echo ""
echo "User exits AI session (types /done or exits)"
echo "[WORK SESSION] Session state preserved in IPC mailbox"
echo "[WORK SESSION] Cookie remains valid for future appends"

echo ""
echo "=== Step 7: Resume Session Later ==="

run "$MAESTRO_BIN" work resume ws-20250126-abc123
# EXPECT: NOT IMPLEMENTED (CLI_GAPS: GAP-0018)
# STORES_READ: IPC_MAILBOX, REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: load_session_context, load_breadcrumbs

echo ""
echo "[WORK SESSION] Resuming session ws-20250126-abc123"
echo "[WORK SESSION] Loading context.json..."
echo "[WORK SESSION] Loading breadcrumbs.json (3 entries)..."
echo ""
echo "AI: Welcome back! I was working on implementing password hashing for the login endpoint."
echo "AI: I've completed unit tests. Would you like me to continue?"

echo ""
echo "=== Conceptual: Cookie Validation ==="

echo ""
echo "# Attempt with wrong cookie (fails):"
run "$MAESTRO_BIN" wsession breadcrumb add --cookie wrong-cookie --prompt "Hacked"
echo ""
echo "[WSESSION] Validating cookie..."
echo "ERROR: Invalid cookie for session ws-20250126-abc123"
echo "Expected: cookie-7f3a9b2e"
echo "Got: wrong-cookie"
echo "Breadcrumb REJECTED"

echo ""
echo "=== Outcome B: Cookie Missing → Breadcrumb Rejected ==="

run "$MAESTRO_BIN" wsession breadcrumb add --prompt "Progress..."
# Missing --cookie flag
echo ""
echo "ERROR: Cookie required for breadcrumb update"
echo "Usage: maestro wsession breadcrumb add --cookie <cookie> --prompt <msg>"

echo ""
echo "=== Multi-Process Safety ==="

echo ""
echo "File-based IPC allows multiple processes to interact:"
echo "  - Process 1 (AI): Writes breadcrumbs via 'maestro wsession breadcrumb add'"
echo "  - Process 2 (User CLI): Reads breadcrumbs via 'maestro wsession show'"
echo "  - Process 3 (Web UI): Polls breadcrumbs.json for live updates"
echo ""
echo "No locking required for reads. Appends are OS-atomic."

echo ""
echo "=== EX-07 Outcome A: Breadcrumbs Accumulated, Session Resumed ==="
echo "Artifacts:"
echo "  - IPC mailbox: \$HOME/.maestro/ipc/ws-20250126-abc123/"
echo "  - Breadcrumbs: 3 entries in breadcrumbs.json"
echo "  - Cookie: cookie-7f3a9b2e (still valid)"
echo "  - Session can be resumed anytime"

echo ""
echo "=== Optional: Mutation Mode (Advanced) ==="
echo "# By default, AI cannot mutate repo truth during work session"
echo "# But with --allow-mutations flag (if it exists):"
echo ""
echo "# run maestro work task task-001 --allow-mutations  # NOT IMPLEMENTED (CLI_GAPS: GAP-0031)"
echo "#   → AI can call: maestro task update task-001 --status completed"
echo "#   → Changes written to ./docs/maestro/tasks/task-001.json"
echo "#   → Logged in mutations.log"
echo ""
echo "# Risk: AI can corrupt repo truth if buggy"
echo "# Default: NO mutations, only breadcrumbs"
