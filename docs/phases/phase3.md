# Phase 3: CMake Builder 📋 **[Planned]**

**Reference**: `docs/umk.md` Phase 3
**Duration**: 2-3 weeks
**Dependencies**: Phase 1

**Objective**: Build CMake packages detected by `maestro repo resolve`.

## Tasks

- [ ] **3.1: CMake Builder Implementation**
  - [ ] Create `cmake.py` module
  - [ ] Implement `configure()` method
  - [ ] Implement `build_package()` method
  - [ ] Support CMake arguments: `-DCMAKE_BUILD_TYPE`, `-DCMAKE_INSTALL_PREFIX`

- [ ] **3.2: Configuration Mapping**
  - [ ] Map Maestro config → CMake variables
  - [ ] Support Debug/Release builds
  - [ ] Support compiler selection
  - [ ] Generate toolchain files for cross-compilation

- [ ] **3.3: Target Support**
  - [ ] Build specific targets
  - [ ] Support install targets
  - [ ] Support CPack package generation

- [ ] **3.4: Generator Support**
  - [ ] Support Unix Makefiles
  - [ ] Support Ninja
  - [ ] Support Visual Studio (multi-config)
  - [ ] Support Xcode (multi-config)

## Deliverables:
- CMake builder
- Support for CMakePresets.json
- Cross-compilation support

## Test Repositories:
- `~/Dev/pedigree` (CMake-based OS)

## Test Criteria:
- Build pedigree successfully
- CMake configuration works
- Multi-config generators work