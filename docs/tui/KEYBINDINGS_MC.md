# Midnight Commander-Style Keyboard Bindings

This document details the complete keyboard binding policy for Maestro's MC-style shell.

## Function Key Bindings (F-keys)

### Global Navigation (Available in all panes)
- **F1**: Open Help screen
- **F2**: Open active pane's action menu (if available)
- **F3**: Open "View" menu for pane switching
- **F5**: Run default action (pane-specific)
- **F7**: New item (pane-specific)
- **F8**: Delete selected item (pane-specific)
- **F9**: Toggle menubar (activate/deactivate)
- **F10**: Quit application

### Pane-Specific Actions
- **F-keys may map to pane menu items** when the pane defines them with corresponding key hints
- **F5/F7/F8** will execute actions defined in the active pane's menu with matching key hints or fkey properties

### BatchPane Specific Actions
- **F3**: Open repo in single-repo MC view
- **F5**: Run batch (respects rehearsal/checkpoint mode)
- **F6**: Resume batch
- **F7**: Skip job (requires reason, logged as evidence)
- **F8**: Abort job
- **F9**: Open menu
- **F10**: Quit/Back to main navigation

### TimelinePane Specific Actions
- **F3**: Jump to state before this event (read-only preview)
- **F5**: Replay from this event (dry-run)
- **F6**: Replay & apply from this event (with confirmation)
- **F7**: Mark event as "explained" (requires note, stored as evidence)
- **F8**: Create recovery branch (new plan/run lineage)
- **F9**: Open timeline menu
- **F10**: Quit/Back to main navigation

## Standard Navigation Keys

### Focus Management
- **Tab**: Cycle focus between left pane, right pane, and menubar (when active)
- **Shift+Tab**: Cycle focus in reverse order
- **Ctrl+Tab**: Switch focus between panes (alternative to Tab)

### Pane Navigation
- **Up/Down arrows**: Move selection in focused list/view
- **Left arrow**: Move focus from right pane to left pane (does nothing in left pane)
- **Right arrow**: Move focus from left pane to right pane (may expand details in right pane)

### Action Keys
- **Enter**: Execute default action on selected item (view/open in left pane, context-specific in right pane)
- **Escape**: Cancel/close modal, close open menu, or return to previous state (never quits)

## Menubar Navigation

When menubar is active (via F9 or mouse click):
- **Left/Right arrows**: Move between top-level menus
- **Down arrow**: Open currently selected menu
- **Enter**: Open currently selected menu or execute selected menu item
- **Up/Down arrows**: Navigate within open menu items
- **Enter**: Execute selected menu item
- **Escape**: Close menubar and return focus
- **F9**: Close menubar (when active)

## Mouse Interaction

### Click Behavior
- **Left click on menubar**: Activate menubar
- **Left click on menubar menu**: Open that menu
- **Left click on menu item**: Execute that action
- **Left click on section list**: Select that section and switch focus to right pane
- **Left click on content pane**: Focus that pane for keyboard input
- **Double-click anywhere**: Equivalent to Enter on selected item

### Scroll Behavior
- **Mouse wheel in left pane**: Scroll through section list
- **Mouse wheel in right pane**: Scroll through content (pane-specific behavior)

### Hover Behavior
- **Hover over menubar items**: Visual highlight
- **Hover over menu items**: Visual highlight and potential preview
- **Hover over list items**: Visual highlight

## Keyboard-First Philosophy

- **Mouse is always optional** - every action accessible via mouse is also accessible via keyboard
- **Menu actions correspond to F-key bindings** when applicable
- **Keypad navigation follows MC conventions** for familiar workflow
- **No hidden actions** - all functionality is discoverable through menubar or keyboard