#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }
MAESTRO_BIN="${MAESTRO_BIN:-maestro}"

# EX-20: Git Context Guard + Branch Hygiene — Commit Messages Tied to Task/Phase/Track

echo "=== Git Awareness: Context Guard and Commit Hygiene ==="
echo "Pipeline: Capture git context → Guard branch switching → Generate commit messages"

echo ""
echo "=== Minimal Project Skeleton ==="
echo "my-project/"
echo "├── .git/"
echo "├── docs/"
echo "│   └── maestro/"
echo "│       ├── repo.json"
echo "│       ├── tasks/"
echo "│       │   └── task-001.json"
echo "│       └── phases/"
echo "│           └── phase-alpha.json"
echo "└── src/"
echo "    └── logger.cpp"

echo ""
echo "Git state (before work session):"
run git status
echo "On branch feature/add-logging"
echo "nothing to commit, working tree clean"
echo ""
run git log -1 --oneline
echo "a3b5c7d Initial commit"

echo ""
echo "=== Step 1: Start Work Session (Capture Git Context) ==="

run "$MAESTRO_BIN" work task task-001
# EXPECT: Maestro captures git context (branch, commit, status)
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: capture_git_context, bind_to_branch, enable_git_guard

echo ""
echo "[WORK] Starting work session for task: task-001 (Add logging module)"
echo "[WORK] Work session ID: wsession-logging-xyz123"
echo "[GIT] Captured git context:"
echo "[GIT]   Branch: feature/add-logging"
echo "[GIT]   Commit: a3b5c7d"
echo "[GIT]   Status: clean"
echo "[GIT] Work session bound to branch: feature/add-logging"
echo ""
echo "AI: I'm starting work on task-001: Add logging module."
echo "    Git context: On branch feature/add-logging (clean)"
echo ""
echo "    [AI begins work...]"

echo ""
echo "Artifact: work_sessions/wsession-logging-xyz123.json"
echo "{"
echo "  \"id\": \"wsession-logging-xyz123\","
echo "  \"task_id\": \"task-001\","
echo "  \"status\": \"active\","
echo "  \"git_context\": {"
echo "    \"branch\": \"feature/add-logging\","
echo "    \"commit\": \"a3b5c7d\","
echo "    \"working_tree_clean\": true,"
echo "    \"captured_at\": \"2025-01-26T10:00:00Z\""
echo "  },"
echo "  \"created_at\": \"2025-01-26T10:00:00Z\""
echo "}"

echo ""
echo "=== Step 2: Make Code Changes (Detect Dirty State) ==="

echo ""
echo "AI: I've implemented the logging module in src/logger.cpp."
echo ""
echo "[GIT] Detected working tree changes:"
echo "[GIT]   Modified: src/logger.cpp"
echo "[GIT]   Status: dirty"

echo ""
run git status
echo "On branch feature/add-logging"
echo "Changes not staged for commit:"
echo "  modified:   src/logger.cpp"

echo ""
echo "=== Step 3: Attempt Branch Switch (Git Guard Blocks) ==="

run git switch main
# EXPECT: Git guard blocks operation
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: GIT_GUARD_ACTIVE_WORK_SESSION (BLOCKS)
# INTERNAL: check_active_wsession, block_checkout

echo ""
echo "[MAESTRO GIT GUARD] Active work session detected!"
echo "[MAESTRO GIT GUARD] Work session: wsession-logging-xyz123"
echo "[MAESTRO GIT GUARD] Task: task-001 (Add logging module)"
echo "[MAESTRO GIT GUARD] Bound to branch: feature/add-logging"
echo "[MAESTRO GIT GUARD]"
echo "[MAESTRO GIT GUARD] Cannot switch branches with active work session."
echo "[MAESTRO GIT GUARD]"
echo "[MAESTRO GIT GUARD] Options:"
echo "[MAESTRO GIT GUARD]   1. Close work session: maestro wsession close wsession-logging-xyz123"
echo "[MAESTRO GIT GUARD]   2. Use separate worktree: git worktree add ../main-worktree main"
echo "[MAESTRO GIT GUARD]"
echo "[MAESTRO GIT GUARD] Branch switch blocked."
echo ""
echo "fatal: Maestro git guard: Active work session prevents branch switch"

echo ""
echo "Alternative (if user closes work session first):"
run "$MAESTRO_BIN" wsession close wsession-logging-xyz123
echo ""
echo "[WORK] Closing work session: wsession-logging-xyz123"
echo "[WORK] Work session paused. Resume later: maestro work resume wsession-logging-xyz123"
echo "[GIT GUARD] Work session closed. Branch switching now allowed."

run git switch main
echo "Switched to branch 'main'"

echo ""
echo "=== Step 4: Complete Task (Generate Commit Suggestion) ==="

echo ""
echo "AI: Logging module implementation complete. All tests pass."
echo "    Shall I mark this task as done?"
echo ""
echo "User: /done"
echo ""
echo "[WORK SESSION] Task task-001 marked as completed."
echo "[WORK SESSION] Updated: ./docs/maestro/tasks/task-001.json"
echo "[GIT] Generating commit message suggestion..."

echo ""
echo "=== Step 5: Suggest Commit Message Template ==="

run "$MAESTRO_BIN" ops commit suggest --task task-001
echo "[NOT IMPLEMENTED] CLI_GAPS: GAP-0032"
# EXPECT: Template with task/phase/track references
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: (none - read-only)
# INTERNAL: load_task_metadata, generate_commit_template

echo ""
echo "[COMMIT] Suggested commit message for task-001:"
echo ""
echo "──────────────────────────────────────"
echo "task(core): add logging module"
echo ""
echo "Implements basic logging functionality with configurable"
echo "output levels (DEBUG, INFO, WARN, ERROR)."
echo ""
echo "Files changed:"
echo "- src/logger.cpp (new)"
echo ""
echo "Task: task-001"
echo "Phase: phase-alpha"
echo "Track: track-core"
echo ""
echo "Resolves: #task-001"
echo "──────────────────────────────────────"
echo ""
echo "Copy to clipboard: maestro ops commit suggest --task task-001 --copy"
echo "Use directly: maestro ops commit create --task task-001"

echo ""
echo "=== Step 6: Create Commit with Suggested Message ==="

run "$MAESTRO_BIN" ops commit create --task task-001
echo "[NOT IMPLEMENTED] CLI_GAPS: GAP-0033"
# EXPECT: Commit created with template message
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: (none)
# INTERNAL: stage_files, create_commit, update_wsession

echo ""
echo "[COMMIT] Staging files changed during work session:"
echo "[COMMIT]   - src/logger.cpp"
echo ""
echo "[COMMIT] Creating commit..."
echo ""
echo "[feature/add-logging 3f8a1c2] task(core): add logging module"
echo " 1 file changed, 45 insertions(+)"
echo " create mode 100644 src/logger.cpp"
echo ""
echo "[COMMIT] Commit created: 3f8a1c2"
echo "[WORK SESSION] Updated wsession-logging-xyz123 with commit hash"

echo ""
echo "Artifact: work_sessions/wsession-logging-xyz123.json updated"
echo "{"
echo "  \"id\": \"wsession-logging-xyz123\","
echo "  \"task_id\": \"task-001\","
echo "  \"status\": \"completed\","
echo "  \"git_context\": {"
echo "    \"branch\": \"feature/add-logging\","
echo "    \"start_commit\": \"a3b5c7d\","
echo "    \"end_commit\": \"3f8a1c2\","
echo "    \"working_tree_clean\": true"
echo "  },"
echo "  \"completed_at\": \"2025-01-26T10:30:00Z\""
echo "}"

echo ""
echo "=== Step 7: Close Work Session (Clean Exit) ==="

echo ""
echo "[WORK SESSION] Task task-001 complete and committed."
echo "[WORK SESSION] Closing work session: wsession-logging-xyz123"
echo "[GIT GUARD] Work session closed. Branch switching now allowed."
echo ""
echo "You can now safely switch branches."

echo ""
echo "=== Alternative Path: Uncommitted Changes with Branch Switch ==="

run "$MAESTRO_BIN" wsession close wsession-logging-xyz123
echo ""
echo "[WORK] Closing work session: wsession-logging-xyz123"
echo "[GIT GUARD] Work session closed."

run git switch main
echo ""
echo "error: Your local changes to the following files would be overwritten by checkout:"
echo "	src/logger.cpp"
echo "Please commit your changes or stash them before you switch branches."
echo "Aborting"
echo ""
echo "Note: Maestro git guard only blocks when work session active."
echo "      Standard git protections still apply for uncommitted changes."

echo ""
echo "=== Alternative Path: Phase Completion Milestone Commit ==="

echo ""
echo "[WORK SESSION] Task task-001 marked as completed."
echo "[WORK SESSION] Detected: phase-alpha is now complete (all tasks done)"
echo "[COMMIT] Suggested commit message for phase-alpha:"
echo ""
echo "──────────────────────────────────────"
echo "phase(alpha): complete core logging implementation"
echo ""
echo "Completed all tasks in phase-alpha:"
echo "- task-001: Add logging module"
echo "- task-002: Add log file rotation"
echo "- task-003: Add configuration parser"
echo ""
echo "Phase: phase-alpha (track: track-core)"
echo "Status: complete"
echo ""
echo "Resolves: #phase-alpha"
echo "──────────────────────────────────────"

echo ""
echo "=== Outcome A: Clean Workflow with Git Guard Protection ==="
echo "Flow:"
echo "  1. Start work session on feature/add-logging (git context captured)"
echo "  2. Make code changes (dirty state detected)"
echo "  3. Attempt branch switch (git guard blocks)"
echo "  4. Complete task, generate commit message"
echo "  5. Create commit with task/phase/track metadata"
echo "  6. Close work session (git guard released)"
echo ""
echo "Artifacts:"
echo "  - tasks/task-001.json (status: completed)"
echo "  - work_sessions/wsession-logging-xyz123.json (with git context)"
echo "  - Git commit 3f8a1c2 with structured message"
echo ""
echo "Duration: ~15 minutes"

echo ""
echo "=== Outcome B: Force Branch Switch by Closing Work Session ==="
echo "Flow:"
echo "  1. Start work session, make changes"
echo "  2. Attempt branch switch (blocked)"
echo "  3. User closes work session: maestro wsession close wsession-logging-xyz123"
echo "  4. Branch switch allowed (work session paused)"
echo "  5. Later: resume work session on original branch"
echo ""
echo "Artifacts:"
echo "  - Work session paused (can be resumed)"
echo "  - Git state on different branch"
echo ""
echo "Duration: ~5 minutes"

echo ""
echo "=== Outcome C: Phase Completion Milestone Commit ==="
echo "Flow:"
echo "  1. Complete final task in phase-alpha"
echo "  2. Maestro detects phase completion"
echo "  3. Suggest milestone commit message referencing all phase tasks"
echo "  4. Create commit marking phase completion"
echo ""
echo "Artifacts:"
echo "  - Phase metadata updated (status: complete)"
echo "  - Git commit with phase milestone message"
echo ""
echo "Duration: ~10 minutes"

echo ""
echo "=== Key Insights ==="
echo "  - Git context captured at work session start (branch, commit, status)"
echo "  - Work sessions are bound to branches (git guard prevents switching)"
echo "  - Commit messages follow conventional commit format"
echo "  - Task/phase/track metadata embedded in commit messages for traceability"
echo "  - Git guard is safety mechanism (prevents accidental branch switches)"
echo "  - Work session close releases git guard (allows branch switching)"
echo "  - Phase completion can generate milestone commits"
