# Maestro Feature Matrix

> **Notice:** TUI development has not started yet. All TUI versions listed below are either `—` or `planned`. TUI versioning will begin at `0.x` when development starts.

## Feature Comparison

| Feature | CLI Version | TUI Version | Notes |
|---------|-------------|-------------|-------|
| Rulebook execution | 0.1.0 | planned | Core functionality for applying rulebooks |
| Batch processing | 0.2.0 | 0.2.0 | Execute multiple rulebooks sequentially |
| Session management | 0.1.5 | 0.1.5 | Track execution state and history |
| Build orchestration | 0.3.0 | 0.3.0 | Coordinate complex build processes |
| Confidence scoring | 0.2.5 | planned | Evaluate reliability of automated changes |
| Interactive mode | 0.4.0 | planned | Prompt user during execution for decisions |
| Decision override workshop | — | planned | TUI wizard to safely override conversion decisions with audit trail |
| Diagnostics | 0.1.0 | planned | System health and troubleshooting tools |
| Plan generation | 0.2.0 | 0.2.0 | Visual planning interface |
| Apply/Revert operations | 0.3.5 | planned | Safe change application with rollback |
| Status monitoring | 0.2.2 | planned | Real-time execution status visualization |
| Configuration management | 0.1.8 | planned | Visual config editor |
| Task progress tracking | 0.3.2 | 0.3.2 | Progress bars and status updates |
| Log visualization | 0.2.8 | planned | Structured log display |
| Rulebook creation wizard | — | planned | Guided rulebook authoring |
| Live execution view | — | planned | Real-time process monitoring |
| Hot-reloading | — | planned | Automatic UI refresh during development |
| UPP parser | CLI v0.1.0 | — | Tolerant parser for .upp package descriptor files extracting metadata |
| Repo resolve | CLI v0.9.0 | — | Universal repository scanning with multi-build-system support (U++, CMake, Make, Autoconf, Maven, Visual Studio), auto-detection, pruning, artifact persistence, and internal package inference |
| CLI: internal package inference | CLI v0.1.0 | — | Group unknown paths into structured Maestro internal packages by top-level directory |
| Build system detection | CLI v0.2.0 | — | Auto-detect build systems: U++, CMake, GNU Make, BSD Make, Autoconf/Automake, Maven, Visual Studio |
| CMake package scanner | CLI v0.1.0 | — | Parse CMakeLists.txt files to extract targets, sources, and project metadata |
| Makefile detector | CLI v0.1.0 | — | Detect Makefile-based build systems (stub implementation) |
| Autoconf package scanner | CLI v0.2.0 | — | Parse configure.ac and Makefile.am files to extract targets (bin_PROGRAMS, lib_LTLIBRARIES) and source files with dual-path resolution |
| Visual Studio scanner | CLI v0.1.0 | — | Parse Visual Studio solution (.sln) and project files (.vcxproj, .vcproj, .csproj) to extract projects, configurations, source files, dependencies, and metadata with wildcard expansion support |
| Maven package scanner | CLI v0.1.0 | — | Parse pom.xml files to extract Maven modules (groupId:artifactId), packaging types, parent/child relationships, and source files from standard Maven directory structure (src/main/java, src/test/java) |
| Repo show | CLI v0.1.0 | — | Display persisted repository scan results from .maestro/repo/ |
| Repo pkg | CLI v0.1.0 | — | Package query commands: list, info, search, tree (with cycle detection) |
| Repo pkg: internal package integration | CLI v0.1.0 | — | Integration of internal packages into repo pkg query interface, allowing both U++ packages and internal packages in queries |
| Repo pkg: platform flag detection | CLI v0.1.0 | — | Automatic platform flag detection (LINUX, WIN32, MACOS) for conditional dependency filtering |
| Repo pkg: mainconfig support | CLI v0.1.0 | — | Support for U++ mainconfig entries and conditional dependency filtering with numbered config selection |
| Repo pkg: numbered package selection | CLI v0.1.0 | — | Numbered package selection and relative paths in repo pkg command |
| Repo pkg: conditional dependency visualization | CLI v0.1.0 | — | Display of conditional package dependencies in tree view with visual indication |
| CLI: repo index artifact | CLI v0.1 | — | Persist resolved repository model to .maestro/repo/ artifacts for reuse |
| CLI: shared repo workflow guardrails | CLI v0.1 | — | Git hygiene warnings in verbose mode and recommended development practices documentation |
| Repo resolve integration test (ai-upp) | test v0.1 | — | Integration test for U++ repository scanning |
| CLI repo workflow E2E (ai-upp) | test v0.1 | — | End-to-end test for init → repo resolve → repo show workflow |
| Run history management | CLI v0.1.0 | 0.1.0 | List, show, replay, and compare runs with baseline support |
| Conversion replay | CLI v0.1.0 | 0.1.0 | Deterministic replay of conversion runs with drift detection |
| Conversion baselines | CLI v0.1.0 | 0.1.0 | Mark runs as baselines for drift analysis |
| Conversion run comparison | CLI v0.1.0 | 0.1.0 | Compare runs to detect drift in structural, decision, and semantic aspects |

## Development Philosophy

- CLI is the mature, stable automation surface
- TUI will provide human-first interactive experience
- Feature parity is tracked but not assumed
- TUI development will focus on workflow improvements for manual operations

## Running Integration Tests

To run the U++ repository integration test:

```bash
export MAESTRO_TEST_AI_UPP_PATH="$HOME/Dev/ai-upp"
pytest -q tests/test_repo_resolve_ai_upp.py
```