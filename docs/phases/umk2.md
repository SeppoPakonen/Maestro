# Phase umk2: U++ Builder Implementation 📋 **[Planned]**

**Reference**: `docs/umk.md` Phase 2
**Duration**: 4-6 weeks
**Dependencies**: Phase 1

**Objective**: Build U++ packages using umk logic ported to Python.

## Tasks

- [ ] **umk2.1: U++ Package Parser**
  - [ ] Extend existing `.upp` file parsing
  - [ ] Extract `uses`, `files`, `flags`, `mainconfig`
  - [ ] Resolve conditional options based on build flags
  - [ ] Create `Package` dataclass

- [ ] **umk2.2: Workspace Dependency Resolver**
  - [ ] Create `workspace.py` module
  - [ ] Port `Workspace::Scan()` logic
  - [ ] Build dependency graph
  - [ ] Determine build order (topological sort)
  - [ ] Detect circular dependencies

- [ ] **umk2.3: GCC/Clang Builder**
  - [ ] Create `gcc.py` module
  - [ ] Implement command-line construction
  - [ ] Add include path resolution
  - [ ] Add define/flag handling
  - [ ] Implement source compilation
  - [ ] Implement linking (executable, shared, static)

- [ ] **umk2.4: MSVC Builder**
  - [ ] Create `msvc.py` module
  - [ ] Port MSVC-specific logic
  - [ ] Implement cl.exe invocation
  - [ ] Implement link.exe invocation

- [ ] **umk2.5: Incremental Build Support**
  - [ ] Create `ppinfo.py` for dependency tracking
  - [ ] Implement file timestamp comparison
  - [ ] Create build cache in `.maestro/cache/`
  - [ ] Add header dependency tracking

- [ ] **umk2.6: Build Cache Management**
  - [ ] Create `cache.py` module
  - [ ] Store file-level dependencies (see umk.md lines 1103-1113)
  - [ ] Implement cache invalidation
  - [ ] Add cache statistics

## Deliverables:
- Complete U++ builder
- Support for all mainconfig options
- Parallel build support
- Incremental builds with dependency tracking

## Test Repositories:
- `~/Dev/ai-upp` (U++ framework)
- U++ sample applications

## Test Criteria:
- Build ai-upp packages successfully
- Incremental builds work correctly
- Parallel builds produce correct output
