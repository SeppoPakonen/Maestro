# Phase CLI5: TUI Track/Phase/Task Conversion 📋 **[Planned]**

"phase_id": "cli-tpt-5"
"track": "Track/Phase/Task CLI and AI Discussion System"
"track_id": "cli-tpt"
"status": "planned"
"completion": 0
"duration": "1-2 weeks"
"dependencies": ["cli-tpt-2"]
"priority": "P1"

**Objective**: Convert existing TUI (Terminal User Interface) implementations to use the new Track/Phase/Task terminology and data backend, replacing old Roadmap/Plan/Task concepts. Update both textual-based and ncurses-based TUI implementations.

## Background

Maestro currently has TUI implementations in:
- `maestro/tui/` - Original TUI implementation
- `maestro/tui_mc2/` - MC2-style TUI implementation

Both use the old terminology:
- "Roadmap" → needs to become "Track"
- "Plan" → needs to become "Phase"
- "Task" → stays as "Task"

These TUIs need to:
1. Use new Track/Phase/Task terminology
2. Read from markdown data backend (docs/*.md files)
3. Update to match new CLI commands
4. Remove or archive textual-mc if no longer needed

## Tasks

### Task cli5.1: TUI Terminology Update

"task_id": "cli-tpt-5-1"
"priority": "P1"
"estimated_hours": 8

Update all UI text, variable names, and documentation to use Track/Phase/Task.

- [ ] **cli5.1.1: Audit Current TUI Code**
  - [ ] Scan maestro/tui/ for "roadmap", "plan" references
  - [ ] Scan maestro/tui_mc2/ for "roadmap", "plan" references
  - [ ] Create list of all files needing changes
  - [ ] Document current navigation structure

- [ ] **cli5.1.2: Update maestro/tui/ Terminology**
  - [ ] Replace "Roadmap" with "Track" in UI text
  - [ ] Replace "Plan" with "Phase" in UI text
  - [ ] Update menu labels and help text
  - [ ] Update screen titles
  - [ ] Rename internal variables (roadmap → track, plan → phase)
  - [ ] Update function and class names

- [ ] **cli5.1.3: Update maestro/tui_mc2/ Terminology**
  - [ ] Replace "Roadmap" with "Track" in UI text
  - [ ] Replace "Plan" with "Phase" in UI text
  - [ ] Update menu labels and help text
  - [ ] Update screen titles
  - [ ] Rename internal variables
  - [ ] Update function and class names

- [ ] **cli5.1.4: Update Comments and Documentation**
  - [ ] Update inline comments
  - [ ] Update docstrings
  - [ ] Update any TUI-specific README or docs

### Task cli5.2: Markdown Data Backend Integration

"task_id": "cli-tpt-5-2"
"priority": "P1"
"estimated_hours": 16

Integrate TUI with the new markdown data backend.

- [ ] **cli5.2.1: Replace JSON Data Access**
  - [ ] Remove direct .maestro/*.json file access
  - [ ] Use maestro.data.parse_todo_md() for track/phase data
  - [ ] Use maestro.data.parse_config_md() for configuration
  - [ ] Use maestro.data.parse_phase_md() for phase details
  - [ ] Handle file not found errors gracefully

- [ ] **cli5.2.2: Update Track/Phase/Task Models**
  - [ ] Update data models to match new markdown format
  - [ ] Support new metadata fields (track_id, phase_id, etc.)
  - [ ] Handle new status types (done, in_progress, planned, proposed)
  - [ ] Support completion percentages
  - [ ] Support priority levels (P0, P1, P2)

- [ ] **cli5.2.3: Real-time Data Refresh**
  - [ ] Detect when markdown files change
  - [ ] Refresh TUI display when docs/*.md files updated
  - [ ] Handle parse errors gracefully (show error, don't crash)
  - [ ] Cache parsed data to avoid re-parsing on every render

- [ ] **cli5.2.4: Navigation Updates**
  - [ ] Update navigation tree to show Track → Phase → Task hierarchy
  - [ ] Add breadcrumbs showing current track/phase/task
  - [ ] Support keyboard shortcuts:
    - `t` - view tracks list
    - `p` - view phases in current track
    - `k` - view tasks in current phase
  - [ ] Update search to work across tracks/phases/tasks

### Task cli5.3: Status Badge and Emoji Support

"task_id": "cli-tpt-5-3"
"priority": "P1"
"estimated_hours": 6

Add visual status indicators using emojis and colors.

- [ ] **cli5.3.1: Emoji Status Indicators**
  - [ ] Display ✅ for done status
  - [ ] Display 🚧 for in_progress status
  - [ ] Display 📋 for planned status
  - [ ] Display 💡 for proposed status
  - [ ] Handle terminals that don't support emoji (fallback to text)

- [ ] **cli5.3.2: Completion Progress Bars**
  - [ ] Show completion percentage for phases
  - [ ] Visual progress bar for phases with tasks
  - [ ] Color coding: red < 30%, yellow 30-70%, green > 70%
  - [ ] Show overall track completion

- [ ] **cli5.3.3: Priority Indicators**
  - [ ] Show P0 tasks in red/bold
  - [ ] Show P1 tasks in yellow
  - [ ] Show P2 tasks in normal text
  - [ ] Allow filtering by priority

### Task cli5.4: Feature Parity with CLI

"task_id": "cli-tpt-5-4"
"priority": "P2"
"estimated_hours": 12

Ensure TUI supports all CLI operations.

- [ ] **cli5.4.1: CRUD Operations**
  - [ ] Add new track (interactive form)
  - [ ] Add new phase to track
  - [ ] Add new task to phase
  - [ ] Edit track/phase/task metadata
  - [ ] Delete/archive track/phase/task
  - [ ] Mark task as completed

- [ ] **cli5.4.2: Context Management**
  - [ ] Display current context (track/phase/task)
  - [ ] Allow setting current track
  - [ ] Allow setting current phase
  - [ ] Allow setting current task
  - [ ] Context-aware operations (default to current when no selection)

- [ ] **cli5.4.3: Discussion Integration**
  - [ ] Launch AI discussion from TUI
  - [ ] Integrate with maestro discuss commands
  - [ ] Show discussion history for track/phase/task
  - [ ] Preview suggested actions from AI

### Task cli5.5: textual-mc Deprecation Decision

"task_id": "cli-tpt-5-5"
"priority": "P2"
"estimated_hours": 4

Decide fate of textual-mc implementation and clean up if needed.

- [ ] **cli5.5.1: Evaluate textual-mc**
  - [ ] Review textual-mc code quality and usage
  - [ ] Check if anyone is using textual-mc
  - [ ] Compare features with main TUI
  - [ ] Document pros/cons

- [ ] **cli5.5.2: Deprecation Path**
  - [ ] If deprecating: Add deprecation notice
  - [ ] If deprecating: Document migration to main TUI
  - [ ] If deprecating: Move to maestro/tui/archived/
  - [ ] If keeping: Update to Track/Phase/Task as well
  - [ ] Update docs to reflect decision

### Task cli5.6: Testing and Polish

"task_id": "cli-tpt-5-6"
"priority": "P1"
"estimated_hours": 8

Test TUI thoroughly and polish the user experience.

- [ ] **cli5.6.1: Manual Testing**
  - [ ] Test track navigation
  - [ ] Test phase navigation
  - [ ] Test task operations
  - [ ] Test with large projects (many tracks/phases)
  - [ ] Test error handling (missing files, parse errors)
  - [ ] Test on different terminal emulators

- [ ] **cli5.6.2: Edge Cases**
  - [ ] Empty project (no tracks)
  - [ ] Track with no phases
  - [ ] Phase with no tasks
  - [ ] Malformed markdown data
  - [ ] Missing docs/ directory

- [ ] **cli5.6.3: Performance**
  - [ ] Optimize markdown parsing (cache results)
  - [ ] Profile rendering performance
  - [ ] Ensure smooth scrolling with large lists
  - [ ] Lazy-load phase details

- [ ] **cli5.6.4: User Experience Polish**
  - [ ] Add helpful tooltips/hints
  - [ ] Improve keyboard navigation
  - [ ] Add vim-style keybindings (hjkl navigation)
  - [ ] Add help screen (F1 or ?)
  - [ ] Consistent color scheme

## Deliverables

- Updated `maestro/tui/` with Track/Phase/Task terminology
- Updated `maestro/tui_mc2/` with Track/Phase/Task terminology
- Markdown data backend integration
- Status badges and progress indicators
- Feature parity with CLI commands
- Decision on textual-mc (deprecated or updated)
- Comprehensive testing

## Test Criteria

- TUI displays tracks, phases, and tasks correctly
- All CRUD operations work
- Markdown files are read and written correctly
- Parse errors are handled gracefully
- Status indicators display correctly
- Context management works
- Performance is acceptable for large projects
- No crashes or data corruption

## Dependencies

- Phase CLI2 (Track/Phase/Task Commands) for consistent behavior
- Phase CLI1 (Markdown Data Backend) is already implemented

## Notes

- Maintain backward compatibility where possible
- Consider removing textual-mc if it's not being used
- Focus on maestro/tui/ as the primary TUI
- Ensure TUI and CLI stay in sync

## Estimated Complexity: Medium (1-2 weeks total)

- Days 1-2: Terminology updates (5.1)
- Days 3-5: Markdown integration (5.2)
- Day 6: Status badges (5.3)
- Days 7-8: Feature parity (5.4)
- Day 9: textual-mc decision (5.5)
- Day 10: Testing and polish (5.6)
