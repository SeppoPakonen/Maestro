# Evidence Packs

Evidence Packs are deterministic, budgeted snapshots of repository context used for AI-driven workflows like runbook generation and plan decomposition.

## Overview

An **Evidence Pack** is a portable, bounded collection of repository evidence that can be:
- **Generated deterministically**: Same repo + same rules → same pack ID
- **Consumed by AI**: Provides context for `maestro runbook resolve`, `maestro plan decompose`, etc.
- **Stored and reused**: Save once, use many times across multiple AI calls
- **Budget-enforced**: Never exceeds hard limits on files, bytes, or command executions

## Why Evidence Packs?

**Problem**: AI workflows need repo context, but naive evidence collection can:
- Produce different results on successive runs (non-deterministic)
- Collect unbounded amounts of data (prompt explosion)
- Hardcode repository-specific paths (not portable)

**Solution**: Evidence Packs provide:
- ✅ Deterministic pack IDs via content hashing
- ✅ Hard budgets (max files, max bytes, max help calls)
- ✅ Repo-agnostic collection via profiles and heuristics
- ✅ Reusable packs across multiple workflows

## Quick Start

### 1. Generate an Evidence Pack

```bash
# Auto-generate with defaults
maestro repo evidence pack

# With custom budgets
maestro repo evidence pack --max-files 30 --max-bytes 100000

# Save for reuse
maestro repo evidence pack --save
```

### 2. Use with Runbook Resolve

```bash
# Auto-generate pack on the fly (default)
maestro runbook resolve "Set up CI pipeline"

# Use saved pack
maestro repo evidence pack --save  # First, create and save
maestro runbook resolve "Set up CI pipeline" --evidence-pack pack-abc123def456

# Skip evidence collection
maestro runbook resolve "Set up CI pipeline" --no-evidence
```

### 3. Use with Plan Decompose

```bash
# Auto-generate pack on the fly (default)
maestro plan decompose "Refactor authentication module"

# Use saved pack
maestro plan decompose "Refactor module" --evidence-pack pack-abc123def456

# Skip evidence
maestro plan decompose "Refactor module" --no-evidence
```

## Evidence Pack Structure

### Metadata

```json
{
  "pack_id": "pack-2245326f9ae17fd6",
  "repo_root": "/home/user/MyProject",
  "created_at": "2026-01-02T10:47:00.343307+00:00",
  "evidence_count": 15,
  "total_bytes": 45320,
  "budget_applied": {
    "max_files": 60,
    "max_bytes": 250000,
    "max_help_calls": 6,
    "files_processed": 15,
    "help_calls_made": 2
  },
  "truncated_items": ["README.md", "docs/guide.md"],
  "skipped_items": []
}
```

### Evidence Items

Evidence is collected in three categories:

**1. Build Signatures** (deterministic order):
- `CMakeLists.txt`, `Makefile`, `configure.ac`
- `package.json`, `pyproject.toml`, `setup.py`
- `Cargo.toml`, `go.mod`, `pom.xml`
- CI files: `.github/workflows/*.yml`, `.gitlab-ci.yml`

**2. Documentation** (prioritized):
- Root `README.md` (first 3KB)
- Profile-specified directories (from `docs_hints`)
- Standard doc directories: `docs/`, `doc/`, `documentation/`

**3. CLI Help Output** (safe, with timeout):
- Binaries from profile `cli_help_candidates`
- Auto-detected from `bin/`, `build/`, `dist/`, `target/release`
- Runs `--help` with timeout (default 5s)

## Budgets and Limits

Evidence collection respects hard limits:

| Budget           | Default | Description                          |
|------------------|---------|--------------------------------------|
| `max_files`      | 60      | Maximum evidence items to collect    |
| `max_bytes`      | 250KB   | Maximum total bytes across all items |
| `max_help_calls` | 6       | Maximum CLI `--help` executions      |
| `timeout_seconds`| 5       | Timeout for each CLI help call       |

When budgets are exceeded:
- **Files**: Collection stops, remaining files added to `skipped_items`
- **Bytes**: Items truncated to fit, logged in `truncated_items`
- **Help calls**: Remaining binaries skipped

## Repo Profile Integration

Evidence Packs use **Repo Profiles** for hints and budgets.

### Create a Profile

```bash
# Auto-infer from repo structure
maestro repo profile init

# View inferred profile
maestro repo profile show
```

### Profile Structure

```json
{
  "product_name": "MyProject",
  "primary_language": "Python",
  "build_entrypoints": ["make", "python setup.py build"],
  "docs_hints": ["docs/", "README.md"],
  "cli_help_candidates": ["bin/myapp", "build/myapp"],
  "evidence_rules": {
    "max_files": 60,
    "max_bytes": 250000,
    "max_help_calls": 6,
    "timeout_seconds": 5,
    "prefer_dirs": ["docs/commands", "docs/api"],
    "exclude_patterns": ["*.pyc", "node_modules"]
  }
}
```

**Profile locations** (checked in order):
1. `docs/maestro/repo_profile.json` (primary)
2. `.maestro/profile.json` (fallback)

If no profile exists, evidence collection falls back to heuristics.

## Determinism

Evidence Packs guarantee deterministic pack IDs:

**Pack ID Formula**:
```
pack_id = hash(sorted_sources + budget_params + profile_hash)
```

**Same inputs → Same pack ID**:
- Same repository files (content and names)
- Same budget parameters
- Same profile (if used)

**Different inputs → Different pack ID**:
- Different max_files (even if actual count is same)
- Different max_bytes
- Different profile hints

### Example

```bash
# Generate pack twice with same settings
maestro repo evidence pack --max-files 10
# → pack-abc123def456

maestro repo evidence pack --max-files 10
# → pack-abc123def456 (same ID!)

# Different budget → different ID
maestro repo evidence pack --max-files 20
# → pack-xyz789ghi012 (different ID)
```

## CLI Reference

### `maestro repo evidence pack`

Generate evidence pack from repository.

**Options**:
- `--save` - Save pack to `docs/maestro/evidence_packs/`
- `--max-files N` - Override max files budget
- `--max-bytes N` - Override max bytes budget
- `--max-help-calls N` - Override max help calls budget
- `--json` - Output pack as JSON to stdout (no save)
- `-v` - Show verbose output

**Examples**:
```bash
# Quick preview
maestro repo evidence pack

# Save with custom budget
maestro repo evidence pack --save --max-files 30

# JSON output for scripting
maestro repo evidence pack --json > pack.json
```

### `maestro repo evidence list`

List all saved evidence packs.

**Options**:
- `--json` - Output as JSON

**Examples**:
```bash
maestro repo evidence list
# → pack-abc123def456
# → pack-xyz789ghi012
```

### `maestro repo evidence show <pack-id>`

Show evidence pack details.

**Options**:
- `--json` - Output as JSON
- `--show-content` - Include item content (may be large)

**Examples**:
```bash
maestro repo evidence show pack-abc123def456

# Full details with content
maestro repo evidence show pack-abc123def456 --show-content
```

## Integration with AI Workflows

### Runbook Resolve

```bash
# Method 1: Auto-generate (default)
maestro runbook resolve "Deploy to production"
# → Generates pack on the fly, uses it, discards it

# Method 2: Use saved pack (faster, reproducible)
maestro repo evidence pack --save  # Save once
PACK_ID=$(maestro repo evidence list --json | jq -r '.packs[0]')
maestro runbook resolve "Deploy to production" --evidence-pack $PACK_ID

# Method 3: No evidence (fastest, less context)
maestro runbook resolve "Deploy to production" --no-evidence
```

### Plan Decompose

```bash
# Auto-generate with domain enrichment
maestro plan decompose --domain issues "Fix open bugs"
# → Generates pack + adds issues + log scans

# Use saved pack
maestro plan decompose --evidence-pack pack-abc123 "Refactor auth"

# No evidence (freeform only)
maestro plan decompose --no-evidence "Create new feature"
```

## Storage and Cleanup

### Storage Location

```
docs/maestro/evidence_packs/
├── pack-abc123def456/
│   ├── meta.json         # Metadata (budgets, truncation info)
│   └── pack.json         # Complete pack (meta + items)
└── pack-xyz789ghi012/
    ├── meta.json
    └── pack.json
```

### Cleanup

Evidence packs are immutable once created. To clean up:

```bash
# Remove specific pack
rm -rf docs/maestro/evidence_packs/pack-abc123def456

# Remove all packs
rm -rf docs/maestro/evidence_packs/
```

## Troubleshooting

### "Pack ID changes on every run"

**Cause**: Files or timestamps in repo are changing.

**Solution**:
- Check if build artifacts are being included (add to `.gitignore`)
- Use `exclude_patterns` in repo profile to skip generated files
- Verify repo is in clean state (`git status`)

### "Evidence count is too low"

**Cause**: Budget is too restrictive or files are being excluded.

**Solution**:
```bash
# Check what's being collected
maestro repo evidence pack -v

# Increase budget
maestro repo evidence pack --max-files 100 --save

# Check profile exclude patterns
maestro repo profile show
```

### "Pack not found"

**Cause**: Pack was not saved or storage directory doesn't exist.

**Solution**:
```bash
# List available packs
maestro repo evidence list

# Ensure pack was saved
maestro repo evidence pack --save --max-files 20
```

### "Help commands timing out"

**Cause**: CLI binaries are interactive or hang.

**Solution**:
- Use repo profile to specify known-good binaries:
  ```json
  "cli_help_candidates": ["bin/app"]
  ```
- Increase timeout in profile:
  ```json
  "evidence_rules": {
    "timeout_seconds": 10
  }
  ```

## Best Practices

1. **Create a Repo Profile**
   - Improves evidence quality
   - Provides stable budgets
   - Documents repo structure

2. **Save Packs for Reuse**
   - Faster AI workflows (no re-collection)
   - Reproducible results
   - Easier debugging

3. **Use Appropriate Budgets**
   - Small repos: `--max-files 30` is often sufficient
   - Large repos: Default 60 is usually good
   - Docs-heavy: Increase `--max-bytes` to 500000

4. **Leverage -vv for Debugging**
   ```bash
   maestro runbook resolve "task" -vv
   # → Shows evidence pack summary + AI prompt/response
   ```

5. **Clean Up Old Packs**
   - Packs are immutable and can accumulate
   - Remove packs for outdated repo states

## See Also

- [maestro repo profile](./SIGNATURES.md#maestro-repo-profile) - Repo Profile management
- [maestro runbook resolve](./SIGNATURES.md#maestro-runbook-resolve) - Runbook generation
- [maestro plan decompose](./SIGNATURES.md#maestro-plan-decompose) - WorkGraph generation
- [REPO_DISCOVERY.md](./REPO_DISCOVERY.md) - Legacy discovery system (being replaced)
