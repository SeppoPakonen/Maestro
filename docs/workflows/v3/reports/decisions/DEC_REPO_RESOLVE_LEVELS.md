# Decision: `repo resolve --level` Semantics

**Status**: DEFERRED
**Date**: 2025-12-27
**Context**: P1 Sprint 1.1 - Test Suite Stabilization

## Problem

There is semantic ambiguity in the `repo resolve` command regarding the `--level` parameter:

1. **Documentation references** (v1, v2, v3 runbooks) show usage like:
   - `maestro repo resolve --level lite`
   - `maestro repo resolve --level deep`

2. **Current CLI implementation** status is unclear - needs investigation

3. **Docs/CLI drift**: Without a locked-down implementation + tests, docs and CLI can easily diverge

## Options Considered

### Option 1: Preserve `--level` parameter

**Approach**:
```bash
maestro repo resolve [PATH] [--level lite|deep]
```

**Semantics**:
- `--level lite`: Minimal scan (file structure, basic metadata)
- `--level deep`: Full scan (conventions, targets, build system introspection)

**Pros**:
- Matches existing documentation
- Single command, flexible behavior
- Familiar pattern from other tools

**Cons**:
- Requires careful flag parsing implementation
- May confuse users about default behavior
- Harder to compose in scripts (flag vs subcommand)

### Option 2: Explicit command split

**Approach**:
```bash
maestro repo resolve [PATH]           # Default/lite scan
maestro repo refresh all [PATH]       # Deep scan
```

**Semantics**:
- `repo resolve`: Quick, lightweight discovery
- `repo refresh all`: Comprehensive analysis + update

**Pros**:
- Clear intent from command name
- Easier to discover (`repo --help` shows both)
- Simpler implementation (no flag complexity)
- Better for scripting/automation

**Cons**:
- Breaks backward compat if `--level` exists
- Requires updating all documentation
- More commands to maintain

### Option 3: Hybrid approach

**Approach**:
```bash
maestro repo resolve [PATH]           # Default (currently "lite")
maestro repo resolve [PATH] --deep    # Deep scan
maestro repo refresh all              # Alias for resolve --deep
```

**Pros**:
- Best of both worlds
- Flexible for users

**Cons**:
- Most complex to implement
- Semantic overlap between commands

## Decision

**DEFERRED to future sprint.**

**Rationale**:
- This is a P1 Sprint 1.1 **hardening** sprint (test stabilization), not a feature sprint
- Implementing/changing CLI semantics requires:
  - Code changes in `maestro/commands/repo.py`
  - Comprehensive tests
  - Documentation updates across v1/v2/v3
  - Migration path for existing users
- Risk vs reward: Rushing this increases chance of bugs and doc drift

**Action Items for Future Sprint**:
1. **Investigate current state**:
   - Read `maestro/commands/repo.py`
   - Check if `--level` is already implemented
   - Run `maestro repo --help` and `maestro repo resolve --help`

2. **Choose option based on**:
   - Current implementation (avoid breaking changes if possible)
   - User feedback
   - Consistency with rest of CLI

3. **Implement**:
   - Code changes
   - Tests (both CLI parsing and functional)
   - Doc updates (v3 primarily, v1/v2 for reference)

4. **Verify**:
   - Smoke test with actual repos
   - Update all runbook examples
   - Ensure ledger reflects final decision

## Current Gaps

Tracked in `docs/workflows/v3/cli/CLI_GAPS.md`:
- `repo resolve --level` semantics undefined
- No tests for `repo resolve` parameter handling
- Docs reference `--level` but implementation unclear

## References

- EX-13: `docs/workflows/v3/runbooks/examples/input_from_v2_proposed/EX-13_repo_resolve_levels_and_repoconf_targets.md`
- v1 scenarios: `docs/workflows/v1/scenario_10_repo_resolve_levels_lite_deep.md`
- Implementation: `maestro/commands/repo.py`
