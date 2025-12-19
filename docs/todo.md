# Maestro Development TODO

> **Planning Document**: Comprehensive roadmap for Maestro development, covering universal build system integration, Portage integration, and external dependency management.

**Last Updated**: 2025-12-18 (normalized phases and moved content to docs/phases/*.md)

---

## Table of Contents

### Legend
- ✅ **Done**: Completed and tested
- 🚧 **In Progress**: Currently being worked on
- 📋 **Planned**: Specified and scheduled
- 💡 **Proposed**: Concept stage, needs refinement

### Current Status Overview

| Track | Phase | Status | Completion |
|-------|-------|--------|------------|
| **🔥 Track/Phase/Task CLI** | | | |
| | CLI1: Markdown Data Backend | ✅ Done | 100% |
| | CLI2: Track/Phase/Task Commands | ✅ Done | 100% |
| | CLI3: AI Discussion System | ✅ Done | 100% |
| | CLI4: Settings and Configuration | ✅ Done | 100% |
| | CLI5: TUI Conversion | ✅ Done | 100% |
| **Repository Scanning** | | | |
| | U++ packages | ✅ Done | 100% |
| | CMake packages | ✅ Done | 100% |
| | Autoconf packages | ✅ Done | 100% |
| | Visual Studio packages | ✅ Done | 100% |
| | Maven packages | ✅ Done | 100% |
| | Gradle packages | ✅ Done | 100% |
| **Build System** | | | |
| | Core builder abstraction | 🚧 In Progress | 60% |
| | U++ builder | 🚧 In Progress | 40% |
| | CMake builder | 🚧 In Progress | 50% |
| | Autotools builder | 🚧 In Progress | 50% |
| | MSBuild builder | 🚧 In Progress | 40% |
| | Maven builder | 🚧 In Progress | 40% |
| | Gradle builder | 📋 Planned | 0% |
| | **Phase 12: Retroactive Fixes** | 🚧 **CURRENT** | **10%** |
| **Test Meaningfulness & Reliability** | | | |
| | TM1: Test Meaningfulness Audit | 📋 Planned | 0% |
| **TU/AST System** | | | |
| | TU1: Core AST infrastructure | ✅ Done | 100% |
| | TU2: Incremental TU builder | ✅ Done | 100% |
| | TU3: Symbol resolution | ✅ Done | 100% |
| | TU4: Auto-completion | ✅ Done | 100% |
| | TU5: Build integration | ✅ Done | 100% |
| | TU6: Code transformation | ✅ Done | 100% |
| **External Dependencies** | | | |
| | Git submodule handling | 📋 Planned | 0% |
| | Build script integration | 📋 Planned | 0% |
| | Portage integration | 💡 Proposed | 0% |
| | Host package recognition | 💡 Proposed | 0% |

---

## ✅ COMPLETED Track: Track/Phase/Task CLI and AI Discussion System

"track_id": "cli-tpt"
"priority": 0
"status": "done"
"completion": 100%

This track implements the new Track/Phase/Task command-line interface with integrated AI discussion capabilities, and migrates all data storage from `.maestro/` JSON files to `docs/` markdown files.

**Track Completed**: 2025-12-19
**All phases (CLI1-CLI5) completed and documented in docs/done.md**

**Core Concepts:**
- **TODO vs DONE**: Past and future separation throughout the entire architecture
- **Track/Phase/Task**: New hierarchy replacing the old Roadmap/Plan/Task
- **AI Discussion**: Unified discussion interface for tracks, phases, and tasks
- **Markdown Storage**: All data in human-readable, machine-parsable markdown

### Phase CLI1: Markdown Data Backend

"phase_id": "cli-tpt-1"
"status": "done"
"completion": 100

- [x] [Phase CLI1: Markdown Data Backend](phases/cli1.md) ✅ **[Done]**
  - Parser module for markdown data format
  - Writer module for markdown data format
  - Migration from JSON to markdown
  - Data validation and error recovery

### Phase CLI2: Track/Phase/Task Commands

"phase_id": "cli-tpt-2"
"status": "done"
"completion": 100

- [x] [Phase CLI2: Track/Phase/Task Commands](phases/cli2.md) ✅ **[Done]**
  - `maestro track {help,list,add,remove,<id>}` commands
  - `maestro phase {help,list,add,remove,<id>}` commands
  - `maestro task {help,list,add,remove,<id>}` commands
  - `maestro track <id> phase` navigation
  - `maestro {track,phase,task} <id> {show,edit}` subcommands

### Phase CLI3: AI Discussion System

"phase_id": "cli-tpt-3"
"status": "done"
"completion": 100

- [x] [Phase CLI3: AI Discussion System](phases/cli3.md) ✅ **[Done]**
  - Unified discussion module for all AI interactions
  - `maestro track discuss` - general track planning
  - `maestro phase <id> discuss` - phase-specific discussion
  - `maestro task <id> discuss` - task-specific discussion
  - Editor mode ($EDITOR) with # comment syntax
  - Terminal stream mode (Enter to send, Ctrl+J for newline)
  - `/done` command to finish and generate JSON actions
  - `/quit` command to cancel
  - JSON action processor for track/phase/task operations
  - Settings management: `maestro settings` for defaults

### Phase CLI4: Settings and Configuration

"phase_id": "cli-tpt-4"
"status": "done"
"completion": 100

- [x] [Phase CLI4: Settings and Configuration](phases/cli4.md) ✅ **[Done]**
  - Move all config from `~/.maestro/` to `docs/config.md`
  - `maestro settings` command
  - User preferences (editor mode, AI context, etc.)
  - Project-level settings in docs/config.md

### Phase CLI5: TUI Track/Phase/Task Conversion

"phase_id": "cli-tpt-5"
"status": "done"
"completion": 100

- [x] [Phase CLI5: TUI Conversion](phases/cli5.md) ✅ **[Done]**
  - Convert TUI to use Track/Phase/Task terminology
  - Integrate with markdown data backend
  - Update status badges and visual indicators
  - Feature parity with CLI commands
  - Deprecate or update textual-mc

---

## Primary Track: UMK Integration (Universal Build System)

"track_id": "umk"
"priority": 1
"status": "in_progress"

This track implements all phases from `docs/umk.md`, creating a universal build orchestration system.

- [ ] [Phase 1: Core Builder Abstraction](phases/phase1.md) ✅ **[Design Complete]** 📋 **[Implementation Planned]**
- [ ] [Phase 2: U++ Builder Implementation](phases/phase2.md) 📋 **[Planned]**
- [ ] [Phase 3: CMake Builder](phases/phase3.md) 📋 **[Planned]**
- [ ] [Phase 4: Autotools Builder](phases/phase4.md) 📋 **[Planned]**
- [ ] [Phase 5: MSBuild / Visual Studio Builder](phases/phase5.md) 📋 **[Planned]**
- [ ] [Phase 5.5: Maven Builder](phases/phase5_5.md) 📋 **[Planned]**
- [ ] [Phase 6: Universal Build Configuration](phases/phase6.md) 📋 **[Planned]**
- [ ] [Phase 7: CLI Integration](phases/phase7.md) 📋 **[Planned]**
- [ ] [Phase 8: Advanced Features](phases/phase8.md) 📋 **[Planned]**
- [ ] [Phase 9: TUI Integration](phases/phase9.md) 📋 **[Planned]**
- [ ] [Phase 10: Universal Hub System (MaestroHub)](phases/phase10.md) 📋 **[Planned]**
- [ ] [Phase 11: Internal Package Groups](phases/phase11.md) 📋 **[Planned]**
- [ ] [Phase 12: Retroactive Fixes and Missing Components](phases/phase12.md) 🚧 **[CURRENT - Critical]**

---

## Track: Test Meaningfulness & Reliability

"track_id": "test-meaningfulness"
"priority": 2
"status": "planned"

This track focuses on evaluating and improving the meaningfulness and reliability of the test suite so failures reflect real regressions, not environment noise.

### Phase TM1: Test Meaningfulness Audit

"phase_id": "test-meaningfulness-1"
"status": "planned"
"completion": 0

- [ ] [Phase TM1: Test Meaningfulness Audit](phases/tm1.md) 📋 **[Planned]**
  - Categorize failing tests by value and stability
  - Decide which tests to fix, update, or retire

---

## TU/AST Track: Translation Unit and AST Generation

This track implements Translation Unit (TU) and Abstract Syntax Tree (AST) generation for advanced code analysis, auto-completion, and code transformation.

- [x] [Phase TU1: Core AST Infrastructure](phases/tu1.md) ✅ **[Done - 2025-12-19]**
- [x] [Phase TU2: Incremental TU Builder with File Hashing](phases/tu2.md) ✅ **[Done - 2025-12-19]**
- [x] [Phase TU3: Symbol Resolution and Indexing](phases/tu3.md) ✅ **[Done - 2025-12-19]**
- [x] [Phase TU4: Auto-Completion Engine](phases/tu4.md) ✅ **[Done - 2025-12-19]**
- [x] [Phase TU5: Integration with Build System and CLI](phases/tu5.md) ✅ **[Done - 2025-12-19]**
- [ ] [Phase TU6: Code Transformation and Convention Enforcement](phases/tu6.md) 📋 **[Planned]**

---

## Extended Track: Additional Build Systems

This track extends repository scanning and build support to additional ecosystems.

- [ ] [Phase E1: Python Project Support](phases/e1.md) 📋 **[Planned]**
- [ ] [Phase E2: Node.js / npm Project Support](phases/e2.md) 📋 **[Planned]**
- [ ] [Phase E3: Go Project Support](phases/e3.md) 📋 **[Planned]**
- [ ] [Phase E4: Pedigree pup Package System Support](phases/e4.md) 📋 **[Planned]**
- [ ] [Phase E5: Additional Build Systems (Future)](phases/e5.md) 💡 **[Proposed]**

---

## Assemblies and Packages Track

This track handles the organization of packages into logical assemblies that represent cohesive units of code.

- [x] [Phase AS1: Assemblies in Maestro Repository System](phases/as1.md) ✅ **[Done - 2025-12-19]**

## Advanced Track: External Dependencies and Portage Integration

This track handles external dependencies, build scripts, and Gentoo Portage integration.

- [ ] [Phase A1: Git Submodule and Build Script Handling](phases/a1.md) 💡 **[Proposed]**
- [ ] [Phase A2: Gentoo Portage Integration - Design](phases/a2.md) 💡 **[Proposed]**
- [ ] [Phase A3: Portage Integration - Implementation](phases/a3.md) 💡 **[Proposed]**
- [ ] [Phase A4: Host System Package Recognition](phases/a4.md) 💡 **[Proposed]**
- [ ] [Phase A5: Portage Superset Integration](phases/a5.md) 💡 **[Proposed]**
- [ ] [Phase A6: External Dependency Workflow](phases/a6.md) 💡 **[Proposed]**

---

## Integration and Testing

- [ ] [Phase IT1: Integration Testing](phases/it1.md)
- [ ] [Phase IT2: Notes and Considerations](phases/it2.md)
- [ ] [Phase IT3: Next Steps](phases/it3.md)

---

**Document Status**: Planning phase complete, ready for implementation.
**Last Review**: 2025-12-18
