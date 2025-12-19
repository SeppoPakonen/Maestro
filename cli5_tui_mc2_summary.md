# CLI5 TUI_MC2 Terminology Update Summary

## Overview
This report summarizes the terminology changes made to the `maestro/tui_mc2/` directory, updating from the old "roadmap/plan/task" terminology to the new "track/phase/task" terminology.

## Files Renamed
- `maestro/tui_mc2/panes/plans.py` → `maestro/tui_mc2/panes/phases.py`

## Files Updated
1. `maestro/tui_mc2/panes/phases.py` (formerly plans.py)
2. `maestro/tui_mc2/panes/tasks.py`
3. `maestro/tui_mc2/panes/sessions.py`
4. `maestro/tui_mc2/app.py`
5. `maestro/tui_mc2/ui/menubar.py`
6. `maestro/tui_mc2/ui/status.py`

## Terminology Changes Applied
### Plan → Phase
- Variable names: `plan_id` → `phase_id`, `active_plan` → `active_phase`, `selected_plan` → `selected_phase`, etc.
- Function names: `get_plan()` → `get_phase()`, `set_active_plan()` → `set_active_phase()`, `kill_plan()` → `kill_phase()`, etc.
- Class names: `PlansPane` → `PhasesPane`, `PlanTreeNode` → `PhaseTreeNode`, etc.
- UI text: "Active Plan" → "Active Phase", "Plan Tree" → "Phase Tree", "Plans" → "Phases", etc.
- Comments and docstrings updated to reflect phase concept

### Roadmap → Track
- No instances of "roadmap" terminology were found in the tui_mc2 directory to update

## Key Updates in Detail

### 1. `phases.py` (formerly `plans.py`)
- Renamed class `PlansPane` to `PhasesPane`
- Updated imports to use `phases` instead of `plans`
- Changed `PlanRow` to `PhaseRow` class
- Updated all UI elements from "Plan" to "Phase"
- Updated all internal references to plan concept to phase concept

### 2. `app.py`
- Updated import statement to import `PhasesPane` instead of `PlansPane`
- Changed context variables like `active_plan_id` to `active_phase_id`
- Updated view switching logic from "plans" to "phases"
- Updated menu action handlers to use "phases" instead of "plans"

### 3. `tasks.py`
- Updated import to use `get_active_phase` instead of `get_active_plan`
- Changed context variable reference from `plan_id` to `phase_id`
- Updated status message from "No active plan" to "No active phase"

### 4. `sessions.py`
- Updated `SessionDisplay` class to use `active_phase_id` instead of `active_plan_id`
- Updated UI text from "Active Plan" to "Active Phase"

### 5. `ui/menubar.py`
- Renamed "Plans" menu to "Phases" menu
- Updated menu action IDs from "plans.*" to "phases.*"
- Updated menu items from "Plans" to "Phases" in View menu

### 6. `ui/status.py`
- Updated logic to check for "phases" view and display phase status text
- Updated context variable references to use phase terminology

## Verification
- All Python files pass syntax checking
- All import statements are correctly updated
- No old terminology remains in variable or function names
- UI text consistently uses new terminology
- Comments and docstrings updated appropriately

## Edge Cases Handled
- Preserved "planner_model" terminology as it refers to the planning model, not the plan branch
- Only replaced "plan" when it referred to the Maestro concept of plan branches, not general English usage
- Maintained functionality while changing terminology

## Files Affected
- Total files modified: 6
- Files with terminology changes: 6
- Files renamed: 1

This update provides consistency with the new track/phase/task terminology throughout the MC2 TUI system while preserving all existing functionality.