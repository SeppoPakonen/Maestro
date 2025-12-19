# CLI5 TUI Conversion Audit Task

## Context

The Maestro project has completed phases CLI1-CLI4, which introduced a new Track/Phase/Task terminology system to replace the old Roadmap/Plan/Task terminology. The data has been migrated to markdown files in `docs/`.

## Your Task

Perform a comprehensive audit of the TUI (Terminal User Interface) code to prepare for the CLI5 conversion. This audit should:

### 1. Terminology Analysis

Search all TUI code for instances of the old terminology:
- "roadmap" → should become "track"
- "plan" → should become "phase"
- "task" → stays as "task"

For each file that needs changes:
- List the file path
- Count how many instances need updating
- Categorize by type: UI text, variable names, function names, class names, comments

### 2. Data Backend Analysis

Analyze how the TUI currently loads data:
- Find all locations that read from `.maestro/*.json` files
- Find all locations that call old data access functions
- Identify what new markdown parser functions they should use instead

### 3. File Structure Analysis

Create a comprehensive list of all TUI files categorized by:
- **Core TUI files**: Main app, entry points
- **Screen files**: Individual screens (plans, tasks, sessions, etc.)
- **Pane files**: Pane components
- **Widget files**: Reusable widgets
- **Utility files**: Helper functions

### 4. Create Detailed Implementation Plan

For each file that needs changes, create a detailed task description:
- What terminology needs to be changed
- What data access needs to be updated
- Estimated complexity (trivial, easy, medium, hard)
- Dependencies on other files

### 5. Output Format

Create a comprehensive report in markdown format with:

1. **Executive Summary**: High-level overview of the scope
2. **File-by-File Analysis**: Detailed breakdown of each file
3. **Implementation Sequence**: Recommended order of changes
4. **Risk Assessment**: Potential issues and how to mitigate them
5. **Test Strategy**: How to verify the changes work

## Files to Analyze

Focus on these directories:
- `maestro/tui/`
- `maestro/tui_mc2/`

## Additional Context

The new data backend functions are in `maestro/data/` and include:
- `parse_todo_md()` - parses docs/todo.md for track/phase data
- `parse_config_md()` - parses docs/config.md for configuration
- `parse_phase_md()` - parses individual phase markdown files

The new terminology:
- **Track**: Top-level collection of related phases (was "roadmap")
- **Phase**: Major milestone with multiple tasks (was "plan")
- **Task**: Individual work item (stays same)

## Deliverable

Create a single comprehensive markdown file called `cli5_audit_report.md` that can be used to guide the implementation.
