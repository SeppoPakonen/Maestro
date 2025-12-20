# Phase umk1: Core Builder Abstraction ✅ **[Design Complete]** 📋 **[Implementation Planned]**

**Reference**: `docs/umk.md` Phase 1
**Duration**: 2-3 weeks
**Dependencies**: None

**Objective**: Create Python abstraction layer for universal build system support.

## Tasks

- [ ] **umk1.1: Module Structure**
  - [ ] Create `maestro/builders/` module
  - [ ] Implement `base.py` with abstract `Builder` base class
  - [ ] Define builder interface methods:
    - `build_package(package, config)`
    - `link(linkfiles, linkoptions)`
    - `clean_package(package)`
    - `get_target_ext()`
  - [ ] Add type hints and docstrings

- [ ] **umk1.2: Build Method Configuration**
  - [ ] Design TOML/JSON format for build methods (see umk.md lines 657-703)
  - [ ] Implement method storage in `.maestro/methods/`
  - [ ] Create method parser and validator
  - [ ] Support method inheritance
  - [ ] Implement method auto-detection for system compilers

- [ ] **umk1.3: Host Abstraction**
  - [ ] Create `host.py` module
  - [ ] Support local builds
  - [ ] Design interface for remote builds (future)
  - [ ] Design interface for Docker builds (future)

- [ ] **umk1.4: Console Process Management**
  - [ ] Create `console.py` module
  - [ ] Implement parallel job execution using `multiprocessing`
  - [ ] Add process output capture and streaming
  - [ ] Implement error tracking and reporting
  - [ ] Add Ctrl+C handling and cleanup

- [ ] **umk1.5: Configuration System**
  - [ ] Create `config.py` module
  - [ ] Define `BuildConfig` dataclass
  - [ ] Implement platform detection
  - [ ] Support per-package overrides

## Deliverables:
- Python builder framework with abstract base class
- Build method configuration system
- Host abstraction
- Console process management

## Test Criteria:
- Unit tests for builder interface
- Config parsing tests
- Process management tests
