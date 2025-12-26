# Ledger Candidates — Spec→Code Contradictions

This report lists contradictions detected between v2 specification and observed v1 code behavior.
Generated automatically from command IR extraction.

**Total candidates:** 41

---

## 1. Storage Backend Violations (REPO_TRUTH_FORMAT_IS_JSON)

**Count:** 12

Commands using markdown or mixed storage backend instead of JSON:

### CMD-discuss

- **Storage backend:** markdown
- **File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-discuss.code.yaml`
- **Invariant violated:** REPO_TRUTH_FORMAT_IS_JSON
- **Fix required:** Replace markdown persistence with JSON in command implementation

### CMD-init

- **Storage backend:** markdown
- **File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-init.code.yaml`
- **Invariant violated:** REPO_TRUTH_FORMAT_IS_JSON
- **Fix required:** Replace markdown persistence with JSON in command implementation

### CMD-issues

- **Storage backend:** markdown
- **File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-issues.code.yaml`
- **Invariant violated:** REPO_TRUTH_FORMAT_IS_JSON
- **Fix required:** Replace markdown persistence with JSON in command implementation

### CMD-ops

- **Storage backend:** mixed
- **File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-ops.code.yaml`
- **Invariant violated:** REPO_TRUTH_FORMAT_IS_JSON
- **Fix required:** Replace markdown persistence with JSON in command implementation

### CMD-phase

- **Storage backend:** mixed
- **File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-phase.code.yaml`
- **Invariant violated:** REPO_TRUTH_FORMAT_IS_JSON
- **Fix required:** Replace markdown persistence with JSON in command implementation

### CMD-plan

- **Storage backend:** markdown
- **File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-plan.code.yaml`
- **Invariant violated:** REPO_TRUTH_FORMAT_IS_JSON
- **Fix required:** Replace markdown persistence with JSON in command implementation

### CMD-resume

- **Storage backend:** markdown
- **File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-resume.code.yaml`
- **Invariant violated:** REPO_TRUTH_FORMAT_IS_JSON
- **Fix required:** Replace markdown persistence with JSON in command implementation

### CMD-settings

- **Storage backend:** mixed
- **File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-settings.code.yaml`
- **Invariant violated:** REPO_TRUTH_FORMAT_IS_JSON
- **Fix required:** Replace markdown persistence with JSON in command implementation

### CMD-solutions

- **Storage backend:** markdown
- **File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-solutions.code.yaml`
- **Invariant violated:** REPO_TRUTH_FORMAT_IS_JSON
- **Fix required:** Replace markdown persistence with JSON in command implementation

### CMD-task

- **Storage backend:** mixed
- **File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-task.code.yaml`
- **Invariant violated:** REPO_TRUTH_FORMAT_IS_JSON
- **Fix required:** Replace markdown persistence with JSON in command implementation

### CMD-track

- **Storage backend:** mixed
- **File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-track.code.yaml`
- **Invariant violated:** REPO_TRUTH_FORMAT_IS_JSON
- **Fix required:** Replace markdown persistence with JSON in command implementation

### CMD-understand

- **Storage backend:** markdown
- **File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-understand.code.yaml`
- **Invariant violated:** REPO_TRUTH_FORMAT_IS_JSON
- **Fix required:** Replace markdown persistence with JSON in command implementation

---

## 2. Explicit Ledger Hints from Code Layer

**Count:** 29

Hints explicitly flagged during extraction:

### CMD-ai

**File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-ai.code.yaml`

- Observed legacy Qwen server/TUI functionality in cmd_ai deep flow; v2 repo truth uses JSON. These legacy paths may need to be deprecated or updated to align with modern AI engine manager patterns.

### CMD-convert

**File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-convert.code.yaml`

- Observed .maestro/convert/ directory usage in cmd_convert deep flow; violates FORBID_REPO_DOT_MAESTRO invariant; migrate to ./docs/maestro/convert/

### CMD-discuss

**File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-discuss.code.yaml`

- Observed DataMarkdown persistence in cmd_discuss deep flow; v2 repo truth uses JSON. Replace/remove DataMarkdown codepaths and update docs/tests.

### CMD-init

**File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-init.code.yaml`

- Observed DataMarkdown persistence in cmd_init deep flow; v2 repo truth uses JSON. Replace/remove DataMarkdown codepaths and update docs/tests.

### CMD-issues

**File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-issues.code.yaml`

- Observed DataMarkdown persistence in cmd_issues deep flow; v2 repo truth uses JSON. Replace/remove DataMarkdown codepaths and update docs/tests.
- Uses ./docs/issues/*.md, ./docs/solutions/*.md, and ./docs/sessions/*.md for persistence; violates REPO_TRUTH_FORMAT_IS_JSON invariant as these are markdown files.

### CMD-phase

**File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-phase.code.yaml`

- Observed DataMarkdown persistence in cmd_phase deep flow; v2 repo truth uses JSON. Replace/remove DataMarkdown codepaths and update docs/tests.
- Observed .maestro directory usage in cmd_phase deep flow; violates FORBID_REPO_DOT_MAESTRO invariant; migrate to ./docs/maestro/.
- Observed markdown file persistence for repo truth in cmd_phase deep flow; violates REPO_TRUTH_FORMAT_IS_JSON invariant; migrate to JSON-only storage.

### CMD-plan

**File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-plan.code.yaml`

- Observed DataMarkdown persistence in cmd_plan deep flow; v2 repo truth uses JSON. Replace/remove DataMarkdown codepaths and update docs/tests.
- Plan storage uses docs/plans.md which violates REPO_TRUTH_FORMAT_IS_JSON invariant; migrate to JSON format.

### CMD-repo

**File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-repo.code.yaml`

- Observed .maestro directory usage in cmd_repo deep flow; violates FORBID_REPO_DOT_MAESTRO invariant; migrate to ./docs/maestro/.

### CMD-resume

**File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-resume.code.yaml`

- Observed DataMarkdown persistence in cmd_resume deep flow; v2 repo truth uses JSON. Replace/remove DataMarkdown codepaths and update docs/tests.

### CMD-root

**File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-root.code.yaml`

- Observed .maestro/conversations/ directory usage in cmd_root deep flow; v2 spec uses only ./docs/maestro/ for persistence. Enforce REPO_TRUTH_IS_DOCS_MAESTRO and remove .maestro usage.

### CMD-rules

**File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-rules.code.yaml`

- Observed ./.maestro directory usage in cmd_rules deep flow; v2 repo truth uses ./docs/maestro/. Replace ./.maestro references with ./docs/maestro/ and update docs/tests.

### CMD-session

**File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-session.code.yaml`

- Observed session data stored in JSON format under docs/sessions/; aligns with REPO_TRUTH_FORMAT_IS_JSON invariant
- Observed user-specific config in ~/.maestro/config.json; aligns with HOME_HUB_ALLOWED_IN_READONLY invariant

### CMD-settings

**File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-settings.code.yaml`

- Observed DataMarkdown persistence in cmd_settings deep flow; v2 repo truth uses JSON. Replace/remove DataMarkdown codepaths and update docs/tests.
- Observed .maestro directory usage for profiles; violates FORBID_REPO_DOT_MAESTRO invariant; migrate to ./docs/maestro/ for repo-specific profiles.
- Settings stored in docs/config.md using markdown format; violates REPO_TRUTH_FORMAT_IS_JSON invariant; migrate to JSON format.

### CMD-solutions

**File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-solutions.code.yaml`

- Observed markdown persistence in cmd_solutions deep flow; v2 repo truth uses JSON. Replace/remove markdown codepaths and update docs/tests.
- Observed ./.maestro directory usage in _find_repo_root; violates FORBID_REPO_DOT_MAESTRO invariant; migrate to ./docs/maestro/

### CMD-task

**File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-task.code.yaml`

- Observed DataMarkdown persistence in cmd_task deep flow; v2 repo truth uses JSON. Replace/remove DataMarkdown codepaths and update docs/tests.
- Shows mixed persistence model with both JSON and Markdown files; v2 spec requires REPO_TRUTH_FORMAT_IS_JSON invariant. Migrate to JSON-only persistence.

### CMD-track

**File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-track.code.yaml`

- Observed mixed persistence in cmd_track deep flow; uses both DataMarkdown (docs/todo.md, docs/done.md) and JSON (.maestro/tracks/*.json); v2 repo truth uses JSON only. Consider migration strategy to remove markdown persistence paths.

### CMD-tu

**File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-tu.code.yaml`

- Observed .maestro directory usage for TU cache and analysis; violates FORBID_REPO_DOT_MAESTRO invariant; migrate to ./docs/maestro/ structure

### CMD-understand

**File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-understand.code.yaml`

- Observed DataMarkdown persistence in cmd_understand deep flow; v2 repo truth uses JSON. Replace/remove DataMarkdown codepaths and update docs/tests.

### CMD-work

**File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-work.code.yaml`

- Observed DataMarkdown persistence in cmd_work deep flow; v2 repo truth uses JSON. Replace/remove DataMarkdown codepaths and update docs/tests.

### CMD-wsession

**File:** `/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-wsession.code.yaml`

- Observed JSON persistence in cmd_wsession deep flow with session.json and breadcrumbs.jsonl; aligns with v2 repo truth using JSON. Confirmed REPO_TRUTH_FORMAT_IS_JSON invariant.

---

## 3. Summary by Command

| Command | Issues | Storage Backend | File |
|---------|--------|-----------------|------|
| CMD-ai | 1 | json | CMD-ai.code.yaml |
| CMD-convert | 1 | unknown | CMD-convert.code.yaml |
| CMD-discuss | 2 | markdown | CMD-discuss.code.yaml |
| CMD-help | 0 | unknown | — |
| CMD-init | 2 | markdown | CMD-init.code.yaml |
| CMD-issues | 3 | markdown | CMD-issues.code.yaml |
| CMD-log | 0 | unknown | — |
| CMD-ops | 1 | mixed | CMD-ops.code.yaml |
| CMD-phase | 4 | mixed | CMD-phase.code.yaml |
| CMD-plan | 3 | markdown | CMD-plan.code.yaml |
| CMD-repo | 1 | json | CMD-repo.code.yaml |
| CMD-resume | 2 | markdown | CMD-resume.code.yaml |
| CMD-root | 1 | json | CMD-root.code.yaml |
| CMD-rules | 1 | unknown | CMD-rules.code.yaml |
| CMD-session | 2 | json | CMD-session.code.yaml |
| CMD-settings | 4 | mixed | CMD-settings.code.yaml |
| CMD-solutions | 3 | markdown | CMD-solutions.code.yaml |
| CMD-task | 3 | mixed | CMD-task.code.yaml |
| CMD-track | 2 | mixed | CMD-track.code.yaml |
| CMD-tu | 1 | unknown | CMD-tu.code.yaml |
| CMD-understand | 2 | markdown | CMD-understand.code.yaml |
| CMD-work | 1 | json | CMD-work.code.yaml |
| CMD-wsession | 1 | json | CMD-wsession.code.yaml |

---

## Next Steps

1. Review each candidate and determine if it represents a true contradiction
2. For confirmed contradictions, create implementation tasks to fix code
3. Update v1 documentation to reflect v2 spec decisions
4. Add tests to prevent regression
