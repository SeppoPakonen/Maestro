# MC TUI Pane Contract

## Overview
This document specifies the contract that all MC shell panes must implement for reliable operation.

## Core Principle
> A pane is a component, not a script.

That means:

* Predictable lifecycle
* Explicit dependencies
* No side effects at import time
* Safe failure semantics

## MCPane Protocol

All panes must implement the `MCPane` protocol:

```python
class MCPane(Protocol):
    pane_id: str
    pane_title: str

    def on_mount(self) -> None: ...
    def on_focus(self) -> None: ...
    def on_blur(self) -> None: ...
    def refresh(self) -> None: ...
    def get_menu_spec(self) -> MenuSpec: ...
```

## Lifecycle Contract

Guaranteed execution order:

1. `pane.__init__()` - Constructor
2. `pane.on_mount()` - When pane is mounted to DOM
3. `pane.on_focus()` - When pane receives focus

On switch:

1. Old pane's `on_blur()`
2. New pane's `on_focus()`

## Implementation Requirements

### 1. No Import-Time Side Effects
- Pane modules must not touch filesystem, UI facade, session state, or config at import time
- No facade calls at import time
- No global singletons created on import

### 2. Explicit Dependencies
- If a pane needs data → it fetches it in `on_mount()` or `refresh()`
- All dependencies must be explicit and documented

### 3. Safe Failure Containment
- If a pane fails to import or mount, catch exception
- Show `PaneErrorView` inside pane area
- Status line shows error summary
- App does not crash

## MC-complete Panes
The following panes have been migrated to follow the MCPane contract and are considered MC-complete:

- **Sessions** - ✅ MC-complete
- **Plans** - ✅ MC-complete
- **Tasks** - ✅ MC-complete
- **Build** - ✅ MC-complete
- **Convert** - ✅ MC-read-only (Read-only pipeline view, no execution/mutation)
- **Semantic** - ✅ MC-write-capable (Human Judgement interface - Accept/Reject/Defer/Override actions with reason requirements)
- **Decision** - ✅ MC-write-capable (Decision Override Workshop - explicit decision override with reason requirements)
- **Vault** - ✅ MC-native (Universal Evidence Browser - single authoritative evidence surface in MC mode, all explanations route through Vault)
- **Batch** - ✅ MC-native (Batch & Multi-Repo Control - operations center for batch job management with explicit action discipline)
- **Timeline** - ✅ MC-write-capable (Event Timeline and Recovery Explorer - time travel, replay, branching, and explanation tracking)

## Core MC Infrastructure
The **Vault** pane is now considered **core MC infrastructure**. It serves as the single authoritative evidence surface in MC mode - all `why`, `what`, `when`, `where` flows through this surface. The Vault is the backbone for all other panes' "view evidence" functionality and provides the central evidence browser for the entire system. All explanations route through Vault.

## MC-native Write Capabilities
The following panes implement MC-native write capabilities with explicit human authority patterns:

### SemanticPane - Human Judgement Interface
- **Accept** - Mark a semantic finding as accepted (F5)
- **Reject** - Mark a semantic finding as rejected (requires reason) (F7)
- **Defer** - Mark a semantic finding as deferred (F6)
- **Override** - Override a semantic finding with reason (F8)
- All actions stored as evidence in Vault

### DecisionPane - Decision Override Workshop
- **Override Decision** - Create new decision that supersedes old one (F3)
- Requires explicit reason for all overrides
- Maintains decision history (old decisions marked as superseded)
- All actions stored as evidence in Vault

## Mutation Surfaces
Explicit mutation surfaces are confined to:
- **SemanticPane**: Semantic finding approval/rejection/override (RW)
- **DecisionPane**: Decision override and management (RW)
- **Vault**: Evidence browsing and navigation (RO)
- All other panes remain read-only (RO) as per MC contract

## Error Handling
- All panes must handle errors gracefully
- Use `PaneErrorWidget` for displaying errors without crashing
- Provide retry functionality where possible

## Registry Pattern
- MC shell may only instantiate panes via the registry
- Menubar uses registry keys, not imports
- Pane switching = lookup + instantiate + mount