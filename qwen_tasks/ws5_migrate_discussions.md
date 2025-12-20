# WS5 - Migrate CLI Discussions to Sessions

## Overview
This task implements Phase WS5 (Migrate CLI Discussions to Sessions) of the Work & Session Framework track for the Maestro project. This migrates the existing CLI discussion system (Phase CLI3) to use the new work session framework with breadcrumb tracking.

## Implementation Summary

### Files Created/Updated

#### New Files
- `maestro/templates/discussion.py` - Discussion templates for track/phase/general discussions
- `maestro/discussion.py` - DiscussionSession class with editor and terminal modes
- `tests/test_discussion_migration.py` - Comprehensive test suite

#### Updated Files
- `maestro/commands/discuss.py` - Updated to use work sessions and breadcrumbs
- `maestro/commands/track.py` - Added discuss command support 
- `maestro/commands/phase.py` - Added discuss command support
- `maestro/commands/task.py` - Added discuss command support
- `maestro/commands/work.py` - Added discuss functionality
- `maestro/commands/__init__.py` - Updated imports
- `maestro/main.py` - Already had discuss command integration

### Key Features Implemented

1. **DiscussionSession Class** - Wrapper around WorkSession for discussion mode maintaining CLI3 compatibility
2. **Session-Aware Commands** - All discussion commands (track discuss, phase discuss, task discuss, general discuss) now create work sessions
3. **Breadcrumb Tracking** - Each interaction in discussion creates a breadcrumb for audit trail
4. **Resume Functionality** - Sessions can be resumed from where they left off
5. **Backward Compatibility** - All existing CLI3 workflows still work

### Discussion Templates
- `TRACK_DISCUSSION_TEMPLATE` - For track-specific discussions
- `PHASE_DISCUSSION_TEMPLATE` - For phase-specific discussions  
- `GENERAL_DISCUSSION_TEMPLATE` - For general discussions

### Command Structure
- `maestro discuss` - General discussion with optional --track, --phase, --task flags
- `maestro track <id> discuss` - Track-specific discussion
- `maestro phase <id> discuss` - Phase-specific discussion
- `maestro task <id> discuss` - Task-specific discussion
- `maestro work discuss <entity_type> <entity_id>` - Work-focused discussion

### Command Options
- `--mode [editor|terminal]` - Discussion mode selection
- `--resume <session_id>` - Resume previous discussion session
- `--dry-run` - Preview actions without executing

## Technical Details

### Session Creation
All discussion commands now create `WorkSession` objects with:
- `session_type="discussion"`
- `related_entity` containing track_id, phase_id, or task_id
- Proper metadata and breadcrumbs directory

### Breadcrumb Integration
Every user/AI interaction during discussions creates a breadcrumb with:
- Timestamp
- Prompt and response
- Model used
- Token count and cost estimation
- Any tools called or files modified

### Context Handling
- Track discussions use `build_track_context()` 
- Phase discussions use `build_phase_context()`
- Task discussions use `build_task_context()`
- General discussions use generic context

## Migration Strategy
- Backward compatibility maintained for existing CLI3 workflows
- New session infrastructure used transparently
- Old discussion data can be migrated (future enhancement)
- Command-line interface remains unchanged from user perspective

## Testing Results
- 15 test cases pass covering all functionality
- Session creation and management
- Editor and terminal modes
- Command processing
- Breadcrumb creation and tracking
- Resume functionality
- Action generation from discussion history

## Success Criteria Met
- [x] Can start track discuss and create session
- [x] Can start phase discuss and create session
- [x] Can start general discuss and create session
- [x] Editor mode works as before
- [x] Terminal mode works as before
- [x] /done generates actions as before
- [x] /quit cancels session
- [x] Breadcrumbs created for each interaction
- [x] Can view discussion history
- [x] Can resume interrupted discussions
- [x] All tests pass
- [x] Existing CLI3 workflows still work