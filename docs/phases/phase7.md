# Phase 7: CLI Integration 📋 **[Planned]**

**Reference**: `docs/umk.md` Phase 7
**Duration**: 3-4 weeks
**Dependencies**: Phases 2-6

**Objective**: Expose build functionality through `maestro make` command.

## Tasks

- [ ] **7.1: Command Structure**
  - [ ] Implement `maestro make build` (see umk.md lines 723-735)
  - [ ] Implement `maestro make clean` (lines 736-737)
  - [ ] Implement `maestro make rebuild` (lines 739-741)
  - [ ] Implement `maestro make config` (lines 743-750)
  - [ ] Implement `maestro make export` (lines 752-758)
  - [ ] Implement `maestro make methods` (line 760-761)
  - [ ] Implement `maestro make android` (lines 763-773)
  - [ ] Implement `maestro make jar` (lines 775-782)

- [ ] **7.2: Package Selection**
  - [ ] By name: `maestro make build MyPackage`
  - [ ] By pattern: `maestro make build "core/*"`
  - [ ] Main package: `maestro make build` (from current dir)
  - [ ] Build all: `maestro make build --all`

- [ ] **7.3: Method Selection**
  - [ ] Auto-detect: Use package's native build system
  - [ ] Explicit: `maestro make build --method gcc-debug`
  - [ ] U++ config: `maestro make build --config "GUI MT"`

- [ ] **7.4: Output Formatting**
  - [ ] Progress indicator for parallel builds
  - [ ] Error highlighting
  - [ ] Warning/error count summary
  - [ ] Build time reporting

- [ ] **7.5: Repository Integration**
  - [ ] Load packages from `.maestro/repo/index.json`
  - [ ] Resolve dependencies using `repo pkg tree`
  - [ ] Build in dependency order

## Deliverables:
- Complete `maestro make` CLI
- Integration with `maestro repo`
- User-friendly output

## Test Criteria:
- All CLI commands work
- Package selection works
- Output is clear and helpful