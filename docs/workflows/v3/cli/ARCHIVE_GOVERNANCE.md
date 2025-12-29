# Archive Lifecycle Governance

This document defines the policy and operational model for archiving runbooks and workflows.

## Objective

Archive old material without losing it. Archived items can be listed and restored, but default listings show only active content to keep the source of truth clean.

## Scope

### Runbooks

The archive lifecycle applies to **two independent runbook systems**:

1. **JSON Runbooks** - CLI-managed runbook data stored in `docs/maestro/runbooks/`
   - Managed via `maestro runbook add|edit|show|list`
   - Archive operations: `maestro runbook archive <ID>` and `maestro runbook restore <ARCHIVE_ID>`

2. **Markdown Runbook Examples** - Documentation files in `docs/workflows/v3/runbooks/examples/`
   - Example runbooks (EX-01 through EX-34)
   - Archive operations: `maestro runbook archive <PATH>` and `maestro runbook restore <ARCHIVE_ID>`

### Workflows

The archive lifecycle applies to **workflow files** in `docs/workflows/v3/workflows/`:

- Workflow markdown/YAML files
- Archive operations: `maestro workflow archive <PATH>` and `maestro workflow restore <ARCHIVE_ID>`

## Archive Model

### Core Principles

1. **Move, not copy** - Archive operations move items from active to archived location; items are never in both places
2. **Timestamped folders** - Archives use `YYYYMMDD` timestamped folders with mirrored path structure
3. **Separate metadata** - Archive metadata stored in index files (`archive_index.json`)
4. **Idempotency** - Archiving the same item twice fails with clear error
5. **Default active** - Default listings show only active items; `--archived` flag required to view archive
6. **Restore validation** - Restore checks original path is unoccupied before proceeding

### Archive Path Structure

```
docs/maestro/runbooks/
├── runbook-001.json          # Active runbook
├── runbook-002.json          # Active runbook
├── archived/
│   ├── 20251229/            # Timestamp folder (YYYYMMDD)
│   │   └── runbook-003.json  # Archived runbook
│   └── 20251228/            # Earlier archive
│       └── runbook-004.json
└── archive_index.json        # Archive metadata

docs/workflows/v3/runbooks/examples/
├── EX-01_basic_example.sh    # Active example
├── EX-02_another.sh          # Active example
├── archived/
│   ├── 20251229/            # Timestamp folder
│   │   └── proposed/
│   │       └── EX-35_old.sh  # Archived example (path mirrored)
│   └── 20251228/
│       └── EX-10_legacy.sh
└── archive_index.json        # Archive metadata

docs/workflows/v3/workflows/
├── WF-01.md                  # Active workflow
├── archived/
│   └── 20251229/            # Timestamp folder
│       └── WF-99.md          # Archived workflow
└── archive_index.json        # Archive metadata
```

### Archive Metadata

Each archive operation creates an `ArchiveEntry` with:

- `archive_id` - Globally unique identifier (UUID4)
- `type` - Item type ("runbook_markdown", "runbook_json", "workflow")
- `original_path` - Original file location (absolute path)
- `archived_path` - Archived file location (absolute path)
- `archived_at` - ISO timestamp
- `reason` - Optional reason for archiving (user-provided)
- `git_head` - Git HEAD at archive time (for context)
- `user` - User who performed archive (from git config or $USER)
- `runbook_id` - (Runbook JSON only) Original runbook ID

Metadata is stored in `archive_index.json` files using atomic writes (tempfile + fsync + rename).

## CLI Commands

### Runbook Archive

```bash
# List active runbooks (default)
maestro runbook list

# List archived runbooks
maestro runbook list --archived

# Filter by type
maestro runbook list --type markdown
maestro runbook list --archived --type json

# Show active runbook
maestro runbook show <ID_OR_PATH>

# Show archived runbook
maestro runbook show <ID_OR_PATH> --archived

# Archive a runbook (auto-detects markdown vs JSON)
maestro runbook archive <ID_OR_PATH> --reason "Outdated approach"

# Restore archived runbook
maestro runbook restore <ARCHIVE_ID>
```

### Workflow Archive

```bash
# List active workflows (default)
maestro workflow list

# List archived workflows
maestro workflow list --archived

# Show active workflow
maestro workflow show <PATH>

# Show archived workflow
maestro workflow show <PATH> --archived

# Archive a workflow
maestro workflow archive <PATH> --reason "Superseded by v2"

# Restore archived workflow
maestro workflow restore <ARCHIVE_ID>
```

## When to Archive

### Runbooks

Archive runbooks when:

- Runbook is superseded by a newer version
- Runbook applies to deprecated workflow/process
- Runbook is no longer applicable to current codebase
- Consolidating multiple runbooks into one

**Do NOT archive** runbooks that are:

- Still referenced in active tasks or phases
- Part of current operational playbooks
- Historical reference material still consulted regularly

### Workflows

Archive workflows when:

- Workflow is replaced by improved version
- Workflow applies to deprecated feature/system
- Workflow is experimental and no longer pursued
- Consolidating or refactoring workflows

**Do NOT archive** workflows that are:

- Referenced by current documentation
- Used in active development processes
- Required for understanding current system architecture

## Restore Process

Restore is the inverse of archive:

1. Validate archive ID exists in index
2. Check original path is unoccupied
3. Move file from archived location back to original location
4. Remove archive entry from index
5. Report restored path

If original path is occupied, restore fails with error: "Cannot restore: original path occupied: <path>. Move or rename the existing file first."

## Governance Policy

### Review Cycle

- **Quarterly Review**: Review archived items older than 90 days
- **Annual Cleanup**: Permanently delete archives older than 365 days (requires approval)
- **Exception**: Archives with `reason` containing "PRESERVE" are never auto-deleted

### Approval Requirements

- **Single Item Archive**: No approval required (operational decision)
- **Bulk Archive** (>5 items): Requires task/phase owner approval
- **Restore**: No approval required (reversible operation)
- **Permanent Deletion**: Requires two-person approval and git commit with explicit reason

### Audit Trail

All archive operations are tracked via:

1. Archive metadata in `archive_index.json` (git-tracked)
2. Git commits show file moves and index updates
3. Archive `reason` field captures operational context

## Implementation Notes

### Atomic Operations

All archive/restore operations use atomic file moves:

- `shutil.move()` on same filesystem is atomic (rename syscall)
- Index updates use atomic writes (tempfile + fsync + os.replace)
- No partial states: operation either fully succeeds or fully fails

### Test Isolation

Tests use `MAESTRO_DOCS_ROOT` environment variable to override paths:

```python
monkeypatch.setenv("MAESTRO_DOCS_ROOT", str(tmp_path))
```

This ensures tests don't pollute repository and can verify archive behavior in isolation.

### Error Handling

Archive operations fail fast with clear errors:

- `ArchiveError` - Archive operation failed
- `RestoreError` - Restore operation failed

Error messages include next steps (e.g., "Use 'maestro workflow list --archived' to view archived items").

## See Also

- [CLI Signatures](./SIGNATURES.md) - Command syntax
- [CLI Tree](./TREE.md) - Command structure
- [CLI Invariants](./INVARIANTS.md) - Archive lifecycle gates
