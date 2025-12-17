# WORKER TASK: Fix Critical Bugs in Maestro Phases 10-11

## Context
Testing revealed 2 critical bugs preventing Phases 10-11 from working correctly:
- Phase 11: U++ packages show 0 groups despite having separators
- Phase 10: Hub command code exists but CLI is not integrated

## Bug Analysis

### Bug 1: Phase 11 U++ Separator Grouping (CRITICAL)
**File**: maestro/repo/upp_parser.py
**Line**: 415
**Current Code**: `from ..main import FileGroup`
**Issue**: Circular import - FileGroup is imported from main.py but it should come from package.py
**Fix**: Change to `from .package import FileGroup`
**Impact**: U++ packages like CtrlCore.upp have separators but show 0 groups

### Bug 2: Phase 10 Hub Command Not Integrated
**Files**:
- maestro/hub/cli.py (has `create_hub_parser()` function)
- maestro/main.py (needs integration)

**Issue**: Hub module is complete but not connected to CLI
**What exists**:
- maestro/hub/cli.py with create_hub_parser() function
- maestro/hub/client.py with MaestroHub implementation

**What's missing**:
1. Import hub CLI in main.py (around line 37 where other imports are)
2. Add hub parser after line 3916 where make_parser is added
3. Add hub command handler around line 5884 where other commands are handled

**Pattern to follow** (from main.py):
```python
# Line ~37: Import
from .hub.cli import create_hub_parser, handle_hub_command

# Line ~3918: Add parser (after make_parser)
hub_parser = create_hub_parser(subparsers)

# Line ~5886: Add handler (after make command)
elif args.command == 'hub':
    handle_hub_command(args)
```

## Tasks

### Task 1: Fix U++ Separator Grouping Import
1. Open maestro/repo/upp_parser.py
2. Go to line 415
3. Change `from ..main import FileGroup` to `from .package import FileGroup`
4. Save file

### Task 2: Integrate Hub Command to CLI
1. Open maestro/main.py
2. Add import around line 37:
   ```python
   from .hub.cli import create_hub_parser, handle_hub_command
   ```
3. Add hub parser around line 3918 (after make_parser):
   ```python
   # Hub command (Universal Package Hub)
   hub_parser = create_hub_parser(subparsers)
   ```
4. Add hub command handler around line 5886:
   ```python
   elif args.command == 'hub':
       handle_hub_command(args)
   ```

### Task 3: Implement handle_hub_command if Missing
1. Check if maestro/hub/cli.py has `handle_hub_command` function
2. If missing, add it based on the existing hub command handling code in that file
3. The function should dispatch to appropriate hub subcommands

### Task 4: Test Fixes
1. Test Bug 1 fix:
   ```bash
   cd ~/Dev/ai-upp
   rm -rf .maestro
   python -m maestro repo resolve
   python -m maestro repo pkg 235 groups
   ```
   Expected: Should show groups like 'Core', 'Win32', 'X11' from CtrlCore.upp separators

2. Test Bug 2 fix:
   ```bash
   python -m maestro hub --help
   python -m maestro hub list
   ```
   Expected: Hub commands should work, not show 'invalid choice' error

### Task 5: Commit Changes
Create two commits:
1. `fix(phase-11): correct FileGroup import in UPP parser to resolve circular dependency`
2. `fix(phase-10): integrate hub command into main CLI`

## Success Criteria
- [ ] U++ packages show groups based on separators
- [ ] `maestro hub --help` works
- [ ] All hub subcommands accessible
- [ ] No import errors
- [ ] Tests pass

## Reference Files
- maestro/repo/upp_parser.py (line 415)
- maestro/main.py (lines 37, 3918, 5886)
- maestro/hub/cli.py (hub command implementation)
- maestro/repo/package.py (where FileGroup is defined)

Execute these fixes in order and test thoroughly.
