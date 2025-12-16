# Maestro Feature Matrix

> **Notice:** TUI development has not started yet. All TUI versions listed below are either `—` or `planned`. TUI versioning will begin at `0.x` when development starts.

## Feature Comparison

| Feature | CLI Version | TUI Version | Notes |
|---------|-------------|-------------|-------|
| Rulebook execution | 0.1.0 | — | Core functionality for applying rulebooks |
| Batch processing | 0.2.0 | — | Execute multiple rulebooks sequentially |
| Session management | 0.1.5 | — | Track execution state and history |
| Build orchestration | 0.3.0 | — | Coordinate complex build processes |
| Confidence scoring | 0.2.5 | — | Evaluate reliability of automated changes |
| Interactive mode | 0.4.0 | — | Prompt user during execution for decisions |
| Decision override workshop | — | planned | TUI wizard to safely override conversion decisions with audit trail |
| Diagnostics | 0.1.0 | — | System health and troubleshooting tools |
| Plan generation | 0.2.0 | planned | Visual planning interface |
| Apply/Revert operations | 0.3.5 | planned | Safe change application with rollback |
| Status monitoring | 0.2.2 | planned | Real-time execution status visualization |
| Configuration management | 0.1.8 | planned | Visual config editor |
| Task progress tracking | 0.3.2 | planned | Progress bars and status updates |
| Log visualization | 0.2.8 | planned | Structured log display |
| Rulebook creation wizard | — | planned | Guided rulebook authoring |
| Live execution view | — | planned | Real-time process monitoring |
| Hot-reloading | — | planned | Automatic UI refresh during development |
| UPP parser | CLI v0.1.0 | — | Tolerant parser for .upp package descriptor files extracting metadata |
| Repo resolve | CLI v0.4.0 | — | U++ repository scanning with auto-detection, pruning, artifact persistence, and .upp parsing |
| Repo show | CLI v0.1.0 | — | Display persisted repository scan results from .maestro/repo/ |
| Repo resolve integration test (ai-upp) | test v0.1 | — | Integration test for U++ repository scanning |
| CLI repo workflow E2E (ai-upp) | test v0.1 | — | End-to-end test for init → repo resolve → repo show workflow |

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