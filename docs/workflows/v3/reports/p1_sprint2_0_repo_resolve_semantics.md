# Repo Resolve Level Semantics - P1 Sprint 2.0

## Decision: Option 2 (Split Commands)

**Locked Semantics** as of P1 Sprint 2.0:

### Commands

- `maestro repo resolve` - **Lite scan** (default, basic package/assembly detection)
- `maestro repo refresh all` - **Deep scan** (full scan + conventions + rules analysis)

### Rationale

This design is already documented in `docs/workflows/v3/cli/SIGNATURES.md` lines 74-75:
```
- `maestro repo resolve` (lite default)
- `maestro repo refresh all` (deep resolve)
```

**Why Option 2 (NOT Option 1 with `--level` flag)**:

1. **CLI Simplicity**: Keyword-first verbs are clearer than flags
2. **Separation of Concerns**: `repo refresh all` does MORE than just deep scanning:
   - Step 1: Full repository resolve (packages + assemblies + build systems)
   - Step 2: Convention detection (auto-detect naming patterns) - Phase RF3
   - Step 3: Rules analysis (validate docs/RepoRules.md exists) - Phase RF4
3. **Already Implemented**: Both commands exist in the codebase (`maestro/commands/repo.py`)
4. **v3 CLI Philosophy**: Replace flag-based commands with keyword forms (see SUMMARY.md)

### Behavior

#### `maestro repo resolve`
- Scans current directory or `--path` for packages
- Detects assemblies across build systems (U++, CMake, Make, Maven, Gradle, etc.)
- Writes `docs/maestro/repo_model.json` and `repo_state.json`
- **Fast**: Only scans build metadata

#### `maestro repo refresh all`
- Runs full `repo resolve` scan
- Detects naming conventions (Phase RF3 - not yet implemented)
- Validates/creates `docs/RepoRules.md` (Phase RF4 - partially implemented)
- Updates global repo index (`~/.maestro/repos.json`)
- **Comprehensive**: Full repository analysis

### `--level` Flag Handling

**Current Behavior**: The `--level` flag is NOT defined in the argument parser and is automatically rejected by argparse:

```bash
$ maestro repo resolve --level deep
usage: main.py repo resolve [-h] [--path PATH] [--json] [--no-write] ...
main.py: error: unrecognized arguments: --level deep
```

**Recommended Enhancement**: Add explicit check with helpful error message (optional improvement):
```python
# In maestro/commands/repo.py handle_repo_command()
if '--level' in sys.argv:
    print_error("The --level flag is deprecated.", 2)
    print_info("Use instead:", 2)
    print_info("  maestro repo resolve       # lite scan", 3)
    print_info("  maestro repo refresh all   # deep scan", 3)
    sys.exit(1)
```

### Documentation Updates

**LEGACY_MAPPING.md**:
```markdown
| Legacy Command | New Command | Deprecation | Notes |
|---|---|---|---|
| `maestro repo resolve --level lite` | `maestro repo resolve` | Hard error | Use split commands |
| `maestro repo resolve --level deep` | `maestro repo refresh all` | Hard error | Use split commands |
```

**SIGNATURES.md**: Already correct (lines 74-75)

**TREE.md**: Already shows split commands (line 30-31)

### Testing

**Verification**:
```bash
# Lite scan
maestro repo resolve

# Deep scan
maestro repo refresh all

# --level should fail
maestro repo resolve --level deep  # error: unrecognized arguments
```

**Test Coverage**:
- Existing tests cover `repo resolve` functionality
- No new tests needed (--level rejection is automatic via argparse)
- Optional: Add explicit test for --level rejection with helpful message

## Implementation Status

✅ Commands exist and work correctly
✅ Docs (SIGNATURES.md) reflect split command design
✅ --level flag is rejected automatically
✅ No code changes needed (already correct)

## Summary

The split command design (Option 2) is already fully implemented and documented. No `--level` flag exists or should be added. The current design is clean, follows v3 CLI principles, and separates concerns appropriately.
