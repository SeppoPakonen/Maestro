# Phase 4: Autotools Builder 📋 **[Planned]**

**Reference**: `docs/umk.md` Phase 4
**Duration**: 2-3 weeks
**Dependencies**: Phase 1

**Objective**: Build Autotools packages detected by `maestro repo resolve`.

## Tasks

- [ ] **4.1: Autotools Builder Implementation**
  - [ ] Create `autotools.py` module
  - [ ] Implement `configure()` method
  - [ ] Run `autoreconf` if needed
  - [ ] Support `./configure` arguments

- [ ] **4.2: Configuration Options**
  - [ ] Map Maestro config → configure flags
  - [ ] Support `--prefix`, `--enable-debug`
  - [ ] Support custom `CFLAGS`, `CXXFLAGS`
  - [ ] Support cross-compilation (host/build/target)

- [ ] **4.3: Build Execution**
  - [ ] Implement parallel make (`-j`)
  - [ ] Support VPATH builds (out-of-source)
  - [ ] Handle GNU Make and BSD Make

## Deliverables:
- Autotools builder
- Support for configure options
- Cross-compilation support

## Test Repositories:
- Various Autotools-based projects

## Test Criteria:
- Configure and build work
- Parallel builds work
- Cross-compilation works