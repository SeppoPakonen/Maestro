# P1 Sprint 2: Discuss Subsystem Inventory

**Date**: 2025-12-27
**Sprint**: P1 Sprint 2 - Discuss Router + Resume/Replay Contract

## Overview

This document maps the current state of the discuss subsystem before implementing the router, resume/replay, and session contract improvements.

## CLI Entrypoints

### Top-Level Discuss

**Command**: `maestro discuss [--track ID] [--phase ID] [--task ID] [--mode editor|terminal] [--dry-run] [--resume SESSION_ID]`

**Handler**: `handle_discuss_command(args)` in `maestro/commands/discuss.py:345`

**Current behavior**:
- Determines contract type based on args (track_id, phase_id, task_id)
- Falls back to `ContractType.GLOBAL` if no context specified
- Saves artifacts to `docs/maestro/ai/artifacts/<session_id>_results.json`
- Calls `run_discussion_with_router()` internally
- Applies patch operations after user confirmation (unless --dry-run)

**Current gaps**:
- No actual router logic to detect context from environment
- `--resume` flag exists but not wired to resume functionality
- Session ID is timestamp-based, not stable UUID

### Replay Subcommand

**Command**: `maestro discuss replay PATH [--contract global|track|phase|task] [--dry-run]`

**Handler**: `handle_discuss_replay(args)` in `maestro/commands/discuss.py:549`

**Current behavior**:
- Loads JSON/JSONL payload from path
- Extracts `final_json` from transcript or raw JSON
- Validates against specified or inferred contract
- Applies patch operations after user confirmation (unless --dry-run)

**Current implementation status**: Exists but needs refinement for:
- Deterministic replay without AI engines
- Proper dry-run preview
- Session replay tracking (replay_runs[])

### Context-Specific Discuss Commands

#### Track Discuss

**Command**: `maestro track discuss TRACK_ID [--mode editor|terminal] [--dry-run]`

**Handler**: `handle_track_discuss(track_id, args)` in `maestro/commands/discuss.py:454`

**Wired from**: `maestro/commands/track.py:51`

#### Phase Discuss

**Command**: `maestro phase discuss PHASE_ID [--mode editor|terminal] [--dry-run]`

**Handler**: `handle_phase_discuss(phase_id, args)` in `maestro/commands/discuss.py:619`

**Wired from**: `maestro/commands/phase.py:674,978`

#### Task Discuss

**Command**: `maestro task discuss TASK_ID [--mode editor|terminal] [--dry-run]`

**Handler**: `handle_task_discuss(task_id, args)` in `maestro/commands/discuss.py:714`

**Wired from**: `maestro/commands/task.py:798,873,1140`

#### Plan Discuss

**Command**: `maestro plan discuss PLAN_ID`

**Handler**: `handle_plan_discuss()` in `maestro/commands/plan.py:189`

**Note**: Uses different infrastructure (prompt_contract.py), may need alignment

### Work Session Integration

**Commands**:
- `maestro work track TRACK_ID discuss`
- `maestro work phase PHASE_ID discuss`
- `maestro work task TASK_ID discuss`

**Handler**: References in `maestro/commands/work.py:968`

**Integration**: Uses `DiscussionSession` wrapper from `maestro/discussion.py`

## Core Modules

### 1. Router Module

**File**: `maestro/ai/discuss_router.py`

**Key classes**:
- `DiscussionRouter` - Main router class
- `JsonContract` - Contract definition with validation
- `PatchOperation` / `PatchOperationType` - Operations model

**Key methods**:
- `run_discussion(engine, initial_prompt, mode, json_contract)` - Run AI discussion
- `process_json_payload(payload, json_contract)` - Validate and convert JSON → ops
- `extract_json_from_text(response)` - Extract JSON from AI response
- `save_transcript(topic, content)` - Save to `docs/maestro/ai/transcripts/`

**Current gaps**:
- Router doesn't actually route context; just accepts explicit contract type
- No session metadata storage (context.kind, context.ref, router.reason)
- No deterministic replay support

### 2. Session Wrapper Module

**File**: `maestro/discussion.py`

**Key classes**:
- `DiscussionSession` - Wraps WorkSession for discuss mode

**Key functions**:
- `create_discussion_session(session_type, related_entity, mode)` - Create new session
- `resume_discussion(session_id)` - Resume previous session

**Current behavior**:
- Creates WorkSession under `docs/sessions/<session_id>/session.json`
- Integrates with breadcrumb system for conversation history
- Supports editor and terminal modes

**Current gaps**:
- Resume function exists but not wired to CLI
- No router decision logic
- Session metadata doesn't store context selection reasoning

### 3. Context Builder Module

**File**: `maestro/ai/discussion.py`

**Key functions**:
- `build_track_context(track_id)` → DiscussionContext
- `build_phase_context(phase_id)` → DiscussionContext
- `build_task_context(task_id)` → DiscussionContext

**Key classes**:
- `DiscussionContext` - Context with allowed_actions, system_prompt
- `Discussion` - Base discussion class (editor/terminal modes)
- `DiscussionResult` - Final result with messages + actions

**Current behavior**: Builds context from data files (todo.md, phases/*.md)

### 4. OPS Application Module

**File**: `maestro/commands/discuss.py`

**Key functions**:
- `apply_patch_operations(patch_operations)` - Apply PatchOperations to repo truth
- `save_discussion_artifacts(...)` - Save to `docs/maestro/ai/artifacts/`
- `update_artifact_status(session_id, status, ...)` - Update artifact after apply

**Supported operations**:
- `ADD_TRACK`, `ADD_PHASE`, `ADD_TASK`
- `MOVE_TASK`, `EDIT_TASK_FIELDS`
- `MARK_DONE`, `MARK_TODO`

**Current gaps**:
- No context-aware OPS gating (e.g., block track.add in task context)
- No cross-context override mechanism

## Session and Transcript Storage

### 1. Session Artifacts (Results)

**Path**: `docs/maestro/ai/artifacts/<session_id>_results.json`

**Schema**:
```json
{
  "session_id": "discuss_<contract_type>_<timestamp>",
  "timestamp": "ISO8601",
  "engine": "qwen",
  "model": "default",
  "contract_type": "global|track|phase|task",
  "initial_prompt": "...",
  "patch_operations": [...],
  "transcript": {...},
  "status": "pending|applied|cancelled|dry_run|invalid_json|no_operations"
}
```

**Update mechanism**: `update_artifact_status()` adds:
- `applied_operations`: List of ops actually applied
- `applied_at`: ISO timestamp
- `error_message`: Error details if failed

### 2. Transcripts

**Path**: `docs/maestro/ai/transcripts/<topic>/<timestamp>_transcript.json`

**Schema**:
```json
{
  "timestamp": "<timestamp>",
  "content": "<raw_transcript_or_messages>"
}
```

**Current gaps**:
- Not JSONL format (hard to stream/append)
- No final_json event marker
- No deterministic extraction for replay

### 3. Work Sessions

**Path**: `docs/sessions/<session_id>/session.json`

**Schema** (from `maestro/work_session.py`):
```json
{
  "session_id": "UUID",
  "session_type": "discussion|work_track|work_phase|work_task|...",
  "parent_session_id": "UUID or null",
  "status": "running|paused|completed|interrupted|failed",
  "created": "ISO8601",
  "modified": "ISO8601",
  "related_entity": {"track_id": "...", "phase_id": "...", "task_id": "..."},
  "breadcrumbs_dir": "docs/sessions/<session_id>/breadcrumbs",
  "metadata": {...}
}
```

**Breadcrumbs**: `docs/sessions/<session_id>/breadcrumbs/<breadcrumb_id>.json`

**Current gaps**:
- No `context.kind` / `context.ref` stored in session metadata
- No `router.reason` for audit trail
- No `replay_runs[]` array for replay tracking

### 4. Storage Invariants

**Project truth**: `./docs/maestro/**` (JSON only)
**Hub/global**: `$HOME/.maestro/**` (if needed)

**Current compliance**: ✅ All discuss artifacts under `docs/maestro/` or `docs/sessions/`

## Contracts and Validation

### Current Contract Types

**Enum**: `ContractType` in `maestro/ai/__init__.py`
- `GLOBAL`
- `TRACK`
- `PHASE`
- `TASK`

### Contract Definitions

**File**: `maestro/ai/contracts.py`

**Contracts**:
- `GlobalContract: JsonContract` - Global actions (all ops allowed)
- `TrackContract: JsonContract` - Track-scoped actions
- `PhaseContract: JsonContract` - Phase-scoped actions
- `TaskContract: JsonContract` - Task-scoped actions

**Validation**: Each contract has `validation_func` and `allowed_operations` list

**Current gaps**:
- No context-aware OPS filtering (blocking cross-context ops)
- No `--allow-cross-context` override flag

## Gaps Summary

### P0 (Blocking Sprint Goals)

1. **No Router Decision Logic**: `maestro discuss` doesn't detect context from environment (active work session, current path, repo state)
2. **Resume Not Wired**: `--resume` flag exists but `resume_discussion()` not called from CLI
3. **Session Metadata Incomplete**: No `context.kind`, `context.ref`, `router.reason` stored
4. **Replay Not Deterministic**: Replay still calls AI engines; needs pure JSON extraction + apply
5. **No Replay Tracking**: No `replay_runs[]` array to log replay attempts

### P1 (Required for Sprint)

1. **No Context Transfer**: Router doesn't transfer to context-specific handlers (e.g., `task discuss`)
2. **No OPS Gating**: OPS application doesn't enforce context constraints
3. **No Cross-Context Override**: No `--allow-cross-context` flag for exceptional ops
4. **Transcript Format**: Not JSONL with clear `final_json` event

### P2 (Nice to Have)

1. **Plan Discuss Alignment**: `plan discuss` uses separate infrastructure, should use router
2. **Session ID Format**: Currently timestamp-based, should be stable UUID
3. **Repo/Issues/Runbook/Workflow/Solutions Discuss**: Not implemented yet (per SIGNATURES.md)

## Next Steps (Phase 1+)

Per task requirements:

1. **Phase 1**: Implement top-level router with context detection + transfer mechanism
2. **Phase 2**: Stable session IDs, JSONL transcripts, context metadata storage
3. **Phase 3**: Wire `discuss resume` and `discuss replay` (deterministic, no AI)
4. **Phase 4**: Context-aware OPS gating
5. **Phase 5**: Tests + fixtures (no AI dependency)
6. **Phase 6**: Update runbooks EX-21..EX-28
7. **Phase 7**: Update v3 CLI docs
