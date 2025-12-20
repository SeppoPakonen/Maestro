# Phase umk5_5: Maven Builder 📋 **[Planned]**

**Reference**: `docs/umk.md` Phase 5.5
**Duration**: 1-2 weeks
**Dependencies**: Phase 1

**Objective**: Build Maven projects detected by `maestro repo resolve`.

## Tasks

- [ ] **umk5_5.1: Maven Builder Implementation**
  - [ ] Create `maven.py` module
  - [ ] Implement `build_package()` method
  - [ ] Support Maven lifecycle phases (clean, compile, test, package, install)
  - [ ] Support parallel module builds (`-T` flag)

- [ ] **umk5_5.2: Maven Features**
  - [ ] Profile activation (`-P` flag)
  - [ ] Offline mode (`--offline`)
  - [ ] Skip tests (`-DskipTests`)
  - [ ] Property overrides (`-D` flags)

- [ ] **umk5_5.3: Multi-Module Support**
  - [ ] Reactor builds
  - [ ] Module ordering
  - [ ] Partial reactor builds

- [ ] **umk5_5.4: Packaging Types**
  - [ ] JAR packaging
  - [ ] WAR packaging
  - [ ] AAR packaging (Android)
  - [ ] POM packaging (parent POMs)
  - [ ] Native module support (JNI)

## Deliverables:
- Maven builder
- Multi-module reactor builds
- Profile and property configuration

## Test Repositories:
- `~/Dev/TopGuitar` (Maven multi-module)

## Test Criteria:
- Build TopGuitar successfully
- Reactor builds work
- Profile activation works
