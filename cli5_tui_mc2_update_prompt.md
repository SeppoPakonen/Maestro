# CLI5 TUI_MC2 Terminology Update Task

## Context

You've successfully updated `maestro/tui/` to use the new Track/Phase/Task terminology. Now do the same for `maestro/tui_mc2/` directory.

## Task: Update maestro/tui_mc2/ Terminology

Replace all instances of the old terminology with the new one:
- "Roadmap" → "Track" (capitalize as appropriate)
- "roadmap" → "track" (lowercase)
- "Plan" → "Phase" (capitalize as appropriate)
- "plan" → "phase" (lowercase when it refers to the new "phase" concept)
- "Task" stays as "Task"

### Important Rules (Same as TUI)

1. **Context-Aware Replacement**: The word "plan" is common in English. Only replace it when it refers to the Maestro concept of a plan (now phase). DO NOT replace:
   - "Test plan" (this is a general English phrase)
   - "Plan to" (verb usage, like "we plan to do X")
   - "Planning" (verb, general usage)

2. **What TO Replace**:
   - Variable names: `plan_id` → `phase_id`, `active_plan` → `active_phase`, etc.
   - Function names: `get_plan()` → `get_phase()`, `set_active_plan()` → `set_active_phase()`, etc.
   - Class names: `PlanDetails` → `PhaseDetails`, etc.
   - UI text: "Active Plan" → "Active Phase", "Plan Tree" → "Phase Tree", etc.
   - Comments and docstrings when referring to the Maestro plan concept
   - File names: `plans.py` → `phases.py`

3. **Preserve Functionality**: These are pure terminology changes. Do NOT change logic, data structures, or functionality.

## Implementation Approach

### Step 1: Rename Files First
Rename these files:
- `maestro/tui_mc2/panes/plans.py` → `maestro/tui_mc2/panes/phases.py`

### Step 2: Update Import Statements
After renaming, update all import statements that reference the renamed files:
- `from maestro.tui_mc2.panes.plans import` → `from maestro.tui_mc2.panes.phases import`

### Step 3: Global Search and Replace
For each file in `maestro/tui_mc2/`, perform context-aware replacements:

1. Variable names (exact matches with word boundaries):
   - `\bplan_id\b` → `phase_id`
   - `\bactive_plan\b` → `active_phase`
   - `\bactive_plan_id\b` → `active_phase_id`
   - `\bselected_plan\b` → `selected_phase`
   - `\bselected_plan_id\b` → `selected_phase_id`
   - `\bcurrent_plan\b` → `current_phase`
   - `\bplan_tree\b` → `phase_tree`
   - `\bplans\b` → `phases` (when used as variable for list of plans)

2. Function and method names:
   - `\bget_plan\b` → `get_phase`
   - `\bget_active_plan\b` → `get_active_phase`
   - `\blist_plans\b` → `list_phases`
   - `\brefresh_plan\b` → `refresh_phase`
   - `\bkill_plan\b` → `kill_phase`

3. UI text and strings:
   - "Active Plan" → "Active Phase"
   - "No active plan" → "No active phase"
   - "Set active plan" → "Set active phase"
   - "Kill plan" → "Kill phase"
   - "Plan ID" → "Phase ID"

4. Comments and docstrings:
   - Update references to "plan" concept → "phase" concept where appropriate

### Step 4: Special Files

Handle these files with care:

1. **maestro/tui_mc2/app.py**:
   - Context variables like `active_plan_id`, `selected_plan_id`
   - Menu actions for plan operations

2. **maestro/tui_mc2/panes/plans.py** (→ phases.py):
   - All plan tree navigation
   - Phase selection and display logic

3. **maestro/tui_mc2/panes/sessions.py**:
   - Active plan display

4. **maestro/tui_mc2/panes/tasks.py**:
   - References to active plan

5. **maestro/tui_mc2/ui/menubar.py**:
   - Menu items for plan operations

6. **maestro/tui_mc2/ui/status.py**:
   - Status display for active plan

## Output Format

Create a **unified diff file** that shows all the changes:

```bash
# Generate unified diff for all changes
git diff --no-index maestro/tui_mc2/ maestro/tui_mc2.new/ > cli5_tui_mc2_terminology.patch
```

## Verification

After making changes, verify:
1. All imports still work
2. No instances of old terminology remain in variable/function names
3. UI text is updated consistently
4. Comments and docstrings are updated
5. Python syntax is valid

## Deliverables

1. **All updated files** in `maestro/tui_mc2/` with new terminology
2. **A unified diff file** (`cli5_tui_mc2_terminology.patch`) showing all changes
3. **A summary report** (`cli5_tui_mc2_summary.md`) listing:
   - Files renamed
   - Number of replacements by category
   - Any edge cases

## Start Implementation

Begin by:
1. Creating a backup of maestro/tui_mc2 directory
2. Renaming plans.py → phases.py
3. Performing systematic replacements
4. Generating the diff file
5. Creating the summary report
