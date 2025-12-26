# EX-20: Git Context Guard + Branch Hygiene — Commit Messages Tied to Task/Phase/Track

**Scope**: Git awareness and commit hygiene enforcement
**Build System**: N/A (git integration)
**Languages**: N/A
**Outcome**: Demonstrate that Maestro maintains situational awareness of git state: (1) captures branch context at work session start, (2) detects working tree changes, (3) prevents branch switching mid-work (guard), (4) generates commit messages reflecting task/phase/track completion

---

## Scenario Summary

Developer starts work on a task while on branch `feature/add-logging`. Maestro captures the git context (branch, commit hash, clean/dirty state). During the work session, the developer attempts to switch branches with `git switch main`, but Maestro's git guard detects the active work session and refuses to allow the switch without closing the session first. When the task is complete, Maestro suggests a commit message template tied to the task ID, phase, and track.

This demonstrates **git context guard as situational awareness** to maintain work session integrity and commit traceability.

---

## Preconditions

- Repository is a git repository (initialized with `.git/`)
- Maestro initialized in the repository
- At least one task exists, optionally linked to a phase and track
- User is on a feature branch (not main/master)
- Working directory is clean at work session start

---

## Minimal Project Skeleton

```
my-project/
├── .git/
├── docs/
│   └── maestro/
│       ├── repo.json
│       ├── tasks/
│       │   └── task-001.json
│       └── phases/
│           └── phase-alpha.json (optional)
└── src/
    └── logger.cpp (to be modified)
```

**task-001.json**:
```json
{
  "id": "task-001",
  "title": "Add logging module",
  "description": "Implement basic logging functionality",
  "status": "pending",
  "phase_id": "phase-alpha",
  "track_id": "track-core",
  "created_at": "2025-01-26T08:00:00Z"
}
```

**Git state (before work session)**:
```
$ git status
On branch feature/add-logging
nothing to commit, working tree clean

$ git log -1 --oneline
a3b5c7d Initial commit
```

---

## Runbook Steps

### Step 1: Start Work Session (Capture Git Context)

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro work task task-001` | Start work on task | Maestro captures git context (branch, commit, status) |

**Internal**:
- Run `git rev-parse --abbrev-ref HEAD` to get current branch
- Run `git rev-parse HEAD` to get current commit hash
- Run `git status --porcelain` to check dirty state
- Store git context in work session metadata
- Mark work session as "bound" to this branch

**System Output**:
```
[WORK] Starting work session for task: task-001 (Add logging module)
[WORK] Work session ID: wsession-logging-xyz123
[GIT] Captured git context:
[GIT]   Branch: feature/add-logging
[GIT]   Commit: a3b5c7d
[GIT]   Status: clean
[GIT] Work session bound to branch: feature/add-logging

AI: I'm starting work on task-001: Add logging module.
    Git context: On branch feature/add-logging (clean)

    [AI begins work...]
```

**Gates**: REPOCONF_GATE
**Stores write**: REPO_TRUTH_DOCS_MAESTRO (`work_sessions/wsession-logging-xyz123.json`)

**Artifact** (`work_sessions/wsession-logging-xyz123.json`):
```json
{
  "id": "wsession-logging-xyz123",
  "task_id": "task-001",
  "status": "active",
  "git_context": {
    "branch": "feature/add-logging",
    "commit": "a3b5c7d",
    "working_tree_clean": true,
    "captured_at": "2025-01-26T10:00:00Z"
  },
  "created_at": "2025-01-26T10:00:00Z"
}
```

### Step 2: Make Code Changes (Detect Dirty State)

| Command | Intent | Expected |
|---------|--------|----------|
| AI writes code to `src/logger.cpp` | Modify working tree | Maestro detects dirty state |

**Internal**:
- AI writes new code
- Optionally: Maestro hooks git status monitoring (via inotify or periodic poll)
- Detects working tree is now dirty

**System Output**:
```
AI: I've implemented the logging module in src/logger.cpp.

[GIT] Detected working tree changes:
[GIT]   Modified: src/logger.cpp
[GIT]   Status: dirty
```

**Git state**:
```
$ git status
On branch feature/add-logging
Changes not staged for commit:
  modified:   src/logger.cpp
```

### Step 3: Attempt Branch Switch (Git Guard Blocks)

| Command | Intent | Expected |
|---------|--------|----------|
| `git switch main` | Switch to main branch | Maestro git guard detects active work session and blocks |

**Internal**:
- Maestro hooks git pre-checkout or equivalent (via git hooks or wrapper)
- Detects active work session bound to `feature/add-logging`
- Refuses checkout to different branch

**System Output**:
```
$ git switch main

[MAESTRO GIT GUARD] Active work session detected!
[MAESTRO GIT GUARD] Work session: wsession-logging-xyz123
[MAESTRO GIT GUARD] Task: task-001 (Add logging module)
[MAESTRO GIT GUARD] Bound to branch: feature/add-logging
[MAESTRO GIT GUARD]
[MAESTRO GIT GUARD] Cannot switch branches with active work session.
[MAESTRO GIT GUARD]
[MAESTRO GIT GUARD] Options:
[MAESTRO GIT GUARD]   1. Close work session: maestro work close wsession-logging-xyz123
[MAESTRO GIT GUARD]   2. Use separate worktree: git worktree add ../main-worktree main
[MAESTRO GIT GUARD]
[MAESTRO GIT GUARD] Branch switch blocked.

fatal: Maestro git guard: Active work session prevents branch switch
```

**Gates**: GIT_GUARD_ACTIVE_WORK_SESSION (blocks operation)
**Stores read**: REPO_TRUTH_DOCS_MAESTRO

**Alternative** (if user really needs to switch):
```
$ maestro work close wsession-logging-xyz123
[WORK] Closing work session: wsession-logging-xyz123
[WORK] Work session paused. Resume later: maestro work resume wsession-logging-xyz123
[GIT GUARD] Work session closed. Branch switching now allowed.

$ git switch main
Switched to branch 'main'
```

### Step 4: Complete Task (Generate Commit Suggestion)

| Command | Intent | Expected |
|---------|--------|----------|
| Mark task complete | Task status updated, commit message suggested | Maestro generates commit template |

**AI Output**:
```
AI: Logging module implementation complete. All tests pass.
    Shall I mark this task as done?

User: /done

[WORK SESSION] Task task-001 marked as completed.
[WORK SESSION] Updated: ./docs/maestro/tasks/task-001.json
[GIT] Generating commit message suggestion...
```

**Gates**: (task completion always allowed)

### Step 5: Suggest Commit Message Template

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro ops commit suggest --task task-001` | Generate commit message | Template with task/phase/track references |

**Internal**:
- Read task metadata (task-001.json)
- Extract: task ID, title, phase, track
- Check git status for changed files
- Generate conventional commit message

**System Output**:
```
[COMMIT] Suggested commit message for task-001:

──────────────────────────────────────
task(core): add logging module

Implements basic logging functionality with configurable
output levels (DEBUG, INFO, WARN, ERROR).

Files changed:
- src/logger.cpp (new)

Task: task-001
Phase: phase-alpha
Track: track-core

Resolves: #task-001
──────────────────────────────────────

Copy to clipboard: maestro ops commit suggest --task task-001 --copy
Use directly: maestro ops commit create --task task-001
```

**Gates**: (suggestion is read-only)
**Stores read**: REPO_TRUTH_DOCS_MAESTRO

### Step 6: Create Commit with Suggested Message

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro ops commit create --task task-001` | Create git commit | Commit created with template message |

**Internal**:
- Generate commit message from template
- Stage all files changed during work session (optional: `git add .` or selective)
- Run `git commit -m "..."`
- Update work session with commit hash

**System Output**:
```
[COMMIT] Staging files changed during work session:
[COMMIT]   - src/logger.cpp

[COMMIT] Creating commit...

[feature/add-logging 3f8a1c2] task(core): add logging module
 1 file changed, 45 insertions(+)
 create mode 100644 src/logger.cpp

[COMMIT] Commit created: 3f8a1c2
[WORK SESSION] Updated wsession-logging-xyz123 with commit hash
```

**Artifact** (`work_sessions/wsession-logging-xyz123.json` updated):
```json
{
  "id": "wsession-logging-xyz123",
  "task_id": "task-001",
  "status": "completed",
  "git_context": {
    "branch": "feature/add-logging",
    "start_commit": "a3b5c7d",
    "end_commit": "3f8a1c2",
    "working_tree_clean": true
  },
  "completed_at": "2025-01-26T10:30:00Z"
}
```

**Gates**: (commit creation allowed if task complete)
**Stores write**: REPO_TRUTH_DOCS_MAESTRO

### Step 7: Close Work Session (Clean Exit)

| Command | Intent | Expected |
|---------|--------|----------|
| Work session automatically closed after commit | Clean up session state | Git guard released |

**System Output**:
```
[WORK SESSION] Task task-001 complete and committed.
[WORK SESSION] Closing work session: wsession-logging-xyz123
[GIT GUARD] Work session closed. Branch switching now allowed.

You can now safely switch branches.
```

**Gates**: (session closure releases git guard)

---

## Alternative Path: Uncommitted Changes with Branch Switch Attempt

### Step 3b: Git Guard Warns About Uncommitted Changes

**Scenario**: User tries to switch branches with uncommitted changes but no active work session

| Action | Intent | Expected |
|--------|--------|----------|
| Close work session first | Release git guard | Branch switch warning (standard git) |

**System Output**:
```
$ maestro work close wsession-logging-xyz123
[WORK] Closing work session: wsession-logging-xyz123
[GIT GUARD] Work session closed.

$ git switch main
error: Your local changes to the following files would be overwritten by checkout:
	src/logger.cpp
Please commit your changes or stash them before you switch branches.
Aborting
```

**Note**: Maestro's git guard only blocks when work session is active. Standard git protections still apply for uncommitted changes.

---

## Alternative Path: Commit Suggestion for Phase/Track Completion

### Step 5b: Phase Completes (Multiple Tasks)

**Scenario**: Task-001 was the last task in phase-alpha

| Action | Intent | Expected |
|--------|--------|----------|
| Mark task complete | Detect phase completion | Commit message includes phase milestone |

**System Output**:
```
[WORK SESSION] Task task-001 marked as completed.
[WORK SESSION] Detected: phase-alpha is now complete (all tasks done)
[COMMIT] Suggested commit message for phase-alpha:

──────────────────────────────────────
phase(alpha): complete core logging implementation

Completed all tasks in phase-alpha:
- task-001: Add logging module
- task-002: Add log file rotation
- task-003: Add configuration parser

Phase: phase-alpha (track: track-core)
Status: complete

Resolves: #phase-alpha
──────────────────────────────────────
```

---

## AI Perspective (Heuristic)

**What AI notices**:
- Git context is captured at work session start (branch, commit, status)
- Work sessions are bound to branches (can't switch mid-work without closing session)
- Commit messages follow conventional commit format: `<type>(<scope>): <subject>`
- Task/phase/track metadata is embedded in commit messages for traceability
- Git guard is a safety mechanism (prevents accidental branch switches)

**What AI tries**:
- Check git status before starting work (warn if dirty)
- Generate commit messages from task metadata (task ID, title, description)
- Include references to phase and track in commit message scope
- Suggest staging only files modified during work session (not unrelated changes)
- Detect phase/track completion milestones and adjust commit message accordingly

**Where AI tends to hallucinate**:
- May assume git guard auto-commits before branch switch (it blocks, doesn't commit)
- May confuse work session close with git stash (different operations)
- May assume commit messages are auto-generated (user must approve)
- May not account for merge conflicts when resuming on different branch
- May forget that git worktrees allow parallel work on different branches (alternative to blocking)
- May assume phase completion auto-creates milestone commits (requires explicit user action)

---

## Outcomes

### Outcome A: Clean Workflow with Git Guard Protection

**Flow** (as shown in main runbook):
1. Start work session on `feature/add-logging` (git context captured)
2. Make code changes (dirty state detected)
3. Attempt branch switch (git guard blocks)
4. Complete task, generate commit message
5. Create commit with task/phase/track metadata
6. Close work session (git guard released)

**Artifacts**:
- `tasks/task-001.json` (status: completed)
- `work_sessions/wsession-logging-xyz123.json` (with git context)
- Git commit `3f8a1c2` with structured message

**Duration**: ~15 minutes

### Outcome B: Force Branch Switch by Closing Work Session

**Flow**:
1. Start work session, make changes
2. Attempt branch switch (blocked)
3. User closes work session: `maestro work close wsession-logging-xyz123`
4. Branch switch allowed (work session paused)
5. Later: resume work session on original branch

**Artifacts**:
- Work session paused (can be resumed)
- Git state on different branch

**Duration**: ~5 minutes

### Outcome C: Phase Completion Milestone Commit

**Flow**:
1. Complete final task in phase-alpha
2. Maestro detects phase completion
3. Suggest milestone commit message referencing all phase tasks
4. Create commit marking phase completion

**Artifacts**:
- Phase metadata updated (status: complete)
- Git commit with phase milestone message

**Duration**: ~10 minutes

---

## Acceptance Gate Behavior

**GIT_GUARD_ACTIVE_WORK_SESSION gate**:
- Blocks `git switch`, `git checkout <branch>` when work session active
- Allows work session close/pause to release guard
- Does not block `git commit`, `git stash`, or same-branch operations

**Commit message validation** (optional):
- Enforce conventional commit format
- Require task/phase/track references
- Validate against task metadata

---

## CLI Gaps / TODOs

```yaml
cli_gaps:
  - "TODO_CMD: maestro ops git status-guard (check git guard status)"
  - "TODO_CMD: maestro ops commit suggest --task <task-id>"
  - "TODO_CMD: maestro ops commit create --task <task-id>"
  - "TODO_CMD: maestro work close <wsession-id>"
  - "TODO_CMD: maestro work pause <wsession-id> (vs close?)"
  - "How git guard is implemented (git hooks? wrapper? pre-checkout hook?)"
  - "Whether git guard supports git worktrees (parallel work on different branches)"
  - "Policy for git stash during work sessions (allowed or not?)"
  - "Whether commit suggestion is automatic or manual (on task completion)"
  - "How to customize commit message templates (per-project or global?)"
  - "Whether git guard blocks all branch operations or just switches (what about rebase, merge?)"
  - "How to handle detached HEAD state during work session"
```

---

## Trace Block (YAML)

```yaml
trace:
  - user: "maestro work task task-001"
    intent: "Start work session and capture git context"
    gates: ["REPOCONF_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    stores_read: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["capture_git_context", "bind_to_branch", "enable_git_guard"]
    cli_confidence: "medium"  # work task exists, git integration uncertain

  - user: "git switch main (blocked by git guard)"
    intent: "Attempt branch switch during active work session"
    gates: ["GIT_GUARD_ACTIVE_WORK_SESSION (BLOCKS)"]
    stores_write: []
    stores_read: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["check_active_wsession", "block_checkout"]
    cli_confidence: "low"  # Git guard implementation unclear

  - user: "maestro ops commit suggest --task task-001"
    intent: "Generate commit message from task metadata"
    gates: []
    stores_write: []
    stores_read: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["load_task_metadata", "generate_commit_template"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro ops commit create --task task-001"
    intent: "Create git commit with suggested message"
    gates: []
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    stores_read: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["stage_files", "create_commit", "update_wsession"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro work close wsession-logging-xyz123"
    intent: "Close work session and release git guard"
    gates: []
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    stores_read: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["close_wsession", "disable_git_guard"]
    cli_confidence: "low"  # TODO_CMD
```

---

**Related:** Git integration, branch guards, commit hygiene, task traceability, conventional commits
**Status:** Proposed
