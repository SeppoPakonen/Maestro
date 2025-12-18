# Phase TU5: Integration with Build System and CLI 📋 **[Planned]**

**Reference**: `docs/ast.md` Phase 5
**Duration**: 3-4 weeks
**Dependencies**: Phases TU2-TU4

**Objective**: Integrate TU/AST with existing Maestro workflows.

## Tasks

- [ ] **TU5.1: Build Configuration Integration**
  - [ ] Reuse build configuration for TU generation
  - [ ] Create `TUConfigBuilder` class
  - [ ] Extract compile context from Gradle
  - [ ] Extract compile context from CMake
  - [ ] Extract compile context from U++

- [ ] **TU5.2: `maestro tu` CLI Implementation**
  - [ ] Implement `maestro tu build [PACKAGE]`
  - [ ] Implement `maestro tu info [PACKAGE]`
  - [ ] Implement `maestro tu query [PACKAGE]`
  - [ ] Implement `maestro tu complete [PACKAGE]`
  - [ ] Implement `maestro tu references [PACKAGE]`
  - [ ] Implement `maestro tu lsp`
  - [ ] Implement `maestro tu cache` commands

- [ ] **TU5.3: Integration with `maestro repo conf`**
  - [ ] Share configuration between TU and build
  - [ ] Store config in `.maestro/tu/config/<package>.json`

- [ ] **TU5.4: Integration with `maestro build` (AI workflow)**
  - [ ] Provide AST context to AI for build fixing
  - [ ] Include visible symbols in error context
  - [ ] Include AST structure around error location

## Deliverables:
- `maestro tu` CLI with all subcommands
- Integration with build configuration
- Integration with AI build fixing workflow
- Documentation and examples

## Test Repository:
- `~/Dev/RainbowGame/trash` (Gradle project)

## Test Criteria:
- `maestro tu build` works for Gradle project
- `maestro tu complete` provides correct completions
- `maestro tu query` finds symbols
- `maestro tu lsp` works with VS Code