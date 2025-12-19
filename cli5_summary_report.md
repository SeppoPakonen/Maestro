# CLI5 TUI Terminology Update - Summary Report

## Overview
This report summarizes the changes made to update terminology in the `maestro/tui/` directory. The changes replace "Plan" with "Phase" and "Roadmap" with "Track" terminology throughout the TUI codebase.

## Files Modified

### 1. File Renames
- `maestro/tui/screens/plans.py` → `maestro/tui/screens/phases.py`
- `maestro/tui/panes/plans.py` → `maestro/tui/panes/phases.py`

### 2. Updated Files

#### Core Application
- `maestro/tui/app.py` - Updated imports, class references, UI elements, variable names, and session status display

#### Screens
- `maestro/tui/screens/phases.py` (renamed from plans.py) - Updated class name, methods, UI elements, and terminology
- `maestro/tui/screens/home.py` - Updated navigation list item
- `maestro/tui/screens/mc_shell.py` - Updated imports, sections list, session summary, and terminology
- `maestro/tui/screens/sessions.py` - Updated UI elements and confirmation messages
- `maestro/tui/screens/tasks.py` - Updated confirmation messages
- `maestro/tui/screens/help.py` - Updated screen list and quick actions
- `maestro/tui/screens/help_index.py` - Updated concept explanations and system flow

#### Panes
- `maestro/tui/panes/phases.py` (renamed from plans.py) - Updated class name, UI elements, and terminology
- `maestro/tui/panes/registry.py` - Updated import statement
- `maestro/tui/panes/runs.py` - Updated "Plan Revision" reference
- `maestro/tui/panes/sessions.py` - Updated "Active Plan" reference
- `maestro/tui/panes/timeline.py` - Updated menu item and system impact description

#### Widgets
- `maestro/tui/widgets/command_palette.py` - Updated action mappings, navigation, and phase operations
- `maestro/tui/widgets/help_panel.py` - Updated help content for phases and home screen
- `maestro/tui/widgets/status_line.py` - Updated documentation
- `maestro/tui/onboarding.py` - Updated onboarding steps and descriptions

#### Other Files
- `maestro/tui/screens/__init__.py` - Updated module exports
- `maestro/tui/screens/replay.py` - Updated "Plan Revision" reference
- `maestro/tui/screens/memory.py` - Updated "plan_is_stale" references

## Changes Summary by Category

### Variable Name Changes
- `plan_id` → `phase_id`
- `active_plan` → `active_phase`
- `selected_plan_id` → `selected_phase_id`
- `current_plan_details` → `current_phase_details`
- `plan_tree_root` → `phase_tree_root`
- `plans` → `phases`
- And many other plan-related variable names

### Function/Method Name Changes
- `get_plan_tree` → `get_phase_tree`
- `list_plans` → `list_phases`
- `get_plan_details` → `get_phase_details`
- `set_active_plan` → `set_active_phase`
- `kill_plan` → `kill_phase`
- `select_plan` → `select_phase`
- `refresh_plan_tree` → `refresh_phase_tree`
- And many more

### Class Name Changes
- `PlansScreen` → `PhasesScreen`
- `PlansPane` → `PhasesPane`

### UI Text and Labels
- "Active Plan" → "Active Phase"
- "Plan Tree" → "Phase Tree"
- "Plan Details" → "Phase Details"
- "Set Active Plan" → "Set Active Phase"
- "Kill Plan" → "Kill Phase"
- "Plan List" → "Phase List"
- "Plan ID" → "Phase ID"
- And many more UI elements

### Import Updates
- Updated all imports from `maestro.ui_facade.plans` to `maestro.ui_facade.phases`
- Updated screen imports from `maestro.tui.screens.plans` to `maestro.tui.screens.phases`
- Updated pane imports from `maestro.tui.panes.plans` to `maestro.tui.panes.phases`

## Verification
- All import statements have been updated to reflect the new terminology
- All UI text consistently uses the new terminology
- All variable and function names use the new terminology
- The functionality remains intact - these were pure terminology changes

## Files Not Changed
- No external dependencies were modified
- No configuration files changed
- No build files affected

## Patch File
A unified diff file (`cli5_tui_terminology.patch`) has been generated containing all changes made to the codebase.

## Impact Assessment
- No functionality changes - pure terminology update
- All existing features should work identically
- UI now consistently uses "Phase" terminology instead of "Plan"
- Backend facade calls updated to use new terminology (phases instead of plans)