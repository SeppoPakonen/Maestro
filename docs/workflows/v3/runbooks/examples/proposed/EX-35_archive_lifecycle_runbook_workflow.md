# EX-35: Archive Lifecycle for Runbooks and Workflows

**Scope**: Demonstrate archive/restore operations for runbooks (JSON and markdown) and workflows
**Outcome**: Old material archived without loss; default listings show only active content

---

## Preconditions

- Repo truth is JSON under `./docs/maestro/**`
- Repo initialized
- Sample runbooks and workflows exist for archiving

## Gates / IDs / Stores

- Gates: `REPO_TRUTH_FORMAT_IS_JSON`, `ARCHIVE_IDEMPOTENCY`, `ARCHIVE_DEFAULT_LISTING`, `RESTORE_PATH_OCCUPIED`
- IDs/cookies/resume tokens: Archive IDs (UUID4), workflow paths
- Stores: `REPO_TRUTH_DOCS_MAESTRO` (runbooks, workflows, archive indices)

---

## Runbook Steps

| Step | Command | Intent | Expected | Gates | Stores |
|------|---------|--------|----------|-------|--------|
| 1 | `maestro init` | Initialize repo truth | Repo truth created | `REPO_TRUTH_FORMAT_IS_JSON` | `REPO_TRUTH_DOCS_MAESTRO` |
| 2 | `maestro runbook list` | List active runbooks | Shows only active items | none | `REPO_TRUTH_DOCS_MAESTRO` |
| 3 | `maestro runbook archive RB-001 --reason "..."` | Archive JSON runbook by ID | Moved to archived/YYYYMMDD/ | `ARCHIVE_IDEMPOTENCY` | `REPO_TRUTH_DOCS_MAESTRO` |
| 4 | `maestro runbook archive <PATH> --reason "..."` | Archive markdown example | Moved to archived/YYYYMMDD/ | `ARCHIVE_IDEMPOTENCY` | `REPO_TRUTH_DOCS_MAESTRO` |
| 5 | `maestro runbook list` | List active after archive | Archived items excluded | `ARCHIVE_DEFAULT_LISTING` | `REPO_TRUTH_DOCS_MAESTRO` |
| 6 | `maestro runbook list --archived` | List archived items | Shows archived with IDs | none | `REPO_TRUTH_DOCS_MAESTRO` |
| 7 | `maestro runbook list --archived --type json` | Filter archived by type | Shows only JSON runbooks | none | `REPO_TRUTH_DOCS_MAESTRO` |
| 8 | `maestro runbook show RB-001 --archived` | Show archived runbook | Displays content + metadata | none | `REPO_TRUTH_DOCS_MAESTRO` |
| 9 | `maestro runbook archive RB-001` | Archive duplicate (should fail) | Error: already archived | `ARCHIVE_IDEMPOTENCY` | `REPO_TRUTH_DOCS_MAESTRO` |
| 10 | `maestro runbook restore <ARCHIVE_ID>` | Restore archived runbook | Moved back to original path | `RESTORE_PATH_OCCUPIED` | `REPO_TRUTH_DOCS_MAESTRO` |
| 11 | `maestro workflow list` | List active workflows | Shows only active | `ARCHIVE_DEFAULT_LISTING` | `REPO_TRUTH_DOCS_MAESTRO` |
| 12 | `maestro workflow archive <PATH> --reason "..."` | Archive workflow file | Moved to archived/YYYYMMDD/ | `ARCHIVE_IDEMPOTENCY` | `REPO_TRUTH_DOCS_MAESTRO` |
| 13 | `maestro workflow list --archived` | List archived workflows | Shows archived with IDs | none | `REPO_TRUTH_DOCS_MAESTRO` |
| 14 | `maestro workflow show <PATH> --archived` | Show archived workflow | Displays content + metadata | none | `REPO_TRUTH_DOCS_MAESTRO` |
| 15 | `maestro workflow restore <ARCHIVE_ID>` | Restore workflow | Moved back to original path | `RESTORE_PATH_OCCUPIED` | `REPO_TRUTH_DOCS_MAESTRO` |
| 16 | `maestro workflow list` | Verify restore | Restored workflow in active list | none | `REPO_TRUTH_DOCS_MAESTRO` |

---

## AI Perspective (Heuristic)

- Archive old material to keep active listings clean while preserving history
- Use timestamped folders (YYYYMMDD) so multiple archives of same item are preserved
- Move operations (not copy) ensure item is active OR archived, never both
- Archive metadata tracks reason, user, git HEAD for governance audit trail
- Default listings exclude archived items; explicit `--archived` flag required to view
- Restore validates original path unoccupied before moving file back

---

## Outcomes

### Outcome A: Archive Success

- Item moved from active location to `archived/YYYYMMDD/<relative_path>`
- Archive entry added to `archive_index.json` with UUID4 archive ID
- Default listings no longer show archived item
- Archive metadata preserved: reason, timestamp, user, git context

### Outcome B: Archive Idempotency Failure

- Attempting to archive already-archived item fails with error
- Error message shows archive ID and suggests using `list --archived`
- No duplicate archive entries created

### Outcome C: Restore Success

- Item moved from `archived/YYYYMMDD/<path>` back to original location
- Archive entry removed from `archive_index.json`
- Item reappears in default active listings

### Outcome D: Restore Occupied Path Failure

- Restore fails if original path already exists
- Error message suggests moving or renaming existing file first
- Archive remains intact; no partial state

---

## CLI Gaps / TODOs

None - all commands fully implemented.

---

## Trace (YAML)

```yaml
trace:
  example: EX-35
  steps:
    - step: init_repo
      command: "maestro init"
      gates: [REPO_TRUTH_FORMAT_IS_JSON]
      stores: [REPO_TRUTH_DOCS_MAESTRO]
    - step: list_active_runbooks
      command: "maestro runbook list"
      gates: []
      stores: [REPO_TRUTH_DOCS_MAESTRO]
    - step: archive_json_runbook
      command: "maestro runbook archive RB-001 --reason 'Superseded by v2'"
      gates: [ARCHIVE_IDEMPOTENCY]
      stores: [REPO_TRUTH_DOCS_MAESTRO]
    - step: archive_markdown_runbook
      command: "maestro runbook archive docs/workflows/v3/runbooks/examples/EX-01_old_example.sh --reason 'Outdated approach'"
      gates: [ARCHIVE_IDEMPOTENCY]
      stores: [REPO_TRUTH_DOCS_MAESTRO]
    - step: verify_active_listing
      command: "maestro runbook list"
      gates: [ARCHIVE_DEFAULT_LISTING]
      stores: [REPO_TRUTH_DOCS_MAESTRO]
    - step: list_archived_runbooks
      command: "maestro runbook list --archived"
      gates: []
      stores: [REPO_TRUTH_DOCS_MAESTRO]
    - step: filter_archived_by_type
      command: "maestro runbook list --archived --type json"
      gates: []
      stores: [REPO_TRUTH_DOCS_MAESTRO]
    - step: show_archived_runbook
      command: "maestro runbook show RB-001 --archived"
      gates: []
      stores: [REPO_TRUTH_DOCS_MAESTRO]
    - step: test_idempotency
      command: "maestro runbook archive RB-001 --reason 'Testing idempotency'"
      gates: [ARCHIVE_IDEMPOTENCY]
      stores: [REPO_TRUTH_DOCS_MAESTRO]
      expected: error
    - step: restore_runbook
      command: "maestro runbook restore <ARCHIVE_ID>"
      gates: [RESTORE_PATH_OCCUPIED]
      stores: [REPO_TRUTH_DOCS_MAESTRO]
    - step: list_active_workflows
      command: "maestro workflow list"
      gates: [ARCHIVE_DEFAULT_LISTING]
      stores: [REPO_TRUTH_DOCS_MAESTRO]
    - step: archive_workflow
      command: "maestro workflow archive docs/workflows/v3/workflows/WF-OLD.md --reason 'Legacy workflow'"
      gates: [ARCHIVE_IDEMPOTENCY]
      stores: [REPO_TRUTH_DOCS_MAESTRO]
    - step: list_archived_workflows
      command: "maestro workflow list --archived"
      gates: []
      stores: [REPO_TRUTH_DOCS_MAESTRO]
    - step: show_archived_workflow
      command: "maestro workflow show docs/workflows/v3/workflows/WF-OLD.md --archived"
      gates: []
      stores: [REPO_TRUTH_DOCS_MAESTRO]
    - step: restore_workflow
      command: "maestro workflow restore <WORKFLOW_ARCHIVE_ID>"
      gates: [RESTORE_PATH_OCCUPIED]
      stores: [REPO_TRUTH_DOCS_MAESTRO]
    - step: verify_workflow_restore
      command: "maestro workflow list"
      gates: []
      stores: [REPO_TRUTH_DOCS_MAESTRO]
  stores_considered:
    - REPO_TRUTH_DOCS_MAESTRO
  gates_considered:
    - REPO_TRUTH_FORMAT_IS_JSON
    - ARCHIVE_IDEMPOTENCY
    - ARCHIVE_DEFAULT_LISTING
    - RESTORE_PATH_OCCUPIED
```

---

## Archive Governance Notes

This runbook demonstrates the complete archive lifecycle governance model:

1. **Move, not copy**: Items are moved to archive, ensuring they exist in only one location
2. **Timestamped folders**: Archives use YYYYMMDD format allowing multiple archives over time
3. **Metadata tracking**: Archive index stores reason, user, timestamp, git HEAD
4. **Idempotency**: Attempting to archive the same item twice fails explicitly
5. **Default active**: Listings show only active content unless `--archived` flag provided
6. **Restore validation**: Restore checks original path unoccupied before proceeding
7. **Dual system support**: Runbooks support both JSON (CLI-managed) and markdown examples
8. **Atomic operations**: All archive/restore use atomic file moves and index updates

See [ARCHIVE_GOVERNANCE.md](../../cli/ARCHIVE_GOVERNANCE.md) for full policy details.
