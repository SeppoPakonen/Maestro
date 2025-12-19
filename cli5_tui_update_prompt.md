# CLI5 TUI Terminology Update Task

## Context

You've completed the audit (see `cli5_audit_report.md`). Now implement the actual terminology changes for the `maestro/tui/` directory.

## Task: Update maestro/tui/ Terminology

Replace all instances of the old terminology with the new one:
- "Roadmap" → "Track" (capitalize as appropriate)
- "roadmap" → "track" (lowercase)
- "Plan" → "Phase" (capitalize as appropriate)
- "plan" → "phase" (lowercase when it refers to the new "phase" concept)
- "Task" stays as "Task"

### Important Rules

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

4. **Consistent Casing**: Maintain the same casing pattern:
   - `plan_id` → `phase_id` (snake_case)
   - `PlanID` → `PhaseID` (PascalCase)
   - `planId` → `phaseId` (camelCase, if any)

## Implementation Approach

### Step 1: Rename Files First
Rename these files:
- `maestro/tui/screens/plans.py` → `maestro/tui/screens/phases.py`
- `maestro/tui/panes/plans.py` → `maestro/tui/panes/phases.py`

### Step 2: Update Import Statements
After renaming, update all import statements that reference the renamed files:
- `from maestro.tui.screens.plans import` → `from maestro.tui.screens.phases import`
- `from maestro.tui.panes.plans import` → `from maestro.tui.panes.phases import`

### Step 3: Global Search and Replace
For each file in `maestro/tui/`, perform context-aware replacements:

1. Variable names (exact matches with word boundaries):
   - `\bplan_id\b` → `phase_id`
   - `\bactive_plan\b` → `active_phase`
   - `\bselected_plan\b` → `selected_phase`
   - `\bcurrent_plan\b` → `current_phase`
   - `\bparent_plan\b` → `parent_phase`
   - `\bplan_tree\b` → `phase_tree`
   - `\bplan_list\b` → `phase_list`
   - `\bplans\b` → `phases` (when used as variable for list of plans)

2. Function and method names:
   - `\bget_plan\b` → `get_phase`
   - `\bset_plan\b` → `set_phase`
   - `\bload_plan\b` → `load_phase`
   - `\brefresh_plan\b` → `refresh_phase`
   - `\bkill_plan\b` → `kill_phase`
   - `\bselect_plan\b` → `select_phase`

3. Class names:
   - `\bPlanDetails\b` → `PhaseDetails`
   - `\bPlanTree\b` → `PhaseTree`
   - `\bPlanPane\b` → `PhasePane`

4. UI text and strings:
   - "Active Plan" → "Active Phase"
   - "Plan Tree" → "Phase Tree"
   - "Plan ID" → "Phase ID"
   - "Set Active Plan" → "Set Active Phase"
   - "Kill Plan" → "Kill Phase"
   - "No plan selected" → "No phase selected"

5. Comments and docstrings:
   - Update references to "plan" concept → "phase" concept where appropriate

### Step 4: Special Cases

Handle these files with extra care:

1. **maestro/tui/app.py**:
   - Status bar displays (`#active-plan` → `#active-phase`)
   - Context variables

2. **maestro/tui/widgets/command_palette.py**:
   - Command names and labels
   - Menu items for plan operations → phase operations

3. **maestro/tui/widgets/help_panel.py**:
   - Help text documentation

4. **maestro/tui/onboarding.py**:
   - Onboarding tutorial text

## Output Format

Create a **unified diff file** that shows all the changes. This is critical for review:

```bash
# Generate unified diff for all changes
git diff --no-index --unified=3 maestro/tui/ maestro/tui.new/ > cli5_tui_terminology.patch
```

Or if working in-place, use a systematic approach to generate diffs for each file changed.

## Verification

After making changes, verify:
1. All imports still work (no broken imports from renamed files)
2. No instances of old terminology remain in variable/function/class names
3. UI text is updated consistently
4. Comments and docstrings are updated
5. The code still follows Python conventions

## Deliverables

1. **All updated files** in `maestro/tui/` with new terminology
2. **A unified diff file** (`cli5_tui_terminology.patch`) showing all changes
3. **A summary report** listing:
   - Files renamed
   - Number of replacements by category (variables, functions, classes, UI text, comments)
   - Any edge cases or manual interventions needed

## Example Change

Before:
```python
def set_active_plan(self, plan_id: str):
    """Set the active plan for the session."""
    self.active_plan = plan_id
    self.query_one("#active-plan").update(f"Plan: {plan_id[:8]}...")
```

After:
```python
def set_active_phase(self, phase_id: str):
    """Set the active phase for the session."""
    self.active_phase = phase_id
    self.query_one("#active-phase").update(f"Phase: {phase_id[:8]}...")
```

## Start Implementation

Begin by:
1. Creating a backup of the maestro/tui directory
2. Renaming the key files (plans.py → phases.py)
3. Performing systematic replacements
4. Generating the diff file
5. Creating the summary report
