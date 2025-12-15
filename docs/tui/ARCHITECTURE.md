# Maestro TUI Architecture

## Separation Contract

The Maestro project consists of two separate frontends that share common backend/domain logic:

```
CLI ─┐
     ├── backend / domain / orchestration
TUI ─┘
```

### Core Principles

1. **CLI and TUI are separate frontends**
   - Each serves different user needs and use cases
   - They remain independently maintainable

2. **Shared backend/domain modules only**
   - Both frontends consume the same core logic
   - No cross-dependencies between CLI and TUI

3. **TUI must never:**
   - Call the CLI binary (no subprocess to maestro.py)
   - Parse CLI text output
   - Depend on CLI flags/argument parsing
   - Shell out to command-line functionality

4. **CLI remains:**
   - Scriptable and automatable
   - Stable with backward compatibility
   - Optimized for automation and AI tools
   - Primary interface for CI/CD and programmatic usage

5. **TUI remains:**
   - Human-first interactive interface
   - Allowed to evolve UX rapidly
   - Focused on real-time feedback and workflow
   - Accessible for manual operations and debugging

## Framework Choice: Textual

We use [Textual](https://textual.textualize.io/) as the TUI framework because:

- **Rich interactive components**: Provides buttons, trees, tables, and custom widgets
- **Event-driven architecture**: Matches the async nature of Maestro orchestration
- **Cross-platform**: Works consistently across Unix systems
- **Modern Python**: Clean integration with asyncio and type hints

**What Textual is NOT for:**
- Replacing CLI automation capabilities
- Scripting or batch operations
- Integration with external automation tools

## Non-Goals

The TUI will NOT attempt to:

- Replace shell scripting or command-line automation
- Become the primary interface for CI/CD pipelines
- Mirror every advanced CLI flag and option
- Support headless or non-interactive operation
- Provide the same level of granular control as CLI arguments
- Serve as an API layer for external tools

## Dependency Management

TUI-specific dependencies are managed separately from core Maestro logic:
- Dependencies pinned to specific versions
- Clear separation in requirements or setup.py
- Independent upgrade cycles from core logic

## UI Facade Contract

The TUI communicates with backend services exclusively through a dedicated facade:

- **Only structured data**: Dicts, lists, dataclasses (no formatted strings)
- **Python exceptions**: Machine-meaningful error types (no user-facing prose)
- **Read-only operations**: Initial implementation supports viewing only
- **Direct access**: Reads session files, build targets, and plan artifacts directly
- **No CLI shelling**: Never invokes maestro CLI or parses its output

This ensures stability and predictable data exchange between TUI and backend.