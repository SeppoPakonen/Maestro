# Phase TU2: Incremental TU Builder with File Hashing 📋 **[Planned]**

**Reference**: `docs/ast.md` Phase 2
**Duration**: 3-4 weeks
**Dependencies**: Phase TU1

**Objective**: Build translation units efficiently with incremental compilation tracking.

## Tasks

- [ ] **TU2.1: File Hash Tracking**
  - [ ] Implement SHA-256-based file change detection
  - [ ] Create `FileHasher` class
  - [ ] Store hashes in `.maestro/tu/cache/file_hashes.json`
  - [ ] Detect changed files efficiently

- [ ] **TU2.2: AST Cache Management**
  - [ ] Create `.maestro/tu/cache/ast/` directory structure
  - [ ] Implement `ASTCache` class
  - [ ] Cache ASTs by file hash
  - [ ] Reuse cached ASTs for unchanged files

- [ ] **TU2.3: Translation Unit Builder**
  - [ ] Create `TUBuilder` class
  - [ ] Parse all source files in package
  - [ ] Build symbol table across files
  - [ ] Resolve cross-file references
  - [ ] Cache complete TU

- [ ] **TU2.4: Dependency Tracking**
  - [ ] Track file dependencies (includes/imports)
  - [ ] Track symbol dependencies
  - [ ] Invalidate cache when dependencies change
  - [ ] Store in `.maestro/tu/cache/ast/<hash>.meta`

## Deliverables:
- File hash tracking system
- AST cache management
- Translation unit builder
- Dependency tracking
- Incremental rebuild (only re-parse changed files)

## Test Criteria:
- Build TU for simple package (3-5 files)
- Modify one file, rebuild TU (only that file re-parsed)
- Verify cached ASTs are reused correctly
- Extract correct dependency graph