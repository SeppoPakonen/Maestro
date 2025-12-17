# Maestro Time Travel Model

This document describes the time travel, replay, and recovery mechanisms available in Maestro's TimelinePane.

## Core Concepts

### Timeline Events
The timeline records significant events in the Maestro system:
- **runs**: Conversion runs and their execution
- **checkpoints**: Manual and automatic checkpoints
- **semantic decisions**: Integrity check decisions and overrides
- **batch job transitions**: State changes in batch processing
- **aborts/skips/overrides**: Human interventions and system actions

### Lineage Model
Maestro maintains a lineage system for reproducible state management:
- **Immutable History**: Old states and decisions are never overwritten
- **New Lineage Creation**: Replay and branch operations create new run/plan lineages
- **Evidence Linking**: All operations create linked evidence in the Vault

## Time Travel Operations

### Preview (F3)
- **Purpose**: Read-only preview of system state before a specific event
- **Mechanism**: Shows the state without making any changes
- **Safety**: No mutations to system state
- **Lineage Impact**: No new lineage created

### Dry-Run Replay (F5)
- **Purpose**: Simulate running operations from a specific event forward
- **Mechanism**: Executes replay without applying changes
- **Safety**: No actual system modifications
- **Evidence**: Creates evidence log of what would happen
- **Lineage Impact**: No new lineage created

### Apply Replay (F6)
- **Purpose**: Execute actual replay from a specific event forward
- **Mechanism**: Applies changes to recreate state from that point
- **Safety**: Requires confirmation before execution
- **Evidence**: Creates comprehensive evidence of operation
- **Lineage Impact**: Creates new run lineage (no overwrites)

### Explanations (F7)
- **Purpose**: Document understanding of why events occurred
- **Mechanism**: Links explanation notes to timeline events
- **Safety**: No system state changes
- **Evidence**: Creates explanation evidence in Vault
- **Requirements**: User must provide explanation note

### Recovery Branching (F8)
- **Purpose**: Create alternative execution path from specific event
- **Mechanism**: Establishes new plan/run lineage from that point
- **Safety**: No modification of original timeline
- **Evidence**: Creates branching evidence in Vault
- **Lineage Impact**: Creates new plan/run lineage

## Safety Guarantees

### No Silent Rewinds
- All time travel operations are explicit and visible
- Users must specifically choose to use time travel features
- All operations have clear confirmation steps where appropriate

### No Destructive Rollback
- Original timeline is never modified or destroyed
- All operations create new lineages rather than reverting existing ones
- Previous states remain accessible through original lineages

### Evidence Tracking
- Every time travel operation creates evidence in the Vault
- Evidence links to the specific timeline events that triggered it
- Complete audit trail is maintained for all state changes

## Lineage Semantics

### Run Lineage
- When replaying with apply, new run IDs are generated
- Original runs and their artifacts are preserved
- Branch operations create entirely new run sequences

### Plan Lineage
- Recovery branches may create new plan variations
- Original plans remain unchanged and accessible
- Decision trees can diverge based on branching points

### Evidence Lineage
- Each operation creates linked evidence artifacts
- Evidence artifacts reference original timeline events
- Complete chain of custody is maintained

## User Experience Model

### Explicit vs Implicit Operations
- All time travel operations must be initiated by explicit user action
- No automatic or background time travel operations occur
- Users maintain clear awareness of current execution context

### Confirmation Requirements
- Operations that modify system state require explicit confirmation
- Visual indicators show the scope and impact of operations
- Users can review operation details before confirming

### Recovery Workflow
1. Identify problematic timeline event
2. Select appropriate recovery action
3. Review operation details and impact
4. Confirm operation execution
5. Verify results and evidence creation

## Integration with Vault
- All timeline operations create Vault entries
- Timeline events link to related Vault items
- Vault can filter and display items related to timeline events
- Evidence from time travel operations is stored in Vault