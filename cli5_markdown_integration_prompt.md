# CLI5 Markdown Data Backend Integration

## Context

The terminology has been updated in both `maestro/tui/` and `maestro/tui_mc2/`. Now we need to integrate the new markdown data backend so the TUIs read from `docs/*.md` files instead of `.maestro/*.json` files.

## Current Situation

The markdown parser functions exist in `maestro/data/markdown_parser.py` and are exported from `maestro/data/__init__.py`:
- `parse_todo_md()` - parses docs/todo.md for tracks/phases/tasks
- `parse_done_md()` - parses docs/done.md for completed items
- `parse_phase_md(phase_id)` - parses individual phase markdown files
- `parse_config_md()` - parses docs/config.md for configuration

The UI facade in `maestro/ui_facade/` currently accesses JSON files in `.maestro/`. We need to update it to use markdown parsers.

## Task: Create Markdown-Based UI Facade

### Step 1: Rename ui_facade/plans.py to ui_facade/phases.py

First, rename the file to match the new terminology:
```bash
git mv maestro/ui_facade/plans.py maestro/ui_facade/phases.py
```

### Step 2: Create New Phase Facade Functions

Update `maestro/ui_facade/phases.py` to provide these functions using the markdown backend:

```python
from maestro.data import parse_todo_md, parse_done_md, parse_phase_md
from typing import List, Optional

def get_phase_tree(session_id: Optional[str] = None) -> List[PhaseTreeNode]:
    """Get the phase tree from docs/todo.md"""
    tracks = parse_todo_md()
    # Transform tracks → phases → tree structure
    # Return tree nodes compatible with TUI expectations

def list_phases(session_id: Optional[str] = None) -> List[Phase]:
    """Get list of all phases from docs/todo.md"""
    tracks = parse_todo_md()
    # Extract all phases from all tracks
    # Return flat list of phases

def get_phase_details(phase_id: str) -> Optional[PhaseDetails]:
    """Get details for a specific phase"""
    # First check docs/todo.md for the phase
    # Then check individual phase markdown file if it exists
    # Return phase details

def get_active_phase(session_id: str) -> Optional[Phase]:
    """Get the active phase for a session from docs/config.md"""
    config = parse_config_md()
    # Extract active phase from config
    # Return phase object

def set_active_phase(session_id: str, phase_id: str) -> None:
    """Set the active phase in docs/config.md"""
    # Update config markdown file
    # Write back to docs/config.md

def kill_phase(phase_id: str) -> None:
    """Mark a phase as killed/cancelled"""
    # Update phase status in docs/todo.md
    # Move to appropriate section or mark as cancelled
```

### Step 3: Update Data Models

The markdown parser returns different data structures than the old JSON format. You may need to:

1. Check what the TUI expects (look at how it uses the ui_facade functions)
2. Create adapter/transformation functions to convert markdown data to the expected format
3. Update the data models if necessary to match the markdown structure

### Step 4: Update Import Statements

Update all files that import from `maestro.ui_facade.plans` to import from `maestro.ui_facade.phases`:

```bash
# Find all imports to update
grep -r "from maestro.ui_facade.plans import" maestro/
grep -r "import maestro.ui_facade.plans" maestro/
```

### Step 5: Test Data Flow

Create a test script to verify:
1. The markdown files can be parsed
2. The phase tree is constructed correctly
3. Phase details are retrieved correctly
4. Active phase can be set and retrieved

### Step 6: Handle Edge Cases

1. **Missing files**: What if docs/todo.md doesn't exist?
2. **Parse errors**: What if markdown is malformed?
3. **Missing phases**: What if a phase_id isn't found?
4. **Active phase**: How is this stored in config.md?

## Important Considerations

### Data Structure Mapping

The old JSON structure was session-based:
```
.maestro/sessions/{session_id}/
  ├── plan_tree.json
  └── active_plan.json
```

The new markdown structure is project-based:
```
docs/
  ├── todo.md        (all tracks/phases/tasks)
  ├── done.md        (completed items)
  ├── config.md      (configuration including active phase)
  └── phases/
      ├── cli1.md
      ├── cli2.md
      └── ...
```

You need to:
1. Remove session_id parameters where they're no longer relevant
2. Adapt functions to read from markdown instead of JSON
3. Ensure the TUI still works with the new data structure

### Backward Compatibility

For now, keep both systems working:
1. Check if docs/todo.md exists
2. If yes, use markdown backend
3. If no, fall back to JSON backend
4. Add a deprecation warning for JSON backend

## Deliverables

1. **Updated maestro/ui_facade/phases.py** with markdown backend
2. **Updated import statements** in all TUI files
3. **Test results** showing data can be read from markdown
4. **Summary document** explaining the changes

## Example Transformation

Old (JSON-based):
```python
def get_plan_tree(session_id: str):
    json_file = f".maestro/sessions/{session_id}/plan_tree.json"
    with open(json_file) as f:
        return json.load(f)
```

New (Markdown-based):
```python
def get_phase_tree(session_id: Optional[str] = None):
    tracks = parse_todo_md()  # Read docs/todo.md
    # Transform tracks into tree structure
    tree_nodes = []
    for track in tracks:
        for phase in track.phases:
            node = PhaseTreeNode(
                phase_id=phase.phase_id,
                label=phase.title,
                status=phase.status,
                children=[...],  # tasks
            )
            tree_nodes.append(node)
    return tree_nodes
```

## Start Implementation

1. Examine the current `maestro/ui_facade/plans.py` to understand what it does
2. Look at the markdown parser to understand what data structures it returns
3. Create the mapping layer to transform markdown data → ui_facade data
4. Update the facade functions one by one
5. Test each function as you go
6. Generate a summary of changes
