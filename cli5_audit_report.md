# CLI5 TUI Conversion Audit Report

## Executive Summary

This report provides a comprehensive analysis of the Terminal User Interface (TUI) codebase for the CLI5 conversion from the old "Roadmap/Plan/Task" terminology to the new "Track/Phase/Task" terminology. The audit covers both `maestro/tui` and `maestro/tui_mc2` directories, identifying all instances of old terminology that need updating and mapping data access patterns to the new markdown parser functions.

**Scope of Changes:**
- 2 TUI implementations with multiple panes, screens, and utility files
- Over 1000 total occurrences of old terminology requiring updates
- Data access patterns shifting from JSON-based to markdown-based parsing
- UI text, variable names, and function names requiring consistent terminology updates

---

## File-by-File Analysis

### maestro/tui Directory

#### Core TUI Files
- `app.py`, `entry.py`, `__main__.py`, `__init__.py`
  - Contains references to old terminology throughout UI status and navigation
  - Uses `ui_facade.plans`, `ui_facade.sessions`, `ui_facade.build` for data access
  - Requires terminology updates in UI text and variable names

#### Screen Files
- `screens/__init__.py`
  - Exports "plans" and "tasks" screens which need renaming to "phases" and "tasks"
- `screens/build.py`, `screens/help.py`, `screens/home.py`, `screens/plans.py`, `screens/sessions.py`, `screens/tasks.py`
  - All screens contain references to "plan" terminology that needs to be updated to "phase"
  - Data access via `ui_facade.*` modules will need to be mapped to new markdown parsers
- `screens/vault.py`, `screens/mc_shell.py`, `screens/semantic.py`, `screens/semantic_diff.py`, etc.
  - Secondary screens with various UI text containing old terminology

#### Pane Files
- `panes/base.py`, `panes/plans.py`, `panes/sessions.py`, `panes/tasks.py`
  - Critical files requiring terminology updates (plans -> phases)
  - Data access functions from `ui_facade.plans`, `ui_facade.sessions`, `ui_facade.tasks`
- `panes/build.py`, `panes/convert.py`, `panes/registry.py`
  - Additional panes with terminology updates needed
  - Registry system needs updating to handle new "phase" terminology

#### Widget Files
- `widgets/modals.py`, `widgets/help_panel.py`, `widgets/status_line.py`
  - UI text elements contain "plan" terminology that needs updating to "phase"
  - Status line displays active plan/build info - needs terminology update

#### Utility Files
- `utils.py`, `onboarding.py`
  - Onboarding help text contains old terminology
  - Utility functions may contain terminology that needs updating

### maestro/tui_mc2 Directory

#### Core Files
- `app.py`
  - Contains numerous references to "plans" that need updating to "phases"
  - Context variables like `active_plan_id`, `selected_plan_id` need renaming
  - Menu actions like `plans.refresh`, `plans.set_active`, `plans.kill` need updating

#### UI Files
- `ui/menubar.py`, `ui/status.py`, `ui/modals.py`
  - Menubar contains menus for "Plans" which need to be "Phases"
  - Status displays plan information - needs terminology update
  - Modal dialogs reference "plan" terminology

#### Pane Files
- `panes/plans.py`, `panes/tasks.py`, `panes/sessions.py`, `panes/build.py`, `panes/convert.py`
  - Critical files with significant terminology changes needed
  - Heavy use of `ui_facade.plans` and related data access functions
  - Plan tree structure needs to become Phase structure

---

## Implementation Sequence

### Phase 1: Core Infrastructure Changes
1. Update import paths and module references
2. Create new UI facade functions for markdown data access
3. Update data access functions to use `parse_todo_md`, `parse_config_md`, `parse_phase_md`

### Phase 2: Variable and Function Name Updates
1. Rename `plan` variables to `phase` variables
2. Update function names from `get_plan_...` to `get_phase_...`
3. Maintain backward compatibility where required

### Phase 3: UI Text and Display Updates
1. Update all UI text containing old terminology
2. Update help text and onboarding materials
3. Update menu items and status displays

### Phase 4: Integration and Testing
1. Test data flow from markdown parsers to UI components
2. Verify all functionality remains intact after terminology changes
3. Validate that both TUI implementations work with new data backend

---

## Risk Assessment

### High Risk Areas
- **Data Access Migration**: Moving from JSON files (`./.maestro/*.json`) to markdown files (`docs/*.md`) requires careful handling to ensure no data loss
- **UI Facade Compatibility**: The UI facade functions need to be updated to work with the new markdown parsers without breaking existing functionality
- **Variable Renaming**: Extensive renaming of variables like `plan_id` to `phase_id` could introduce subtle bugs if not handled systematically

### Medium Risk Areas
- **Terminology Consistency**: Ensuring all references to "plan" become "phase" consistently across both TUI implementations
- **Session State Handling**: Active session and plan selection needs to properly map to phase selection

### Mitigation Strategies
1. Implement new markdown-based data access functions alongside existing ones initially
2. Use feature flags to allow gradual rollout of new terminology
3. Create comprehensive test suite to validate all UI paths with new data backend
4. Maintain backward compatibility with JSON format during transition period

---

## Data Backend Mapping

### Current JSON-Based Access (to be replaced)
- `ui_facade.plans.*` functions currently access `.maestro/sessions/*` JSON files
- `ui_facade.sessions.*` functions access `.maestro/sessions/` directory
- `ui_facade.tasks.*` functions access task-related JSON files

### New Markdown-Based Access (to implement)
- `parse_todo_md()` → replaces session/roadmap-level JSON access
- `parse_config_md()` → replaces configuration JSON access
- `parse_phase_md()` → replaces plan-specific JSON access
- Data transformation layer needed to map markdown structure to current UI facade interface

### Mapping Strategy
1. Create new UI facade functions that internally use markdown parsers
2. Preserve existing function signatures to minimize UI changes
3. Create adapter layer between markdown structure and current data models
4. Gradually migrate from old JSON-based backends to new markdown-based ones

---

## Test Strategy

### Unit Tests
- Test new markdown parsing functions with various input formats
- Test data transformation from markdown to UI facade models
- Test error handling for missing or malformed markdown files

### Integration Tests
- Test end-to-end UI flows with new data backend
- Verify all pane and screen functionality remains intact
- Test edge cases like empty markdown files, missing sections, etc.

### User Acceptance Tests
- Test navigation between sessions, phases, and tasks
- Test active session and phase selection
- Verify all menu options and keyboard shortcuts work correctly
- Test both TUI implementations (maestro/tui and maestro/tui_mc2)

---

## Recommendations

1. **Start with Infrastructure**: Begin by implementing the new markdown parsing functions and data transformation layer
2. **Gradual Migration**: Use feature flags to allow testing new functionality alongside the old system
3. **Thorough Testing**: Implement comprehensive tests for all UI paths before fully switching to new data backend
4. **Documentation**: Update all inline comments and documentation to reflect new terminology
5. **Rollback Plan**: Maintain the ability to revert to the old JSON-based system if issues arise

The CLI5 conversion represents a significant but necessary evolution of the Maestro system to use human-readable markdown files as the primary data source, improving maintainability and transparency for users.