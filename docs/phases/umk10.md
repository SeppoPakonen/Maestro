# Phase umk10: Universal Hub System (MaestroHub) 📋 **[Planned]**

**Reference**: `docs/umk.md` Phase 10
**Duration**: 4-5 weeks
**Dependencies**: Phases 2-7

**Objective**: Universal package hub for automatic dependency resolution.

## Tasks

- [ ] **umk10.1: Hub Metadata Format**
  - [ ] Define JSON schema for hub registries (see umk.md lines 260-292)
  - [ ] Support UppHub compatibility
  - [ ] Multi-build-system package metadata
  - [ ] Versioning and compatibility tracking

- [ ] **umk10.2: Hub Client**
  - [ ] Create `hub/client.py` module
  - [ ] Implement `load_hub(url)`
  - [ ] Implement `search_package(name)`
  - [ ] Implement `install_nest(name)`
  - [ ] Implement `auto_resolve(workspace)`

- [ ] **umk10.3: CLI Integration** (see umk.md lines 999-1020)
  - [ ] Implement `maestro hub list`
  - [ ] Implement `maestro hub search`
  - [ ] Implement `maestro hub install`
  - [ ] Implement `maestro hub update`
  - [ ] Implement `maestro hub add`
  - [ ] Implement `maestro hub sync`
  - [ ] Implement `maestro hub info`

- [ ] **umk10.4: Auto-Resolution**
  - [ ] Detect missing packages during build
  - [ ] Search registered hubs
  - [ ] Prompt user for installation
  - [ ] Clone repositories to `~/.maestro/hub/`
  - [ ] Recursive dependency resolution

- [ ] **umk10.5: Hub Registry Management**
  - [ ] Create official MaestroHub registry
  - [ ] Import existing UppHub
  - [ ] Support custom/private hubs
  - [ ] Support organization-specific hubs

- [ ] **umk10.6: Package Path Resolution**
  - [ ] Search order: local → hub → system
  - [ ] Package name disambiguation
  - [ ] Version conflict resolution

- [ ] **umk10.7: Integration with Package Managers**
  - [ ] Conan wrapper for C++ packages
  - [ ] vcpkg integration
  - [ ] npm/pip/cargo bridge (future)

## Deliverables:
- Universal hub client
- CLI commands for hub management
- Auto-dependency resolution
- UppHub compatibility

## Test Criteria:
- Hub metadata loads correctly
- Package search works
- Auto-resolution works
- Build + hub workflow works (see umk.md lines 1250-1274)
