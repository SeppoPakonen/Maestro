# Ledger Candidates — Spec→Code Contradictions

This report lists contradictions detected between v2 specification and observed v1 code behavior.
Generated automatically from command IR extraction.

**Total candidates:** 38

---

## 1. Storage Backend Violations (REPO_TRUTH_FORMAT_IS_JSON)

**Count:** 12

Commands using markdown or mixed storage backend instead of JSON:

### CMD-discuss

- **Storage backend:** markdown
- **File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-discuss.code.yaml`
- **Invariant violated:** REPO_TRUTH_FORMAT_IS_JSON
- **Fix required:** Replace markdown persistence with JSON in command implementation

### CMD-init

- **Storage backend:** markdown
- **File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-init.code.yaml`
- **Invariant violated:** REPO_TRUTH_FORMAT_IS_JSON
- **Fix required:** Replace markdown persistence with JSON in command implementation

### CMD-issues

- **Storage backend:** markdown
- **File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-issues.code.yaml`
- **Invariant violated:** REPO_TRUTH_FORMAT_IS_JSON
- **Fix required:** Replace markdown persistence with JSON in command implementation

### CMD-ops

- **Storage backend:** mixed
- **File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-ops.code.yaml`
- **Invariant violated:** REPO_TRUTH_FORMAT_IS_JSON
- **Fix required:** Replace markdown persistence with JSON in command implementation

### CMD-phase

- **Storage backend:** mixed
- **File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-phase.code.yaml`
- **Invariant violated:** REPO_TRUTH_FORMAT_IS_JSON
- **Fix required:** Replace markdown persistence with JSON in command implementation

### CMD-plan

- **Storage backend:** markdown
- **File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-plan.code.yaml`
- **Invariant violated:** REPO_TRUTH_FORMAT_IS_JSON
- **Fix required:** Replace markdown persistence with JSON in command implementation

### CMD-settings

- **Storage backend:** mixed
- **File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-settings.code.yaml`
- **Invariant violated:** REPO_TRUTH_FORMAT_IS_JSON
- **Fix required:** Replace markdown persistence with JSON in command implementation

### CMD-solutions

- **Storage backend:** markdown
- **File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-solutions.code.yaml`
- **Invariant violated:** REPO_TRUTH_FORMAT_IS_JSON
- **Fix required:** Replace markdown persistence with JSON in command implementation

### CMD-task

- **Storage backend:** mixed
- **File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-task.code.yaml`
- **Invariant violated:** REPO_TRUTH_FORMAT_IS_JSON
- **Fix required:** Replace markdown persistence with JSON in command implementation

### CMD-track

- **Storage backend:** mixed
- **File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-track.code.yaml`
- **Invariant violated:** REPO_TRUTH_FORMAT_IS_JSON
- **Fix required:** Replace markdown persistence with JSON in command implementation

### CMD-understand

- **Storage backend:** markdown
- **File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-understand.code.yaml`
- **Invariant violated:** REPO_TRUTH_FORMAT_IS_JSON
- **Fix required:** Replace markdown persistence with JSON in command implementation

### CMD-work

- **Storage backend:** mixed
- **File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-work.code.yaml`
- **Invariant violated:** REPO_TRUTH_FORMAT_IS_JSON
- **Fix required:** Replace markdown persistence with JSON in command implementation

---

## 2. Explicit Ledger Hints from Code Layer

**Count:** 26

Hints explicitly flagged during extraction:

### CMD-ai

**File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-ai.code.yaml`

- Observed legacy qwen-old command paths in cmd_ai deep flow; these represent deprecated functionality that should be removed in v2.

### CMD-convert

**File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-convert.code.yaml`

- Observed .maestro/convert/ directory usage in cmd_convert deep flow; violates FORBID_REPO_DOT_MAESTRO invariant; migrate to ./docs/maestro/convert/ and update docs/tests.

### CMD-discuss

**File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-discuss.code.yaml`

- Observed DataMarkdown persistence in cmd_discuss deep flow; v2 repo truth uses JSON. Replace/remove DataMarkdown codepaths and update docs/tests.

### CMD-init

**File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-init.code.yaml`

- Observed DataMarkdown persistence in cmd_init deep flow; v2 repo truth uses JSON. Replace/remove DataMarkdown codepaths and update docs/tests.

### CMD-issues

**File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-issues.code.yaml`

- Observed DataMarkdown persistence in cmd_issues deep flow; v2 repo truth uses JSON. Replace/remove DataMarkdown codepaths and update docs/tests.
- Observed .maestro directory usage in _find_repo_root; v2 spec uses ./docs/maestro/ for repo truth. This may violate FORBID_REPO_DOT_MAESTRO invariant.
- Observed markdown file persistence for repo truth in issues flow; v2 spec requires JSON. This violates REPO_TRUTH_FORMAT_IS_JSON invariant.

### CMD-log

**File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-log.code.yaml`

- Observed JSON persistence in cmd_log deep flow with session.json and other JSON files; aligns with v2 repo truth using JSON.

### CMD-ops

**File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-ops.code.yaml`

- Observed DataMarkdown persistence in cmd_ops deep flow; v2 repo truth uses JSON. Replace/remove DataMarkdown codepaths and update docs/tests.
- Observed .maestro directory usage in ops command flow; violates FORBID_REPO_DOT_MAESTRO invariant; migrate to ./docs/maestro/ for repo truth.

### CMD-phase

**File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-phase.code.yaml`

- Observed DataMarkdown persistence in cmd_phase deep flow; v2 repo truth uses JSON. Replace/remove DataMarkdown codepaths and update docs/tests.

### CMD-plan

**File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-plan.code.yaml`

- Observed DataMarkdown persistence in cmd_plan deep flow; v2 repo truth uses JSON. Replace/remove DataMarkdown codepaths and update docs/tests.

### CMD-repo

**File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-repo.code.yaml`

- Observed .maestro directory usage in cmd_repo deep flow; violates FORBID_REPO_DOT_MAESTRO invariant; migrate to ./docs/maestro/
- Observed JSON persistence in cmd_repo deep flow; confirms REPO_TRUTH_FORMAT_IS_JSON invariant

### CMD-resume

**File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-resume.code.yaml`

- Observed JSON persistence in docs/sessions/<name>/ directory structure; aligns with REPO_TRUTH_FORMAT_IS_JSON invariant

### CMD-root

**File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-root.code.yaml`

- Observed .maestro directory usage for conversations in cmd_root deep flow; v2 spec has FORBID_REPO_DOT_MAESTRO invariant. Conversation transcripts should be stored in ./docs/maestro/conversations/ instead.

### CMD-rules

**File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-rules.code.yaml`

- Observed rules.txt persistence as plain text file in session directory; verify this aligns with intended storage contract and doesn't conflict with JSON-only repo truth requirements

### CMD-solutions

**File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-solutions.code.yaml`

- Observed markdown persistence in cmd_solutions deep flow; v2 repo truth uses JSON. Replace/remove markdown codepaths and update docs/tests.

### CMD-task

**File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-task.code.yaml`

- Observed DataMarkdown persistence in cmd_task deep flow; v2 repo truth uses JSON. Replace/remove DataMarkdown codepaths and update docs/tests.
- Mentions .maestro directory usage which contradicts FORBID_REPO_DOT_MAESTRO invariant - needs migration to ./docs/maestro/
- Shows mixed markdown/JSON persistence model which contradicts REPO_TRUTH_FORMAT_IS_JSON invariant

### CMD-track

**File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-track.code.yaml`

- Observed DataMarkdown persistence in cmd_track deep flow; v2 repo truth uses JSON. Replace/remove DataMarkdown codepaths and update docs/tests.
- Observed ./.maestro directory usage in track command flow; contradicts FORBID_REPO_DOT_MAESTRO invariant. Migrate to ./docs/maestro/ for repo truth.

### CMD-understand

**File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-understand.code.yaml`

- Observed DataMarkdown persistence in cmd_understand deep flow; v2 repo truth uses JSON. Replace/remove DataMarkdown codepaths and update docs/tests.

### CMD-work

**File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-work.code.yaml`

- Observed DataMarkdown persistence in cmd_work deep flow; v2 repo truth uses JSON. Replace/remove DataMarkdown codepaths and update docs/tests.

### CMD-wsession

**File:** `/common/active/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd/CMD-wsession.code.yaml`

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
| CMD-issues | 4 | markdown | CMD-issues.code.yaml |
| CMD-log | 1 | json | CMD-log.code.yaml |
| CMD-ops | 3 | mixed | CMD-ops.code.yaml |
| CMD-phase | 2 | mixed | CMD-phase.code.yaml |
| CMD-plan | 2 | markdown | CMD-plan.code.yaml |
| CMD-repo | 2 | json | CMD-repo.code.yaml |
| CMD-resume | 1 | json | CMD-resume.code.yaml |
| CMD-root | 1 | json | CMD-root.code.yaml |
| CMD-rules | 1 | unknown | CMD-rules.code.yaml |
| CMD-session | 0 | json | — |
| CMD-settings | 1 | mixed | CMD-settings.code.yaml |
| CMD-solutions | 2 | markdown | CMD-solutions.code.yaml |
| CMD-task | 4 | mixed | CMD-task.code.yaml |
| CMD-track | 3 | mixed | CMD-track.code.yaml |
| CMD-tu | 0 | unknown | — |
| CMD-understand | 2 | markdown | CMD-understand.code.yaml |
| CMD-work | 2 | mixed | CMD-work.code.yaml |
| CMD-workflow | 0 | json | — |
| CMD-wsession | 1 | json | CMD-wsession.code.yaml |

---

## Next Steps

1. Review each candidate and determine if it represents a true contradiction
2. For confirmed contradictions, create implementation tasks to fix code
3. Update v1 documentation to reflect v2 spec decisions
4. Add tests to prevent regression
