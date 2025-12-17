# MC2 TUI Spike Documentation

## Overview

This document describes the MC2 (Midnight Commander 2) TUI spike, a new implementation of the Maestro TUI using Python curses instead of Textual. This approach offers:

- Lower memory footprint
- Better performance in constrained environments
- More direct terminal control
- Compatibility with a wider range of terminals

## Why Evaluate curses/npyscreen/asciimatics?

We're evaluating these three libraries for the following reasons:

- **curses**: Built into Python standard library, mature, efficient, works in all terminal types
- **npyscreen**: Higher-level wrapper around curses, easier to use
- **asciimatics**: Modern library with animation capabilities

## MC2 Layout Contract

The MC2 TUI follows a rigid layout contract to maintain consistency:

```
+------------------------------------------------+
| File  Edit  View  Help            F1=Help F10=X |  <- Menubar (1 line)
+-------------------+----------------------------+
| Left Pane         | Right Pane                 |  <- Two panes (fill space)
|                   |                            |
| - Content         | - Details of selected      |
| - Navigation      | - Contextual actions       |
| - Lists           | - Information display      |
|                   |                            |
+-------------------+----------------------------+
| F1=Help F5=Refresh F7=New F8=Del F9=Menu F10=Quit |  <- Status line (1 line)
+------------------------------------------------+
```

### Key Navigation Rules
- `Tab`: Switch between left and right panes
- Arrow keys: Navigate within the focused pane
- `Enter`: Perform primary action (select/open/execute)
- `Esc`: Close menus/modals, return focus to main interface
- Function keys:
  - `F1`: Help
  - `F5`: Refresh
  - `F7`: New item
  - `F8`: Delete item
  - `F9`: Toggle menubar
  - `F10`: Quit (with confirmation)

## Modes of Operation

### Interactive Mode
Run with:
```bash
python -m maestro.tui --mc2
```

### Smoke Mode (Non-interactive)
For CI and testing:
```bash
python -m maestro.tui --mc2 --smoke --smoke-seconds 0.1
```

Smoke mode will:
1. Start the curses app
2. Render at least one frame
3. Exit automatically within the given time
4. Print `MAESTRO_TUI_SMOKE_OK` to stdout
5. Not hang even if terminal isn't fully interactive

## Implementation Features

### Sessions Pane
The current implementation focuses on the Sessions pane with full functionality:

#### Left Pane (Sessions List)
- Displays all available sessions
- Shows session name, status, and truncated ID
- Navigation with arrow keys
- Selected item highlighted when pane has focus

#### Right Pane (Session Details)
- Shows detailed information for selected session
- Updates when selection changes in left pane
- Displays ID, creation time, status, and task information

#### Actions
- `F5` Refresh: Reloads the sessions list from the backend
- `F7` New: Opens input modal to create a new session
- `F8` Delete: Opens confirmation modal to delete selected session
- `Enter` on session: Displays details in right pane and sets status message

## Known Limitations

### Mouse Support
- Basic mouse events are supported in curses but not currently used
- Textual has more advanced mouse support than curses
- For this MC-style interface, keyboard navigation is the primary focus

### Color Limitations
- Colors depend on terminal capabilities
- Basic color pairs are used for UI elements (menubar, status, selection)

### Modal Interactions
- Input modals temporarily change terminal settings
- May not work properly in all terminal emulators
- Non-blocking smoke mode ensures no hangs

### Screen Resizing
- Curses applications have basic resize detection
- UI will adapt when terminal is resized (with proper handling)

## Architecture

### Directory Structure
```
maestro/tui_mc2/
├── __init__.py
├── app.py                  # Main application and event loop
├── ui/
│   ├── menubar.py          # Menubar implementation
│   ├── status.py           # Status line implementation
│   └── modals.py           # Modal dialog helpers
├── panes/
│   └── sessions.py         # Sessions pane implementation
└── util/
    └── smoke.py            # Smoke mode utilities
```

### Integration with Existing Code
- Uses the same `ui_facade` layer as other TUI implementations
- No dependency on CLI subprocess calls
- Leverages existing session management functions
- Maintains the same data contracts

## Testing

### Smoke Test
The `--smoke` and `--smoke-seconds` parameters enable non-interactive testing, crucial for CI systems. The application will render UI elements and then exit after the specified time.

### Manual Testing
Test the following scenarios:
- Basic navigation between panes
- All function key operations
- Modal dialog interactions  
- Smoke mode execution
- Terminal resize handling

## Future Considerations

### Additional Panes
The architecture is extensible to add other panes (Plans, Tasks, Build, etc.) following the same patterns as the Sessions pane.

### Enhanced Menubar
Currently basic, with potential for:
- More dynamic menu content
- Keyboard shortcuts for menu items
- Contextual menus based on pane content

### Accessibility
- High contrast color schemes
- Screen reader compatibility (limited in curses)
- Keyboard navigation compliance