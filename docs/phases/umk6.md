# Phase umk6: Universal Build Configuration 📋 **[Planned]**

**Reference**: `docs/umk.md` Phase 6
**Duration**: 2-3 weeks
**Dependencies**: Phases 2-5.5

**Objective**: Unified configuration system for all build systems.

## Tasks

- [ ] **6.1: Unified Configuration Format**
  - [ ] Design TOML format (see umk.md lines 657-703)
  - [ ] Support compiler settings
  - [ ] Support flags and options
  - [ ] Support platform settings

- [ ] **6.2: Method Auto-Detection**
  - [ ] Detect available compilers
  - [ ] Detect build tools
  - [ ] Generate default methods
  - [ ] Store in `.maestro/methods/`

- [ ] **6.3: Method Inheritance**
  - [ ] Implement inheritance mechanism
  - [ ] Support override of inherited values
  - [ ] Validate inherited configurations

- [ ] **6.4: Per-Package Overrides**
  - [ ] Store in `.maestro/packages/<package>/method.toml`
  - [ ] Support package-specific flags
  - [ ] Support builder selection per package

## Deliverables:
- Unified build configuration
- Method auto-detection
- Method inheritance
- Per-package overrides

## Test Criteria:
- Methods detected correctly
- Inheritance works
- Package overrides apply correctly
