# Maestro TUI Key Bindings - Midnight Commander Style

This document establishes the single source of truth for key binding policy in Maestro's Midnight Commander-style TUI.

## Global Rules (Always Available)

These key bindings work across all screens and panes:

- **Tab** - Switch focus between panes/elements
- **Shift+Tab** - Switch focus in reverse direction between panes/elements
- **Up/Down/Left/Right Arrows** - Navigate within focused lists, trees, and containers
- **Enter** - Perform primary action on currently selected item (never destructive)
- **Esc** - Cancel current operation, close menus/popups, or return to safe state (never destructive)
- **F9** - Open/close menubar for discoverability
- **F10** - Quit application

## Function Key Map (F1-F10)

These keys provide consistent, primary access to common actions:

- **F1** - Help (open help modal/view)
- **F2** - Actions menu (open the active pane's menu directly)
- **F3** - View (open View menu, context-dependent)
- **F5** - Run/Execute (pane-defined; if none, show "not available" message)
- **F6** - Switch/Focus (contextual - future use)
- **F7** - New (pane-defined; if none, show "not available" message)
- **F8** - Delete/Kill (pane-defined; must confirm, or show "not available" message)
- **F9** - Menubar focus/open (canonical discoverability surface)
- **F10** - Quit (exit application)

## Pane-Specific Action Rules

When an F-key is pressed:

1. The MC shell checks if the active pane has an associated action for that F-key
2. If available and enabled, the action is executed
3. If not available or disabled, a status message is shown: "Not available in this pane"
4. No error modal is displayed for unavailable actions

## Action Addressability

All actions that should be accessible via F-keys must:

1. Be exposed in the pane's menu definition
2. Have an `action_id` for programmatic access
3. Optionally have an `fkey` hint indicating preferred function key

## Temporary Legacy Support

The following single-letter shortcuts are temporarily allowed for backward compatibility but will be phased out:

- **s** - Sessions screen
- **p** - Plans screen
- **t** - Tasks screen
- **b** - Build screen
- **c** - Convert screen
- **r** - Refresh current view

These will eventually be gated behind a "legacy mode" toggle.

## Hard Rule: No Conflicting Global Bindings

**NO screen or pane may define conflicting global bindings.** Specifically:

- Panes cannot override Tab, Enter, Esc, or arrow key behavior without special coordination
- Panes cannot override F1, F9, or F10 behavior
- Any pane that needs to handle these keys must do so in a way that respects the global contract
- Panes cannot define their own F-key bindings that conflict with the global map (F1-F10)

## Navigation Consistency Policy

Navigation within the TUI adheres to this consistent pattern:

- **Arrows** - Move cursor/selection within focused container
- **Tab/Shift+Tab** - Switch focus between major UI elements
- **Enter** - Activate/confirm current selection
- **Esc** - Cancel/exit/close
- **F-keys** - Direct access to primary functions

## Enforcement

This policy will be enforced through:

1. Documentation and team awareness
2. Code-level checks to prevent conflicting bindings
3. Test coverage to ensure compliance
4. Regular audits of key binding usage