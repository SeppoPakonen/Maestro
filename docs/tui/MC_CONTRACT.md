# Midnight Commander-Style TUI Contract

This document defines the baseline interaction contract for Maestro's new Midnight Commander (MC)-style shell. It is a thin skeleton that future tasks will plug real content into without changing the fundamentals.

## Why We Are Doing This
- Provide a predictable, keyboard-first shell that mirrors the proven MC workflow (menu + two panes + status bar).
- Establish shared focus/navigation/action rules before migrating any feature screens.
- Reserve function keys and mouse behavior early to avoid conflicting bindings later.

## What We Will Replace (Eventually)
- The current router + screen-per-feature layout will give way to this two-pane shell.
- Existing standalone screens will be embedded into the panes instead of mounted directly.
- Menu interactions will migrate from scattered bindings to the top menubar once implemented.

## Layout Contract
- Top menubar row with three regions: left `Maestro` label, center current section placeholder (e.g., `Navigator`), right active session/plan/build summary (read-only).
- Two main panes:
  - **Left pane:** selectable list of sections.
  - **Right pane:** content/detail area showing the currently opened section.
- Bottom status bar:
  - Key hints string (e.g., `Tab Switch Pane | Enter Open | Esc Back | F1 Help | F10 Quit`).
  - Focus indicator text `FOCUS: LEFT` or `FOCUS: RIGHT`.

## Focus Rules
- `Tab` / `Shift+Tab` cycle focus between left and right panes.
- The focused pane is visually highlighted (border/background change).
- Future: pane-local focus between list/detail sub-areas will be layered in without changing the Tab contract.

## Navigation Rules
- `Up` / `Down` move the selection within the focused pane when it contains a list (left pane initially).
- `Left` / `Right` will be used later to switch between list and detail sub-areas; keep bindings free until those areas exist.

## Action Rules
- `Enter` performs the safe default: view/open the current selection, never destructive.
- `Esc` cancels/closes modals or steps back/close menu; never destructive and never quits directly.
- `F10` remains the explicit quit path (with the app handling confirmation if needed).

## Function Key Policy (Reserved Now, Implement Later)
- `F1` Help
- `F2` Actions menu
- `F3` View
- `F4` Edit (future)
- `F5` Run/Execute (contextual)
- `F6` Switch/Focus (contextual)
- `F7` New (contextual)
- `F8` Delete/Kill (always confirm)
- `F9` Menu
- `F10` Quit

## Mouse Baseline (Planned)
- Single click selects items.
- Wheel scroll scrolls lists.
- Double-click mirrors `Enter` and is never destructive.
