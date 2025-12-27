# P1 Sprint 2.1: Discuss Session Format Canonicalization

**Date**: 2025-12-27
**Sprint**: P1 Sprint 2.1 - Replay Hardening + Session Format Upgrade

## Overview

This document defines the canonical session storage format for the discuss subsystem, ensuring deterministic replay, clean audit trails, and backward compatibility.

## Current State (Pre-Sprint 2.1)

### Storage Locations

1. **Work Sessions** (including discussions via `DiscussionSession`):
   - Path: `docs/sessions/<uuid>/session.json`
   - Format: Single JSON file with metadata
   - Conversation history: `docs/sessions/<uuid>/breadcrumbs/*.json`
   - Session ID: UUID (e.g., `11c021f4-300b-488e-9e8a-1c370c5c41ec`)

2. **Discuss Artifacts** (results from AI-driven discuss):
   - Path: `docs/maestro/ai/artifacts/<session_id>_results.json`
   - Format: Single JSON file with all data
   - Session ID: Timestamp-based (e.g., `discuss_global_20251227_143025`)

### Problems

- **Dual storage systems**: Work sessions vs discuss artifacts with no unification
- **No JSONL format**: Cannot stream/append events deterministically
- **No final_json marker**: Hard to extract final payload for replay
- **Timestamp-based IDs**: Not stable for replay references
- **No replay tracking**: No audit trail of replay runs

## Canonical Format (Post-Sprint 2.1)

### Storage Layout

```
./docs/maestro/sessions/discuss/<session_id>/
  meta.json          - Session metadata
  transcript.jsonl   - Event stream (one JSON event per line)
```

### Session ID Format

- Use UUID (stable across runs): `<uuid>`
- Examples: `f3a1b2c3-4d5e-6f7a-8b9c-0d1e2f3a4b5c`

### meta.json Schema

```json
{
  "session_id": "<uuid>",
  "context": {
    "kind": "task|phase|track|repo|issues|runbook|workflow|solutions|global",
    "ref": "<entity_id or null>",
    "router_reason": "Explanation of why this context was chosen"
  },
  "contract_type": "global|track|phase|task",
  "created_at": "2025-12-27T14:30:25.123456",
  "updated_at": "2025-12-27T14:35:12.654321",
  "status": "open|closed",
  "final_json_present": true,
  "engine": "qwen|claude|etc",
  "model": "default|specific-model",
  "initial_prompt": "User's original request..."
}
```

### transcript.jsonl Schema

Each line is a JSON event with this structure:

```json
{"ts": "2025-12-27T14:30:25.123456", "type": "user_message", "payload": {"content": "..."}}
{"ts": "2025-12-27T14:30:28.456789", "type": "assistant_message", "payload": {"content": "..."}}
{"ts": "2025-12-27T14:35:12.654321", "type": "final_json", "payload": {"patch_operations": [...]}}
{"ts": "2025-12-27T14:36:00.123456", "type": "replay_run", "payload": {"dry_run": false, "result": "REPLAY_OK", "ops_count": 3}}
{"ts": "2025-12-27T14:37:00.123456", "type": "error", "payload": {"message": "Invalid JSON schema", "details": "..."}}
```

#### Event Types

1. **user_message**: User input
   - `payload.content`: The user's message text

2. **assistant_message**: AI response
   - `payload.content`: The AI's response text
   - `payload.model`: Model used (optional)

3. **final_json**: Final JSON payload from AI (via `/done` command)
   - `payload.patch_operations`: List of PatchOperation objects
   - This event marks the end of the discussion phase
   - Only one `final_json` event per session

4. **replay_run**: Record of a replay operation
   - `payload.dry_run`: Boolean (was this a dry-run?)
   - `payload.result`: "REPLAY_OK" | "REPLAY_FAIL"
   - `payload.ops_count`: Number of operations applied
   - `payload.error`: Error message if failed (optional)

5. **error**: Error during discussion or replay
   - `payload.message`: Error message
   - `payload.details`: Additional error details (optional)

## Backward Compatibility

### Legacy Format 1: Work Sessions (`docs/sessions/<uuid>/`)

- **Loader**: Check if path exists as `docs/sessions/<uuid>/session.json`
- **Migration**: Read session.json, extract breadcrumbs, convert to canonical format
- **Write**: Always write new canonical format

### Legacy Format 2: Discuss Artifacts (`docs/maestro/ai/artifacts/<session_id>_results.json`)

- **Loader**: Check if path ends with `_results.json`
- **Migration**: Read results.json, extract `final_json` from transcript, convert to canonical format
- **Write**: Always write new canonical format

### Compatibility Rule

1. **Read**: Support all formats (canonical, legacy work sessions, legacy artifacts)
2. **Write**: Always use canonical format for new sessions
3. **No deletion**: Never delete legacy files during migration (read-only migration)

## Migration Strategy

### Phase 1 (This Sprint)

- Implement canonical format writers
- Implement legacy loaders (read-only)
- Update `save_discussion_artifacts()` to write canonical format
- Update replay to read from canonical or legacy

### Phase 2 (Future)

- Optional migration tool to bulk-convert legacy sessions
- Deprecation notice for legacy formats

## Replay Contract

### Deterministic Replay Requirements

1. **No AI engine calls**: Replay extracts `final_json` event from transcript.jsonl
2. **Strict validation**: Invalid JSON fails replay with error event
3. **Audit trail**: Each replay appends `replay_run` event to transcript.jsonl
4. **Dry-run support**: `--dry-run` flag shows planned ops without applying

### Replay Process

1. Load session from `docs/maestro/sessions/discuss/<session_id>/`
2. Read `meta.json` to get context
3. Read `transcript.jsonl` to find `final_json` event
4. If no `final_json` event: fail with actionable error
5. Validate JSON against contract type
6. If valid: apply ops (or dry-run)
7. Append `replay_run` event to transcript.jsonl

## Storage Invariants

- **Project truth**: All discuss sessions under `./docs/maestro/sessions/discuss/**`
- **JSON only**: meta.json and transcript.jsonl (JSONL is newline-delimited JSON)
- **No .maestro/**: Never use `./.maestro` for project state
- **Hub/global**: Future global discuss history may use `$HOME/.maestro/discuss/`

## Implementation Checklist

- [ ] Create `maestro/session_format.py` with canonical writers/loaders
- [ ] Update `save_discussion_artifacts()` to use canonical format
- [ ] Implement legacy loaders for both formats
- [ ] Update `handle_discuss_replay()` to use canonical format
- [ ] Add `final_json` event writing in discussion flow
- [ ] Add `replay_run` event writing in replay flow
- [ ] Add tests for canonical format
- [ ] Add tests for legacy format loaders
