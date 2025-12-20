# Phase umk5: MSBuild / Visual Studio Builder 📋 **[Planned]**

**Reference**: `docs/umk.md` Phase 5
**Duration**: 2-3 weeks
**Dependencies**: Phase 1

**Objective**: Build Visual Studio projects detected by `maestro repo resolve`.

## Tasks

- [ ] **5.1: MSBuild Builder Implementation**
  - [ ] Create `msbuild.py` module
  - [ ] Implement MSBuild invocation
  - [ ] Support Configuration selection (Debug/Release)
  - [ ] Support Platform selection (Win32/x64/ARM/ARM64)

- [ ] **5.2: Project Types**
  - [ ] Support `.vcxproj` (MSBuild C++)
  - [ ] Support `.csproj` (MSBuild C#)
  - [ ] Support `.vcproj` (legacy VCBuild)

- [ ] **5.3: Solution Builds**
  - [ ] Parse `.sln` files
  - [ ] Resolve project dependencies
  - [ ] Build projects in correct order

## Deliverables:
- MSBuild builder
- Support for all configurations/platforms
- Solution-level builds

## Test Repositories:
- `~/Dev/StuntCarStadium` (Unity/Visual Studio)

## Test Criteria:
- Build Visual Studio projects
- Configuration selection works
- Solution builds work
