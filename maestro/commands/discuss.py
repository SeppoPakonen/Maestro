"""Discussion command implementation with work session integration."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Tuple

from maestro.ai import (
    ActionProcessor,
    ContractType,
    DiscussionMode,
    ExternalCommandClient,
    GlobalContract,
    PhaseContract,
    TaskContract,
    TrackContract,
    build_phase_context,
    build_task_context,
    build_track_context,
    DiscussionRouter,
    JsonContract,
    PatchOperation,
    PatchOperationType,
)
from maestro.ai.manager import AiEngineManager
from maestro.ai.cache import AiCacheStore
from maestro.data import parse_config_md
from maestro.discussion import DiscussionSession, create_discussion_session, resume_discussion
from maestro.work_session import (
    SessionType,
    load_session,
    save_session,
    find_session_by_id,
    list_sessions,
    is_session_closed,
)
from maestro.breadcrumb import list_breadcrumbs, get_breadcrumb_summary
from maestro.session_format import (
    create_session,
    write_session,
    load_session as load_discuss_session,
    append_event,
    update_session_status,
    extract_final_json,
    get_session_path,
    create_session_id,
    TranscriptEvent
)
from maestro.repo_lock import RepoLock
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class DiscussContext:
    """Router-selected discussion context."""
    kind: str  # "task", "phase", "track", "repo", "global", etc.
    ref: Optional[str]  # ID of the entity (task_id, phase_id, etc.)
    reason: str  # Explanation of why this context was chosen
    contract_type: ContractType  # Corresponding contract type


def choose_mode(mode_arg: Optional[str]) -> DiscussionMode:
    if mode_arg:
        return DiscussionMode(mode_arg.lower())
    config = parse_config_md("docs/config.md")
    # Use the flat keys from parse_config_md
    discussion_mode = config.get("discussion_mode") if config else None
    if discussion_mode in ("editor", "terminal"):
        return DiscussionMode(discussion_mode)
    if os.environ.get("VISUAL") or os.environ.get("EDITOR"):
        return DiscussionMode.EDITOR
    return DiscussionMode.TERMINAL


def _context_kind_to_contract(kind: Optional[str]) -> ContractType:
    context_map = {
        "task": ContractType.TASK,
        "phase": ContractType.PHASE,
        "track": ContractType.TRACK,
        "repo": ContractType.GLOBAL,
        "issues": ContractType.GLOBAL,
        "runbook": ContractType.GLOBAL,
        "workflow": ContractType.GLOBAL,
        "solutions": ContractType.GLOBAL,
        "global": ContractType.GLOBAL,
    }
    return context_map.get(kind or "global", ContractType.GLOBAL)


def _context_from_work_session(session, reason: str) -> DiscussContext:
    kind = None
    ref = None
    if session.context:
        kind = session.context.get("kind")
        ref = session.context.get("ref")
    if not kind:
        related = session.related_entity or {}
        if related.get("task_id"):
            kind = "task"
            ref = related.get("task_id")
        elif related.get("phase_id"):
            kind = "phase"
            ref = related.get("phase_id")
        elif related.get("track_id"):
            kind = "track"
            ref = related.get("track_id")
    if not kind:
        kind = "global"
    return DiscussContext(
        kind=kind,
        ref=ref,
        reason=reason,
        contract_type=_context_kind_to_contract(kind),
    )


def _resolve_explicit_wsession(args) -> tuple[Optional[tuple], Optional[str]]:
    if not getattr(args, "wsession", None):
        return None, None
    wsession_result = find_session_by_id(args.wsession)
    if not wsession_result:
        return None, f"Work session '{args.wsession}' not found."
    if is_session_closed(wsession_result[0]):
        return None, f"Work session '{wsession_result[0].session_id}' is closed."
    return wsession_result, None


def _detect_discuss_context(args) -> DiscussContext:
    """
    Router decision procedure: detect appropriate discussion context.

    Priority:
    1. Explicit flags (--task, --phase, --track, --context)
    2. Active work session
    3. Fall back to global

    Returns:
        DiscussContext with kind, ref, reason, and contract_type
    """
    # Priority 1: Explicit context flags
    if hasattr(args, 'task_id') and args.task_id:
        return DiscussContext(
            kind="task",
            ref=args.task_id,
            reason=f"Explicit --task flag: {args.task_id}",
            contract_type=ContractType.TASK
        )

    if hasattr(args, 'phase_id') and args.phase_id:
        return DiscussContext(
            kind="phase",
            ref=args.phase_id,
            reason=f"Explicit --phase flag: {args.phase_id}",
            contract_type=ContractType.PHASE
        )

    if hasattr(args, 'track_id') and args.track_id:
        return DiscussContext(
            kind="track",
            ref=args.track_id,
            reason=f"Explicit --track flag: {args.track_id}",
            contract_type=ContractType.TRACK
        )

    if hasattr(args, 'context') and args.context:
        contract_type = _context_kind_to_contract(args.context)
        return DiscussContext(
            kind=args.context,
            ref=None,
            reason=f"Explicit --context flag: {args.context}",
            contract_type=contract_type
        )

    # Priority 2: Explicit work session binding
    if getattr(args, "_wsession", None) is not None:
        return _context_from_work_session(
            args._wsession,
            reason=f"Explicit --wsession: {args._wsession.session_id}"
        )

    # Priority 2: Check for active work session (if allowed)
    if getattr(args, "allow_active_session", None) is True:
        try:
            active_sessions = [
                session for session in list_sessions()
                if session.status in ["running", "paused"]
            ]
            if active_sessions:
                active_sessions.sort(key=lambda s: s.modified, reverse=True)
                most_recent = active_sessions[0]
                setattr(args, "_active_wsession_id", most_recent.session_id)
                return _context_from_work_session(
                    most_recent,
                    reason=f"Active work session {most_recent.session_id}",
                )
        except Exception:
            # If we can't detect active sessions, fall through to default
            pass

    # Priority 3: Fall back to global context
    return DiscussContext(
        kind="global",
        ref=None,
        reason="No explicit context or active work session; defaulting to global",
        contract_type=ContractType.GLOBAL
    )


def run_discussion_with_session(discussion_session: DiscussionSession, dry_run: bool = False) -> int:
    # Run the discussion based on the mode
    if discussion_session.mode == "editor":
        result = discussion_session.run_editor_mode()
    else:
        result = discussion_session.run_terminal_mode()

    # Process actions if any were generated
    if hasattr(result, 'actions') and result.actions:
        # Get context to determine allowed actions
        context = discussion_session._get_context_for_session()
        processor = ActionProcessor(dry_run=dry_run)
        errors = processor.validate_actions(result.actions, context.allowed_actions)

        if errors:
            print("[System] Action validation errors:")
            for err in errors:
                print(f"- {err}")
        else:
            action_result = processor.execute_actions(result.actions)
            if action_result.summary:
                print("[System] Action summary:")
                for line in action_result.summary:
                    print(f"- {line}")
            if action_result.errors:
                print("[System] Action execution errors:")
                for err in action_result.errors:
                    print(f"- {err}")

    # Print session summary
    summary = get_breadcrumb_summary(discussion_session.work_session.session_id)
    print(f"[System] Discussion session completed. Session ID: {discussion_session.work_session.session_id}")
    print(f"[System] Total interactions: {summary['total_breadcrumbs']}")
    print(f"[System] Total tokens: {summary['total_tokens']['input'] + summary['total_tokens']['output']:,}")
    print(f"[System] Estimated cost: ${summary['total_cost']:.2f}")

    return 0


def _load_replay_payload(path: Path) -> Tuple[Optional[Any], Optional[str], Optional[str]]:
    """Load a replay payload from JSON/JSONL or raw text."""
    if not path.exists():
        return None, None, f"Replay transcript not found: {path}"

    contract_hint = None
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        payload = None
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                return None, None, f"Invalid JSONL entry: {exc}"
            if isinstance(event, dict):
                if event.get("contract_type"):
                    contract_hint = event.get("contract_type")
                for key in ("final_json", "final", "payload", "json"):
                    if key in event:
                        payload = event[key]
        if payload is None:
            return None, contract_hint, "No final JSON payload found in transcript."
        return payload, contract_hint, None

    if suffix == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return None, None, f"Invalid JSON transcript: {exc}"
        if isinstance(data, dict):
            contract_hint = data.get("contract_type")
            if "final_json" in data:
                return data["final_json"], contract_hint, None
            if "transcript" in data and isinstance(data["transcript"], dict):
                transcript = data["transcript"]
                if transcript.get("contract_type"):
                    contract_hint = transcript.get("contract_type")
                if "final_json" in transcript:
                    return transcript["final_json"], contract_hint, None
            if "patch_operations" in data:
                return data["patch_operations"], contract_hint, None
        return data, contract_hint, None

    return path.read_text(encoding="utf-8"), contract_hint, None


def _resolve_contract_type(contract_value: Optional[str]) -> ContractType:
    if contract_value == ContractType.TRACK.value:
        return ContractType.TRACK
    if contract_value == ContractType.PHASE.value:
        return ContractType.PHASE
    if contract_value == ContractType.TASK.value:
        return ContractType.TASK
    return ContractType.GLOBAL


def apply_patch_operations(patch_operations):
    """Apply the patch operations to the appropriate data sources."""
    from maestro.data.markdown_writer import (
        insert_track_block,
        insert_phase_block,
        insert_task_block,
        update_task_metadata,
        update_phase_metadata,
        update_track_metadata
    )
    from pathlib import Path

    for op in patch_operations:
        if op.op_type == PatchOperationType.ADD_TRACK:
            # Add a new track to docs/todo.md
            track_name = op.data.get('track_name', 'Unnamed Track')
            track_id = op.data.get('track_id', track_name.replace(' ', '-').lower())

            # Create track block content
            track_block = f"## Track: {track_name}\n\n- *track_id*: *{track_id}*\n- *status*: *proposed*\n- *completion*: 0%\n\n"

            # Insert the track
            todo_path = Path('docs/todo.md')
            if todo_path.exists():
                insert_track_block(todo_path, track_block)
            else:
                todo_path.parent.mkdir(parents=True, exist_ok=True)
                todo_path.write_text(track_block)

        elif op.op_type == PatchOperationType.ADD_PHASE:
            # Add a new phase to a track
            phase_name = op.data.get('phase_name', 'Unnamed Phase')
            phase_id = op.data.get('phase_id', phase_name.replace(' ', '-').lower())
            track_id = op.data.get('track_id', 'default')

            # Create phase block content
            phase_block = f"### Phase {phase_id}: {phase_name}\n\n- *phase_id*: *{phase_id}*\n- *status*: *proposed*\n- *completion*: 0\n\n"

            # Insert the phase
            todo_path = Path('docs/todo.md')
            if todo_path.exists():
                insert_phase_block(todo_path, track_id, phase_block)

        elif op.op_type == PatchOperationType.ADD_TASK:
            # Add a new task to a phase
            task_name = op.data.get('task_name', 'Unnamed Task')
            task_id = op.data.get('task_id', f"task-{len(str(task_name))}")
            phase_id = op.data.get('phase_id', 'default')

            # Create task block content
            task_block = f"### Task {task_id}: {task_name}\n\n- *task_id*: *{task_id}*\n- *status*: *proposed*\n\n"

            # Insert the task
            phase_file = Path(f'docs/phases/{phase_id}.md')
            if phase_file.exists():
                insert_task_block(phase_file, task_block)

        elif op.op_type == PatchOperationType.MOVE_TASK:
            # Move a task to a different phase
            task_id = op.data.get('task_id')
            target_phase_id = op.data.get('target_phase_id')
            source_phase_id = op.data.get('source_phase_id')

            # Implementation for moving tasks between phases would go here
            print(f"Moving task {task_id} from phase {source_phase_id} to phase {target_phase_id}")

        elif op.op_type == PatchOperationType.EDIT_TASK_FIELDS:
            # Edit fields of a task
            task_id = op.data.get('task_id')
            fields = op.data.get('fields', {})

            # Update task fields
            phase_file = find_phase_file_for_task(task_id)
            if phase_file:
                for field, value in fields.items():
                    update_task_metadata(phase_file, task_id, field, value)

        elif op.op_type == PatchOperationType.MARK_DONE:
            # Mark an item as done
            item_type = op.data.get('item_type', 'task')
            item_id = op.data.get('item_id')

            if item_type == 'task':
                # Update task status
                phase_file = find_phase_file_for_task(item_id)
                if phase_file:
                    update_task_metadata(phase_file, item_id, 'status', 'done')
            elif item_type == 'phase':
                # Update phase status
                todo_path = Path('docs/todo.md')
                if todo_path.exists():
                    update_phase_metadata(todo_path, item_id, 'status', 'done')
            elif item_type == 'track':
                # Update track status
                todo_path = Path('docs/todo.md')
                if todo_path.exists():
                    update_track_metadata(todo_path, item_id, 'status', 'done')

        elif op.op_type == PatchOperationType.MARK_TODO:
            # Mark an item as todo
            item_type = op.data.get('item_type', 'task')
            item_id = op.data.get('item_id')

            if item_type == 'task':
                # Update task status
                phase_file = find_phase_file_for_task(item_id)
                if phase_file:
                    update_task_metadata(phase_file, item_id, 'status', 'planned')
            elif item_type == 'phase':
                # Update phase status
                todo_path = Path('docs/todo.md')
                if todo_path.exists():
                    update_phase_metadata(todo_path, item_id, 'status', 'planned')
            elif item_type == 'track':
                # Update track status
                todo_path = Path('docs/todo.md')
                if todo_path.exists():
                    update_track_metadata(todo_path, item_id, 'status', 'planned')


def find_phase_file_for_task(task_id: str) -> Optional[Path]:
    """Find the phase file that contains a specific task."""
    from pathlib import Path

    phases_dir = Path('docs/phases')
    if not phases_dir.exists():
        return None

    for phase_file in phases_dir.glob('*.md'):
        content = phase_file.read_text(encoding='utf-8')
        if task_id in content:
            return phase_file

    return None


def save_discussion_artifacts(
    initial_prompt: str,
    patch_operations: list[PatchOperation],
    engine_name: str,
    model_name: str,
    contract_type: ContractType,
    context: Optional[DiscussContext] = None,
    session_id: Optional[str] = None,
    wsession_id: Optional[str] = None
) -> str:
    """Save discussion artifacts using canonical session format.

    Args:
        session_id: Optional pre-generated session ID (for lock integration)
    """
    # Use canonical session format
    session = create_session(
        context_kind=context.kind if context else "global",
        context_ref=context.ref if context else None,
        router_reason=context.reason if context else "No context provided",
        contract_type=contract_type,
        engine=engine_name,
        model=model_name,
        initial_prompt=initial_prompt,
        wsession_id=wsession_id
    )

    # Override session_id if pre-generated (for lock integration)
    if session_id:
        session.meta.session_id = session_id
        session.session_dir = get_session_path(session_id)

    # Add initial prompt as user_message event
    now = datetime.now().isoformat()
    session.transcript.append(TranscriptEvent(
        ts=now,
        type="user_message",
        payload={"content": initial_prompt}
    ))

    # Add final_json event with patch operations
    if patch_operations:
        session.transcript.append(TranscriptEvent(
            ts=datetime.now().isoformat(),
            type="final_json",
            payload={"patch_operations": [{'op_type': op.op_type.value, 'data': op.data} for op in patch_operations]}
        ))
        session.meta.final_json_present = True

    # Write session to disk
    write_session(session)

    return session.meta.session_id


def update_artifact_status(session_id: str, status: str, applied_operations: list = None, error_message: str = None):
    """Update the status of a discussion session and append events."""
    lock = RepoLock()
    try:
        session_dir = get_session_path(session_id)

        # Update session status
        if status == "applied":
            update_session_status(session_dir, "closed", final_json_present=True)
            # Append replay_run event
            if applied_operations:
                append_event(session_dir, TranscriptEvent(
                    ts=datetime.now().isoformat(),
                    type="replay_run",
                    payload={
                        "dry_run": False,
                        "result": "REPLAY_OK",
                        "ops_count": len(applied_operations)
                    }
                ))
            # Release lock when session closes
            lock.release(session_id)
        elif status == "invalid_json":
            update_session_status(session_dir, "open", final_json_present=False)
            # Append error event
            if error_message:
                append_event(session_dir, TranscriptEvent(
                    ts=datetime.now().isoformat(),
                    type="error",
                    payload={"message": error_message}
                ))
            # Keep lock (session still open)
        elif status in ["cancelled", "no_operations"]:
            update_session_status(session_dir, "closed")
            # Release lock when session closes
            lock.release(session_id)
        elif status == "dry_run":
            # Don't close session on dry-run, keep lock
            pass
    except FileNotFoundError:
        # Session may be in legacy format or not found
        # Try legacy artifact format
        artifacts_dir = Path("docs/maestro/ai/artifacts")
        json_path = artifacts_dir / f"{session_id}_results.json"

        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            data['status'] = status
            if applied_operations is not None:
                data['applied_operations'] = applied_operations
                data['applied_at'] = datetime.now().isoformat()
            if error_message:
                data['error_message'] = error_message

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)


def validate_ops_for_context(
    patch_operations: List[PatchOperation],
    context_kind: str,
    allow_cross_context: bool = False
) -> Tuple[bool, Optional[str]]:
    """Validate that operations are allowed in the given context.

    Args:
        patch_operations: List of operations to validate
        context_kind: Context kind (task, phase, track, repo, global)
        allow_cross_context: If True, bypass context restrictions

    Returns:
        Tuple of (is_valid, error_message)
    """
    if allow_cross_context:
        return True, None

    # Define allowed operation prefixes for each context
    context_allowlists = {
        "task": ["task", "issues", "log"],
        "phase": ["phase", "task", "issues", "log"],
        "track": ["track", "phase", "task", "issues", "log"],
        "repo": ["repo", "repoconf", "make", "tu", "log"],
        "issues": ["issues", "task", "log"],
        "runbook": ["runbook", "log"],
        "workflow": ["workflow", "log"],
        "solutions": ["solutions", "issues", "log"],
        "global": None  # Global allows everything
    }

    allowlist = context_allowlists.get(context_kind)
    if allowlist is None:  # Global context
        return True, None

    # Check each operation
    for op in patch_operations:
        op_name = op.op_type.value.lower()
        # Extract prefix (e.g., "add_task" -> "task")
        if "_" in op_name:
            prefix = op_name.split("_", 1)[1]
        else:
            prefix = op_name

        # Check if prefix is in allowlist
        if not any(prefix.startswith(allowed) for allowed in allowlist):
            error_msg = (
                f"Operation '{op.op_type.value}' not allowed in {context_kind} context. "
                f"Allowed prefixes: {', '.join(allowlist)}. "
                f"Rerun with --allow-cross-context to override."
            )
            return False, error_msg

    return True, None


def handle_discuss_command(args) -> int:
    if getattr(args, "discuss_subcommand", None) == "replay":
        return handle_discuss_replay(args)

    if getattr(args, "discuss_subcommand", None) == "resume":
        return handle_discuss_resume(args)

    # Handle resume if requested via deprecated flag
    if getattr(args, "resume", None):
        print("Warning: --resume flag is deprecated; use 'maestro discuss resume <session_id>' instead")
        session_id = args.resume
        try:
            discussion_session = resume_discussion(session_id)
            print(f"Resuming discussion session: {session_id}")
            print(f"Context: {discussion_session.work_session.related_entity}")
            return run_discussion_with_session(discussion_session, getattr(args, "dry_run", False))
        except Exception as e:
            print(f"Error resuming session {session_id}: {e}")
            return 1

    wsession_link = None
    if getattr(args, "wsession", None):
        wsession_result = find_session_by_id(args.wsession)
        if not wsession_result:
            print(f"Work session '{args.wsession}' not found.")
            return 1
        args._wsession, args._wsession_path = wsession_result
        if is_session_closed(args._wsession):
            print(f"Work session '{args._wsession.session_id}' is closed.")
            return 1
        wsession_link = wsession_result

    # Use router to detect context
    context = _detect_discuss_context(args)
    print(f"[Router] Context selected: {context.kind}")
    if context.ref:
        print(f"[Router] Context ref: {context.ref}")
    print(f"[Router] Reason: {context.reason}")

    # Transfer to appropriate context-specific handler if we have a ref
    if context.kind == "task" and context.ref:
        return handle_task_discuss(context.ref, args)
    elif context.kind == "phase" and context.ref:
        return handle_phase_discuss(context.ref, args)
    elif context.kind == "track" and context.ref:
        return handle_track_discuss(context.ref, args)

    # Otherwise, run discussion with detected contract type
    contract_type = context.contract_type

    if not wsession_link and getattr(args, "_active_wsession_id", None):
        wsession_result = find_session_by_id(args._active_wsession_id)
        if wsession_result:
            wsession_link = wsession_result

    # Generate session ID and acquire lock before starting discussion
    session_id = create_session_id()
    lock = RepoLock()

    try:
        lock.acquire(session_id)
    except RuntimeError as e:
        print(f"Error: {e}")
        return 1

    # Use the new router with appropriate contract
    initial_prompt = getattr(args, 'prompt', f'Start a discussion about {context.kind} context.')
    engine = getattr(args, 'engine', 'qwen')  # Default to qwen, could be configured differently
    model = getattr(args, 'model', 'default')  # Model name for metadata
    mode = choose_mode(getattr(args, "mode", None)).value  # Convert to string

    try:
        patch_operations, json_error = run_discussion_with_router(
            initial_prompt=initial_prompt,
            contract_type=contract_type,
            engine=engine,
            mode=mode,
            context_kind=context.kind,
            context_ref=context.ref
        )
    except Exception as e:
        # Release lock on error
        lock.release(session_id)
        raise

    # Save discussion artifacts with context metadata
    session_id_returned = save_discussion_artifacts(
        initial_prompt=initial_prompt,
        patch_operations=patch_operations,
        engine_name=engine,
        model_name=model,
        contract_type=contract_type,
        context=context,
        session_id=session_id,
        wsession_id=wsession_link[0].session_id if wsession_link else None
    )

    print(f"Discussion session ID: {session_id}")
    if wsession_link:
        wsession_session, wsession_path = wsession_link
        wsession_session.metadata["last_discuss_session_id"] = session_id_returned
        save_session(wsession_session, wsession_path)

    if json_error:
        print(f"Error: {json_error}")
        print("Invalid JSON returned; no operations were applied. Retry or resume the discussion.")
        update_artifact_status(session_id, 'invalid_json', error_message=json_error)
        return 1

    # Apply patches if any were generated
    if patch_operations:
        # Show detailed preview of changes
        print("\nProposed changes:")
        for i, op in enumerate(patch_operations, 1):
            print(f"  {i}. {op.op_type.value}: {op.data}")
            # Provide more detailed preview based on operation type
            if op.op_type == PatchOperationType.ADD_TRACK:
                track_name = op.data.get('track_name', 'Unnamed Track')
                track_id = op.data.get('track_id', track_name.replace(' ', '-').lower())
                print(f"      Track: {track_id} - {track_name}")
            elif op.op_type == PatchOperationType.ADD_PHASE:
                phase_name = op.data.get('phase_name', 'Unnamed Phase')
                phase_id = op.data.get('phase_id', phase_name.replace(' ', '-').lower())
                track_id = op.data.get('track_id', 'default')
                print(f"      Phase: {phase_id} - {phase_name} in track {track_id}")
            elif op.op_type == PatchOperationType.ADD_TASK:
                task_name = op.data.get('task_name', 'Unnamed Task')
                task_id = op.data.get('task_id', f"task-{len(str(task_name))}")
                phase_id = op.data.get('phase_id', 'default')
                print(f"      Task: {task_id} - {task_name} in phase {phase_id}")
            elif op.op_type in [PatchOperationType.MARK_DONE, PatchOperationType.MARK_TODO]:
                item_type = op.data.get('item_type', 'task')
                item_id = op.data.get('item_id')
                status = "DONE" if op.op_type == PatchOperationType.MARK_DONE else "TODO"
                print(f"      {item_type.upper()}: {item_id} -> {status}")
            elif op.op_type == PatchOperationType.MOVE_TASK:
                task_id = op.data.get('task_id')
                target_phase_id = op.data.get('target_phase_id')
                source_phase_id = op.data.get('source_phase_id', 'unknown')
                print(f"      TASK: {task_id} -> moved from {source_phase_id} to {target_phase_id}")
            elif op.op_type == PatchOperationType.EDIT_TASK_FIELDS:
                task_id = op.data.get('task_id')
                fields = op.data.get('fields', {})
                print(f"      TASK: {task_id} -> updated fields: {fields}")

        # Ask for confirmation before applying
        if not getattr(args, "dry_run", False):
            response = input("\nApply these changes? [y]es/[n]o/[e]dit manually: ").lower().strip()
            if response in ['y', 'yes']:
                # Apply the patches
                apply_patch_operations(patch_operations)
                print("Changes applied successfully.")
                # Update artifact status to indicate successful application
                applied_ops = [{'op_type': op.op_type.value, 'data': op.data} for op in patch_operations]
                update_artifact_status(session_id, 'applied', applied_ops)
            elif response in ['e', 'edit']:
                # Provide a way to edit the operations manually if needed
                print("Manual editing of operations is not yet implemented in this version.")
                print("Changes not applied.")
                update_artifact_status(session_id, 'cancelled')
            else:
                print("Changes not applied.")
                update_artifact_status(session_id, 'cancelled')
        else:
            print("Dry run: changes not applied.")
            update_artifact_status(session_id, 'dry_run')
    else:
        print("No changes were proposed.")
        update_artifact_status(session_id, 'no_operations')

    return 0


def handle_track_discuss(track_id: Optional[str], args) -> int:
    wsession_link, wsession_error = _resolve_explicit_wsession(args)
    if wsession_error:
        print(wsession_error)
        return 1

    # Generate session ID and acquire lock before starting discussion
    session_id = create_session_id()
    lock = RepoLock()

    try:
        lock.acquire(session_id)
    except RuntimeError as e:
        print(f"Error: {e}")
        return 1

    # Use the new router with TrackContract
    initial_prompt = getattr(args, 'prompt', f'Start a discussion about track {track_id}.')
    engine = getattr(args, 'engine', 'qwen')  # Default to qwen, could be configured differently
    model = getattr(args, 'model', 'default')  # Model name for metadata
    mode = choose_mode(getattr(args, "mode", None)).value  # Convert to string

    try:
        patch_operations, json_error = run_discussion_with_router(
            initial_prompt=initial_prompt,
            contract_type=ContractType.TRACK,
            engine=engine,
            mode=mode,
            context_kind="track",
            context_ref=track_id
        )
    except Exception as e:
        # Release lock on error
        lock.release(session_id)
        raise

    # Save discussion artifacts
    session_id_returned = save_discussion_artifacts(
        initial_prompt=initial_prompt,
        patch_operations=patch_operations,
        engine_name=engine,
        model_name=model,
        contract_type=ContractType.TRACK,
        session_id=session_id,
        wsession_id=wsession_link[0].session_id if wsession_link else None
    )

    print(f"Discussion session ID for track {track_id}: {session_id}")
    if wsession_link:
        wsession_session, wsession_path = wsession_link
        wsession_session.metadata["last_discuss_session_id"] = session_id_returned
        save_session(wsession_session, wsession_path)

    if json_error:
        print(f"Error: {json_error}")
        print("Invalid JSON returned; no operations were applied. Retry or resume the discussion.")
        update_artifact_status(session_id, 'invalid_json', error_message=json_error)
        return 1

    # Apply patches if any were generated
    if patch_operations:
        # Show detailed preview of changes
        print(f"\nProposed changes for track {track_id}:")
        for i, op in enumerate(patch_operations, 1):
            print(f"  {i}. {op.op_type.value}: {op.data}")
            # Provide more detailed preview based on operation type
            if op.op_type == PatchOperationType.ADD_TRACK:
                track_name = op.data.get('track_name', 'Unnamed Track')
                track_id_op = op.data.get('track_id', track_name.replace(' ', '-').lower())
                print(f"      Track: {track_id_op} - {track_name}")
            elif op.op_type == PatchOperationType.ADD_PHASE:
                phase_name = op.data.get('phase_name', 'Unnamed Phase')
                phase_id = op.data.get('phase_id', phase_name.replace(' ', '-').lower())
                track_id_op = op.data.get('track_id', 'default')
                print(f"      Phase: {phase_id} - {phase_name} in track {track_id_op}")
            elif op.op_type == PatchOperationType.ADD_TASK:
                task_name = op.data.get('task_name', 'Unnamed Task')
                task_id_op = op.data.get('task_id', f"task-{len(str(task_name))}")
                phase_id = op.data.get('phase_id', 'default')
                print(f"      Task: {task_id_op} - {task_name} in phase {phase_id}")
            elif op.op_type in [PatchOperationType.MARK_DONE, PatchOperationType.MARK_TODO]:
                item_type = op.data.get('item_type', 'task')
                item_id = op.data.get('item_id')
                status = "DONE" if op.op_type == PatchOperationType.MARK_DONE else "TODO"
                print(f"      {item_type.upper()}: {item_id} -> {status}")
            elif op.op_type == PatchOperationType.MOVE_TASK:
                task_id_op = op.data.get('task_id')
                target_phase_id = op.data.get('target_phase_id')
                source_phase_id = op.data.get('source_phase_id', 'unknown')
                print(f"      TASK: {task_id_op} -> moved from {source_phase_id} to {target_phase_id}")
            elif op.op_type == PatchOperationType.EDIT_TASK_FIELDS:
                task_id_op = op.data.get('task_id')
                fields = op.data.get('fields', {})
                print(f"      TASK: {task_id_op} -> updated fields: {fields}")

        # Ask for confirmation before applying
        if not getattr(args, "dry_run", False):
            response = input("\nApply these changes? [y]es/[n]o/[e]dit manually: ").lower().strip()
            if response in ['y', 'yes']:
                # Apply the patches
                apply_patch_operations(patch_operations)
                print("Changes applied successfully.")
                # Update artifact status to indicate successful application
                applied_ops = [{'op_type': op.op_type.value, 'data': op.data} for op in patch_operations]
                update_artifact_status(session_id, 'applied', applied_ops)
            elif response in ['e', 'edit']:
                # Provide a way to edit the operations manually if needed
                print("Manual editing of operations is not yet implemented in this version.")
                print("Changes not applied.")
                update_artifact_status(session_id, 'cancelled')
            else:
                print("Changes not applied.")
                update_artifact_status(session_id, 'cancelled')
        else:
            print("Dry run: changes not applied.")
            update_artifact_status(session_id, 'dry_run')
    else:
        print("No changes were proposed.")
        update_artifact_status(session_id, 'no_operations')

    return 0


def handle_discuss_resume(args) -> int:
    """Handle the 'discuss resume' subcommand."""
    session_id = getattr(args, "session_id", None)
    if not session_id:
        print("Error: session_id required for resume")
        return 1

    try:
        discussion_session = resume_discussion(session_id)
        print(f"Resuming discussion session: {session_id}")
        print(f"Context: {discussion_session.work_session.related_entity}")
        return run_discussion_with_session(discussion_session, getattr(args, "dry_run", False))
    except FileNotFoundError:
        print(f"Error: Session {session_id} not found")
        print(f"Session directory should be at: docs/sessions/{session_id}/session.json")
        return 1
    except Exception as e:
        print(f"Error resuming session {session_id}: {e}")
        return 1


def handle_discuss_replay(args) -> int:
    """Handle deterministic replay without AI engines.

    Extracts final_json from session transcript and applies operations.
    Never calls AI engines.
    """
    session_id_or_path = getattr(args, "path", "")
    dry_run = getattr(args, "dry_run", False)
    allow_cross_context = getattr(args, "allow_cross_context", False)

    try:
        # Load session (canonical or legacy format)
        session = load_discuss_session(session_id_or_path)
        print(f"[Replay] Loaded session: {session.meta.session_id}")
        print(f"[Replay] Context: {session.meta.context['kind']}")
        if session.meta.context.get('ref'):
            print(f"[Replay] Entity: {session.meta.context['ref']}")

        # Extract final_json from transcript (deterministic, no AI)
        patch_operations_data = extract_final_json(session)
        if not patch_operations_data:
            error_msg = (
                "No final_json event found in transcript. "
                "Run 'maestro discuss' first and complete with /done to generate final JSON."
            )
            print(f"[Replay] ERROR: {error_msg}")
            # Append error event
            if session.session_dir:
                append_event(session.session_dir, TranscriptEvent(
                    ts=datetime.now().isoformat(),
                    type="error",
                    payload={"message": error_msg}
                ))
            return 1

        # Convert to PatchOperation objects
        patch_operations = []
        try:
            for op_data in patch_operations_data:
                op_type = PatchOperationType(op_data['op_type'])
                patch_operations.append(PatchOperation(op_type=op_type, data=op_data['data']))
        except (KeyError, ValueError) as e:
            error_msg = f"Invalid patch operation format: {e}"
            print(f"[Replay] ERROR: {error_msg}")
            if session.session_dir:
                append_event(session.session_dir, TranscriptEvent(
                    ts=datetime.now().isoformat(),
                    type="error",
                    payload={"message": error_msg}
                ))
            return 1

        # Validate operations against context (OPS gating)
        context_kind = session.meta.context.get('kind', 'global')
        is_valid, validation_error = validate_ops_for_context(
            patch_operations,
            context_kind,
            allow_cross_context
        )

        if not is_valid:
            print(f"[Replay] ERROR: {validation_error}")
            if session.session_dir:
                append_event(session.session_dir, TranscriptEvent(
                    ts=datetime.now().isoformat(),
                    type="error",
                    payload={"message": validation_error}
                ))
            return 1

        # Show operations
        print(f"\n[Replay] Planned operations ({len(patch_operations)}):")
        for i, op in enumerate(patch_operations, 1):
            print(f"  {i}. {op.op_type.value}: {op.data}")

        if dry_run:
            print("\n[Replay] Dry run: changes not applied.")
            print("[Replay] Result: REPLAY_OK (dry-run)")
            # Append replay_run event (dry-run)
            if session.session_dir:
                append_event(session.session_dir, TranscriptEvent(
                    ts=datetime.now().isoformat(),
                    type="replay_run",
                    payload={
                        "dry_run": True,
                        "result": "REPLAY_OK",
                        "ops_count": len(patch_operations)
                    }
                ))
            return 0

        # Apply operations
        try:
            apply_patch_operations(patch_operations)
            print("\n[Replay] Changes applied successfully.")
            print("[Replay] Result: REPLAY_OK")

            # Append replay_run event (success)
            if session.session_dir:
                append_event(session.session_dir, TranscriptEvent(
                    ts=datetime.now().isoformat(),
                    type="replay_run",
                    payload={
                        "dry_run": False,
                        "result": "REPLAY_OK",
                        "ops_count": len(patch_operations)
                    }
                ))
                update_session_status(session.session_dir, "closed")

            return 0

        except Exception as e:
            error_msg = f"Failed to apply operations: {e}"
            print(f"[Replay] ERROR: {error_msg}")
            print("[Replay] Result: REPLAY_FAIL")

            # Append error + replay_run event (failure)
            if session.session_dir:
                append_event(session.session_dir, TranscriptEvent(
                    ts=datetime.now().isoformat(),
                    type="error",
                    payload={"message": error_msg, "details": str(e)}
                ))
                append_event(session.session_dir, TranscriptEvent(
                    ts=datetime.now().isoformat(),
                    type="replay_run",
                    payload={
                        "dry_run": False,
                        "result": "REPLAY_FAIL",
                        "ops_count": 0,
                        "error": error_msg
                    }
                ))

            return 1

    except FileNotFoundError as e:
        print(f"[Replay] ERROR: Session not found: {session_id_or_path}")
        print(f"[Replay] Details: {e}")
        print("[Replay] Result: REPLAY_FAIL")
        return 1
    except Exception as e:
        print(f"[Replay] ERROR: Unexpected error: {e}")
        print("[Replay] Result: REPLAY_FAIL")
        return 1


def handle_phase_discuss(phase_id: str, args) -> int:
    wsession_link, wsession_error = _resolve_explicit_wsession(args)
    if wsession_error:
        print(wsession_error)
        return 1

    # Generate session ID and acquire lock before starting discussion
    session_id = create_session_id()
    lock = RepoLock()

    try:
        lock.acquire(session_id)
    except RuntimeError as e:
        print(f"Error: {e}")
        return 1

    # Use the new router with PhaseContract
    initial_prompt = getattr(args, 'prompt', f'Start a discussion about phase {phase_id}.')
    engine = getattr(args, 'engine', 'qwen')  # Default to qwen, could be configured differently
    model = getattr(args, 'model', 'default')  # Model name for metadata
    mode = choose_mode(getattr(args, "mode", None)).value  # Convert to string

    try:
        patch_operations, json_error = run_discussion_with_router(
            initial_prompt=initial_prompt,
            contract_type=ContractType.PHASE,
            engine=engine,
            mode=mode,
            context_kind="phase",
            context_ref=phase_id
        )
    except Exception as e:
        # Release lock on error
        lock.release(session_id)
        raise

    # Save discussion artifacts
    session_id_returned = save_discussion_artifacts(
        initial_prompt=initial_prompt,
        patch_operations=patch_operations,
        engine_name=engine,
        model_name=model,
        contract_type=ContractType.PHASE,
        session_id=session_id,
        wsession_id=wsession_link[0].session_id if wsession_link else None
    )

    print(f"Discussion session ID for phase {phase_id}: {session_id}")
    if wsession_link:
        wsession_session, wsession_path = wsession_link
        wsession_session.metadata["last_discuss_session_id"] = session_id_returned
        save_session(wsession_session, wsession_path)

    if json_error:
        print(f"Error: {json_error}")
        print("Invalid JSON returned; no operations were applied. Retry or resume the discussion.")
        update_artifact_status(session_id, 'invalid_json', error_message=json_error)
        return 1

    # Apply patches if any were generated
    if patch_operations:
        # Show detailed preview of changes
        print(f"\nProposed changes for phase {phase_id}:")
        for i, op in enumerate(patch_operations, 1):
            print(f"  {i}. {op.op_type.value}: {op.data}")
            # Provide more detailed preview based on operation type
            if op.op_type == PatchOperationType.ADD_TRACK:
                track_name = op.data.get('track_name', 'Unnamed Track')
                track_id = op.data.get('track_id', track_name.replace(' ', '-').lower())
                print(f"      Track: {track_id} - {track_name}")
            elif op.op_type == PatchOperationType.ADD_PHASE:
                phase_name = op.data.get('phase_name', 'Unnamed Phase')
                phase_id_op = op.data.get('phase_id', phase_name.replace(' ', '-').lower())
                track_id = op.data.get('track_id', 'default')
                print(f"      Phase: {phase_id_op} - {phase_name} in track {track_id}")
            elif op.op_type == PatchOperationType.ADD_TASK:
                task_name = op.data.get('task_name', 'Unnamed Task')
                task_id = op.data.get('task_id', f"task-{len(str(task_name))}")
                phase_id_op = op.data.get('phase_id', 'default')
                print(f"      Task: {task_id} - {task_name} in phase {phase_id_op}")
            elif op.op_type in [PatchOperationType.MARK_DONE, PatchOperationType.MARK_TODO]:
                item_type = op.data.get('item_type', 'task')
                item_id = op.data.get('item_id')
                status = "DONE" if op.op_type == PatchOperationType.MARK_DONE else "TODO"
                print(f"      {item_type.upper()}: {item_id} -> {status}")
            elif op.op_type == PatchOperationType.MOVE_TASK:
                task_id = op.data.get('task_id')
                target_phase_id = op.data.get('target_phase_id')
                source_phase_id = op.data.get('source_phase_id', 'unknown')
                print(f"      TASK: {task_id} -> moved from {source_phase_id} to {target_phase_id}")
            elif op.op_type == PatchOperationType.EDIT_TASK_FIELDS:
                task_id = op.data.get('task_id')
                fields = op.data.get('fields', {})
                print(f"      TASK: {task_id} -> updated fields: {fields}")

        # Ask for confirmation before applying
        if not getattr(args, "dry_run", False):
            response = input("\nApply these changes? [y]es/[n]o/[e]dit manually: ").lower().strip()
            if response in ['y', 'yes']:
                # Apply the patches
                apply_patch_operations(patch_operations)
                print("Changes applied successfully.")
                # Update artifact status to indicate successful application
                applied_ops = [{'op_type': op.op_type.value, 'data': op.data} for op in patch_operations]
                update_artifact_status(session_id, 'applied', applied_ops)
            elif response in ['e', 'edit']:
                # Provide a way to edit the operations manually if needed
                print("Manual editing of operations is not yet implemented in this version.")
                print("Changes not applied.")
                update_artifact_status(session_id, 'cancelled')
            else:
                print("Changes not applied.")
                update_artifact_status(session_id, 'cancelled')
        else:
            print("Dry run: changes not applied.")
            update_artifact_status(session_id, 'dry_run')
    else:
        print("No changes were proposed.")
        update_artifact_status(session_id, 'no_operations')

    return 0


def handle_task_discuss(task_id: str, args) -> int:
    wsession_link, wsession_error = _resolve_explicit_wsession(args)
    if wsession_error:
        print(wsession_error)
        return 1

    # Generate session ID and acquire lock before starting discussion
    session_id = create_session_id()
    lock = RepoLock()

    try:
        lock.acquire(session_id)
    except RuntimeError as e:
        print(f"Error: {e}")
        return 1

    # Use the new router with TaskContract
    initial_prompt = getattr(args, 'prompt', f'Start a discussion about task {task_id}.')
    engine = getattr(args, 'engine', 'qwen')  # Default to qwen, could be configured differently
    model = getattr(args, 'model', 'default')  # Model name for metadata
    mode = choose_mode(getattr(args, "mode", None)).value  # Convert to string

    try:
        patch_operations, json_error = run_discussion_with_router(
            initial_prompt=initial_prompt,
            contract_type=ContractType.TASK,
            engine=engine,
            mode=mode,
            context_kind="task",
            context_ref=task_id
        )
    except Exception as e:
        # Release lock on error
        lock.release(session_id)
        raise

    # Save discussion artifacts
    session_id_returned = save_discussion_artifacts(
        initial_prompt=initial_prompt,
        patch_operations=patch_operations,
        engine_name=engine,
        model_name=model,
        contract_type=ContractType.TASK,
        session_id=session_id,
        wsession_id=wsession_link[0].session_id if wsession_link else None
    )

    print(f"Discussion session ID for task {task_id}: {session_id}")
    if wsession_link:
        wsession_session, wsession_path = wsession_link
        wsession_session.metadata["last_discuss_session_id"] = session_id_returned
        save_session(wsession_session, wsession_path)

    if json_error:
        print(f"Error: {json_error}")
        print("Invalid JSON returned; no operations were applied. Retry or resume the discussion.")
        update_artifact_status(session_id, 'invalid_json', error_message=json_error)
        return 1

    # Apply patches if any were generated
    if patch_operations:
        # Show detailed preview of changes
        print(f"\nProposed changes for task {task_id}:")
        for i, op in enumerate(patch_operations, 1):
            print(f"  {i}. {op.op_type.value}: {op.data}")
            # Provide more detailed preview based on operation type
            if op.op_type == PatchOperationType.ADD_TRACK:
                track_name = op.data.get('track_name', 'Unnamed Track')
                track_id = op.data.get('track_id', track_name.replace(' ', '-').lower())
                print(f"      Track: {track_id} - {track_name}")
            elif op.op_type == PatchOperationType.ADD_PHASE:
                phase_name = op.data.get('phase_name', 'Unnamed Phase')
                phase_id = op.data.get('phase_id', phase_name.replace(' ', '-').lower())
                track_id = op.data.get('track_id', 'default')
                print(f"      Phase: {phase_id} - {phase_name} in track {track_id}")
            elif op.op_type == PatchOperationType.ADD_TASK:
                task_name = op.data.get('task_name', 'Unnamed Task')
                task_id_op = op.data.get('task_id', f"task-{len(str(task_name))}")
                phase_id = op.data.get('phase_id', 'default')
                print(f"      Task: {task_id_op} - {task_name} in phase {phase_id}")
            elif op.op_type in [PatchOperationType.MARK_DONE, PatchOperationType.MARK_TODO]:
                item_type = op.data.get('item_type', 'task')
                item_id = op.data.get('item_id')
                status = "DONE" if op.op_type == PatchOperationType.MARK_DONE else "TODO"
                print(f"      {item_type.upper()}: {item_id} -> {status}")
            elif op.op_type == PatchOperationType.MOVE_TASK:
                task_id_op = op.data.get('task_id')
                target_phase_id = op.data.get('target_phase_id')
                source_phase_id = op.data.get('source_phase_id', 'unknown')
                print(f"      TASK: {task_id_op} -> moved from {source_phase_id} to {target_phase_id}")
            elif op.op_type == PatchOperationType.EDIT_TASK_FIELDS:
                task_id_op = op.data.get('task_id')
                fields = op.data.get('fields', {})
                print(f"      TASK: {task_id_op} -> updated fields: {fields}")

        # Ask for confirmation before applying
        if not getattr(args, "dry_run", False):
            response = input("\nApply these changes? [y]es/[n]o/[e]dit manually: ").lower().strip()
            if response in ['y', 'yes']:
                # Apply the patches
                apply_patch_operations(patch_operations)
                print("Changes applied successfully.")
                # Update artifact status to indicate successful application
                applied_ops = [{'op_type': op.op_type.value, 'data': op.data} for op in patch_operations]
                update_artifact_status(session_id, 'applied', applied_ops)
            elif response in ['e', 'edit']:
                # Provide a way to edit the operations manually if needed
                print("Manual editing of operations is not yet implemented in this version.")
                print("Changes not applied.")
                update_artifact_status(session_id, 'cancelled')
            else:
                print("Changes not applied.")
                update_artifact_status(session_id, 'cancelled')
        else:
            print("Dry run: changes not applied.")
            update_artifact_status(session_id, 'dry_run')
    else:
        print("No changes were proposed.")
        update_artifact_status(session_id, 'no_operations')

    return 0


def run_discussion_with_router(
    initial_prompt: str,
    contract_type: ContractType,
    engine: str = "qwen",
    mode: Optional[str] = None,
    context_kind: str = "global",
    context_ref: Optional[str] = None,
    use_cache: bool = True
) -> tuple[list[PatchOperation], Optional[str]]:
    """Run discussion using the new DiscussionRouter with appropriate contract.

    Args:
        initial_prompt: The prompt to send to the AI
        contract_type: The contract type to use
        engine: The AI engine to use
        mode: The discussion mode
        context_kind: Context kind for cache key
        context_ref: Context ref for cache key
        use_cache: Whether to use cache (default True, respects env vars)

    Returns:
        Tuple of (patch_operations, json_error)
    """
    # Initialize cache store
    cache_store = AiCacheStore()

    # Check if cache is enabled
    cache_enabled = use_cache and cache_store.get_cache_enabled()

    # Compute prompt hash for cache lookup
    prompt_hash = None
    if cache_enabled:
        # Get model from engine (simplified - in production this would be more sophisticated)
        model = "default"  # TODO: Get actual model from engine config
        prompt_hash = cache_store.compute_prompt_hash(
            prompt=initial_prompt,
            engine=engine,
            model=model,
            context_kind=context_kind
        )

        # Attempt cache lookup
        cache_result = cache_store.lookup(prompt_hash)
        if cache_result:
            scope, entry_dir = cache_result
            print(f"[Cache] Found entry in {scope} cache: {prompt_hash[:12]}...")

            # Load cache entry
            entry_data = cache_store.load_entry(entry_dir)

            # Validate cache entry
            watch_patterns = cache_store.get_watch_patterns()
            current_workspace_fp = cache_store.compute_workspace_fingerprint(watch_patterns) if watch_patterns else None
            is_valid, error_msg = cache_store.validate_entry(entry_data, current_workspace_fp)

            if is_valid:
                print("[Cache] Cache entry valid, using cached result (CACHE_HIT)")

                # Extract ops from cache
                ops_data = entry_data.get("ops")
                if ops_data:
                    # Reconstruct PatchOperations from cached data
                    patch_operations = []
                    for op_dict in ops_data:
                        op_type = PatchOperationType(op_dict["op_type"])
                        patch_operations.append(PatchOperation(op_type=op_type, data=op_dict["data"]))

                    return patch_operations, None
                else:
                    print("[Cache] Warning: Cache entry has no ops, falling back to AI")
            else:
                print(f"[Cache] Cache entry invalid: {error_msg}, falling back to AI")
                cache_store.mark_stale(entry_dir, error_msg)

    # Cache miss or disabled - run AI normally
    if cache_enabled:
        print("[Cache] CACHE_MISS, invoking AI...")

    manager = AiEngineManager()
    router = DiscussionRouter(manager)

    # Select the appropriate contract based on scope
    if contract_type == ContractType.TRACK:
        json_contract = TrackContract
    elif contract_type == ContractType.PHASE:
        json_contract = PhaseContract
    elif contract_type == ContractType.TASK:
        json_contract = TaskContract
    else:  # Global
        json_contract = GlobalContract

    # Run the discussion with the router
    results = router.run_discussion(
        engine=engine,
        initial_prompt=initial_prompt,
        mode=mode,
        json_contract=json_contract
    )

    # Store result in cache if enabled
    if cache_enabled and prompt_hash and results:
        # Determine cache scope
        cache_scope_pref = cache_store.get_cache_scope()
        if cache_scope_pref == "repo":
            cache_scope = "repo"
        elif cache_scope_pref == "user":
            cache_scope = "user"
        else:  # auto
            # Use repo cache if in a git repo, otherwise user cache
            cache_scope = "repo" if Path(".git").exists() else "user"

        # Serialize patch operations
        ops_serialized = [{"op_type": op.op_type.value, "data": op.data} for op in results]

        # Compute workspace fingerprint
        watch_patterns = cache_store.get_watch_patterns()
        workspace_fp = cache_store.compute_workspace_fingerprint(watch_patterns) if watch_patterns else None

        # Store cache entry
        try:
            cache_store.create_entry(
                prompt_hash=prompt_hash,
                scope=cache_scope,
                engine=engine,
                model="default",  # TODO: Get actual model
                prompt=initial_prompt,
                ops_result=ops_serialized,
                workspace_fp=workspace_fp,
                context_kind=context_kind,
                context_ref=context_ref,
                contract_type=contract_type.value
            )
            print(f"[Cache] Stored result in {cache_scope} cache: {prompt_hash[:12]}...")
        except Exception as e:
            print(f"[Cache] Warning: Failed to store cache entry: {e}")

    return results, router.last_json_error


def add_discuss_parser(subparsers):
    discuss_parser = subparsers.add_parser(
        "discuss",
        help="Start an AI discussion using the current context",
    )
    discuss_subparsers = discuss_parser.add_subparsers(dest="discuss_subcommand", help="Discuss subcommands")

    # Replay subcommand
    replay_parser = discuss_subparsers.add_parser("replay", help="Replay a discuss transcript or JSON payload")
    replay_parser.add_argument("path", help="Path to session ID or transcript (session_id, json/jsonl/text)")
    replay_parser.add_argument("--contract", choices=["global", "track", "phase", "task"], help="Override contract type")
    replay_parser.add_argument("--dry-run", action="store_true", help="Preview actions without executing them")
    replay_parser.add_argument("--allow-cross-context", action="store_true", help="Allow operations that don't match session context")

    # Resume subcommand
    resume_parser = discuss_subparsers.add_parser("resume", help="Resume a previous discussion session")
    resume_parser.add_argument("session_id", help="Session ID to resume")

    # Add mutually exclusive group for selecting context
    context_group = discuss_parser.add_mutually_exclusive_group()
    context_group.add_argument("--context", choices=["task", "phase", "track", "repo", "issues", "runbook", "workflow", "solutions", "global"], help="Explicit context type")
    context_group.add_argument("--track", "--track-id", dest="track_id", help="Select track by ID")
    context_group.add_argument("--phase", "--phase-id", dest="phase_id", help="Select phase by ID")
    context_group.add_argument("--task", "--task-id", dest="task_id", help="Select task by ID")

    discuss_parser.add_argument(
        "--mode",
        choices=["editor", "terminal"],
        help="Discussion mode (editor or terminal)",
    )
    discuss_parser.add_argument(
        "--wsession",
        help="Attach this discussion to a work session ID",
    )
    discuss_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview actions without executing them",
    )
    discuss_parser.add_argument(
        "--resume",
        help="Resume previous discussion session (deprecated: use 'discuss resume' subcommand)"
    )
    discuss_parser.set_defaults(allow_active_session=True)
    return discuss_parser
