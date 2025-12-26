# WF-06: AI-driven task execution with Work Sessions and multi-session resume

## Metadata

```
id: WF-06
title: AI-driven task execution with Work Sessions and multi-session resume
tags: [work, ai, sessions, resume, stream-json, breadcrumbs, ipc, state-update]
entry_conditions: |
  - Operator has a task to work on (track, phase, issue, or specific task)
  - AI engine is configured and accessible
  - Repository is initialized with Maestro
exit_conditions: |
  - AI engine completes the task or reaches a stopping condition
  - Work Session is marked as completed or paused
  - Task status is updated (DONE if completed, or remains TODO if paused)
artifacts_created: |
  - Work Session directory with session.json
  - Breadcrumb files in session's breadcrumbs directory
  - AI transcript logs in docs/logs/ai/
  - Optional session exports (JSON/Markdown)
failure_semantics: |
  - Invalid/non-JSON final output results in HARD STOP
  - Session remains active but task is not marked as done
  - Error is recorded in session metadata
  - Breadcrumbs up to failure point are preserved
related_commands: |
  - maestro work task <id>
  - maestro work track <id>
  - maestro work phase <id>
  - maestro work issue <id>
  - maestro wsession list/show/breadcrumbs/timeline/stats
  - maestro ai sync
notes_on_scope: |
  - Focuses on running work; does not define scenario-specific planning or repo scanning
  - Covers multi-session resume capabilities within single Work Session
  - Includes stream-JSON transcript vs curated breadcrumbs distinction
```

## Core Narrative Flow

    ### 1. Operator Initiates Work on Task

    The operator triggers work on a specific task using one of the work commands:
    - `maestro work task <task_id>`
    - `maestro work track <track_id>`
    - `maestro work phase <phase_id>`
    - `maestro work issue <issue_id>`

    ### 2. Maestro Orchestrator Creates/Reuses Work Session

    The outer Maestro orchestrator ensures a Work Session exists for the task:

    - **Creates new session** if none exists for the task:
      - Generates unique session ID using UUID
      - Creates session directory structure: `docs/sessions/<session_id>/`
      - Creates breadcrumbs subdirectory: `docs/sessions/<session_id>/breadcrumbs/`
      - Initializes `session.json` with session metadata
      - Sets initial status to "running"

    - **Reuses existing session** if continuing work:
      - Locates existing session by task ID or session ID
      - Verifies session status (should be "running" or "paused")
      - Resumes with same session context

    ### 3. AI Engine Session Initiation

    Maestro starts an AI engine session with the following process:

    - **Context preparation**: Builds task-specific prompt with:
      - Task details (ID, name, description)
      - Phase and track context
      - Current Work Session ID (serving as the `wsession cookie/run-id`)
      - Workflow instructions for the AI (including the `wsession cookie/run-id` for multi-process targeting)

    - **Resume token behavior**:
      - If continuing from previous AI session, uses resume ID from session metadata
      - If starting new AI session, begins fresh interaction

    - **Engine selection**: Based on configuration, selects appropriate AI engine (Claude, Qwen, Gemini, Codex)

    ### 4. AI Session Execution with Transcript Capture

    During AI session execution:

    - **Stream-JSON events captured**: AI engine produces stream events that are captured in AI transcript store (`docs/logs/ai/<engine>/`)
      - Each interaction generates timestamped log files
      - Events include: init, delta, message, result, error
      - Full JSON event stream is preserved for debugging

    - **Breadcrumb updates**: Optionally, AI emits progress updates that are written to the Work Session as "breadcrumbs"
      - Breadcrumbs are curated, operator-relevant progress notes
      - Each breadcrumb contains: timestamp, prompt, response, tools called, files modified, token counts, cost
      - Stored in `docs/sessions/<session_id>/breadcrumbs/<depth_level>/<timestamp>.json`

    ### 5. Session Continuation and Multi-Session Resume

    AI sessions can span multiple interactions under the same Work Session:

    - **Session completion criteria**: AI session ends when:
      - AI voluntarily stops (e.g., completes current task step)
      - Time/iteration limits reached
      - Error occurs requiring session pause

    - **Continuation mechanism**: Work Session remains active while AI session ends
      - Next AI session can resume under same Work Session
      - Uses `maestro ai sync` command to transition between tasks within session
      - Maintains session continuity and context

    ### 6. Final JSON Contract and Validation

    Upon AI completion:

    - **Final JSON result**: AI is expected to produce a structured JSON result
    - **Schema validation**: Maestro validates JSON against expected schema/contract
    - **Success path**: On valid JSON:
      - Updates task status to "DONE"
      - Updates related phase/track status if appropriate
      - Marks Work Session as "completed"
      - Preserves all breadcrumbs and transcripts

    - **Failure path**: On invalid/non-JSON output:
      - **HARD STOP** - work halts immediately
      - Session status marked as "failed"
      - Error recorded in session metadata
      - Task remains in TODO state
      - All breadcrumbs up to failure point preserved

    ## Branch Boundaries Note

    **Important**: Maestro operates strictly on the current Git branch. Switching branches during an active `maestro work` session is **unsupported** and risks corrupting the work session state and leading to inconsistent results. This is an **operational rule**. Users must ensure they complete or explicitly abandon a work session before switching branches.
## AI Transcript vs Work Session Log

### Transcript: Exhaustive Stream Events
- Raw assistant text, tool events, and all interaction details
- Stored in `docs/logs/ai/<engine>/` with timestamped files
- Contains full JSON event stream for debugging and analysis
- Includes init, delta, message, result, and error events
- Preserved for audit trail and replay purposes

### Work Session: Curated Progress Updates
- Operator-relevant breadcrumbs/milestone notes/decisions
- Stored in `docs/sessions/<session_id>/breadcrumbs/<depth_level>/`
- Each breadcrumb is a structured JSON file with key information
- Focuses on significant progress rather than raw transcript
- Designed for human consumption and progress tracking

### Relationship
- Work Session references transcript ranges or session IDs via breadcrumb metadata
- Each breadcrumb links to the relevant AI session and transcript entries
- Transcript provides detail; breadcrumbs provide summary and progress tracking

## Process Topology

The system uses a three-party call chain:

### 1. Outer Maestro Process (Orchestrator)
- Main CLI process that coordinates work sessions
- Manages session lifecycle and state
- Coordinates with AI engines
- Handles final validation and state updates

### 2. AI Engine Process (Claude/Codex/Gemini/Qwen adapter)
- Individual AI engine subprocess
- Handles actual AI interaction and streaming
- Communicates via subprocess pipes
- Produces stream-JSON events

### 3. Inner Maestro Invocation (Task Sync)
- When AI completes a task, it calls `maestro ai sync`
- This is a nested Maestro invocation to get next task
- Uses shared memory or file-based coordination
- Maintains session continuity

### Communication Mechanism
- **Subprocess pipes**: Used for AI engine communication
- **File-based coordination**: `docs/ai_sync.json` for task synchronization (keyed by `wsession cookie/run-id`)
- **Log files**: For persistent transcript storage

## Command Contracts

### Task Work Entrypoint Command
- **Command**: `maestro work task <id>` (and track/phase/issue variants)
- **Inputs**: Task ID, optional flags (--simulate, etc.)
- **Outputs**: Work Session creation, AI interaction, breadcrumbs
- **Exit codes**: 0 (success), 1 (error), 130 (interrupted)
- **Hard stops**: On invalid AI output, permission errors

### Work Session Management Commands
- **List sessions**: `maestro wsession list` 
  - Inputs: Optional filters (--type, --status, --since)
  - Outputs: Table of sessions with status, type, timestamps
  - Exit codes: 0 (success), 1 (error)

- **Show session**: `maestro wsession show <session_id>`
  - Inputs: Session ID (or "latest")
  - Outputs: Detailed session information and breadcrumbs
  - Exit codes: 0 (success), 1 (not found/error)

- **Show breadcrumbs**: `maestro wsession breadcrumbs <session_id>`
  - Inputs: Session ID, optional filters (--summary, --depth, --limit)
  - Outputs: List of breadcrumb entries with details
  - Exit codes: 0 (success), 1 (not found/error)

- **Show timeline**: `maestro wsession timeline <session_id>`
  - Inputs: Session ID
  - Outputs: Chronological list of all session events
  - Exit codes: 0 (success), 1 (not found/error)

- **Show stats**: `maestro wsession stats <session_id>`
  - Inputs: Session ID, optional --tree flag
  - Outputs: Session statistics (tokens, cost, duration, etc.)
  - Exit codes: 0 (success), 1 (not found/error)

### AI Engine Invocation Commands
- **Claude**: `maestro ai claude` (and qwen, gemini, codex)
  - Inputs: --one-shot, --stdin, --resume, --model, --quiet, --verbose
  - Outputs: AI interaction with streaming
  - Exit codes: 0 (success), 1 (engine error), 130 (interrupted)
  - Session ID tracking via stream-JSON parsing

## Tests Implied by This Scenario

### Unit Tests
- **Work session creation/reuse**: Test session creation with unique IDs and directory structure
- **Resume token handling**: Test session resume functionality with existing session metadata
- **Stream event parsing and storage**: Test JSON event parsing from AI engines
- **Breadcrumb append semantics**: Test breadcrumb creation, validation, and storage
- **Final JSON contract validation**: Test schema validation and hard stop behavior
- **Task completion state transitions**: Test task status updates on completion

### Integration Tests
- **Two-step resume**: AI session 1 ends early, session 2 completes, same work session
  - Test that session maintains continuity across AI sessions
  - Verify breadcrumbs from both sessions are preserved
  - Confirm final task status update occurs correctly

- **Invalid JSON final output**: Invalid JSON final output ⇒ work halts; session remains; task not marked done
  - Test HARD STOP behavior on invalid AI output
  - Verify session marked as "failed"
  - Confirm task remains in TODO state

- **Breadcrumb-only updates**: Ensure they're persisted and queryable
  - Test that breadcrumbs are created for each AI interaction
  - Verify breadcrumbs can be listed and queried via wsession commands
  - Confirm breadcrumb metadata (tokens, cost, tools called) is accurate