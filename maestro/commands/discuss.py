"""Discussion command implementation with work session integration."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

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
from maestro.data import parse_config_md
from maestro.discussion import DiscussionSession, create_discussion_session, resume_discussion
from maestro.work_session import SessionType
from maestro.breadcrumb import list_breadcrumbs, get_breadcrumb_summary


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
    contract_type: ContractType
) -> str:
    """Save discussion artifacts including transcript and JSON results."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    artifacts_dir = Path(".maestro/ai/artifacts")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Create a unique session ID
    session_id = f"discuss_{contract_type.value}_{timestamp}"

    # Save the transcript
    transcript_content = f"""Discussion Transcript
=================

Timestamp: {datetime.now().isoformat()}
Engine: {engine_name}
Model: {model_name}
Contract Type: {contract_type.value}
Initial Prompt: {initial_prompt}

Patch Operations:
{json.dumps([{'op_type': op.op_type.value, 'data': op.data} for op in patch_operations], indent=2)}
"""

    transcript_path = artifacts_dir / f"{session_id}_transcript.txt"
    transcript_path.write_text(transcript_content, encoding='utf-8')

    # Save the JSON results separately
    json_results = {
        'session_id': session_id,
        'timestamp': datetime.now().isoformat(),
        'engine': engine_name,
        'model': model_name,
        'contract_type': contract_type.value,
        'initial_prompt': initial_prompt,
        'patch_operations': [{'op_type': op.op_type.value, 'data': op.data} for op in patch_operations],
        'status': 'pending'  # Will be updated after applying
    }

    json_path = artifacts_dir / f"{session_id}_results.json"
    json_path.write_text(json.dumps(json_results, indent=2), encoding='utf-8')

    return session_id


def update_artifact_status(session_id: str, status: str, applied_operations: list = None):
    """Update the status of a discussion artifact after applying changes."""
    artifacts_dir = Path(".maestro/ai/artifacts")
    json_path = artifacts_dir / f"{session_id}_results.json"

    if json_path.exists():
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        data['status'] = status
        if applied_operations is not None:
            data['applied_operations'] = applied_operations
            data['applied_at'] = datetime.now().isoformat()

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)


def handle_discuss_command(args) -> int:
    # Determine the appropriate contract based on context
    if hasattr(args, 'track_id') and args.track_id:
        contract_type = ContractType.TRACK
    elif hasattr(args, 'phase_id') and args.phase_id:
        contract_type = ContractType.PHASE
    elif hasattr(args, 'task_id') and args.task_id:
        contract_type = ContractType.TASK
    else:
        # Use global contract for general discussions
        contract_type = ContractType.GLOBAL

    # Use the new router with appropriate contract
    initial_prompt = getattr(args, 'prompt', 'Start a discussion about the selected context.')
    engine = getattr(args, 'engine', 'qwen')  # Default to qwen, could be configured differently
    model = getattr(args, 'model', 'default')  # Model name for metadata
    mode = choose_mode(getattr(args, "mode", None)).value  # Convert to string

    patch_operations = run_discussion_with_router(
        initial_prompt=initial_prompt,
        contract_type=contract_type,
        engine=engine,
        mode=mode
    )

    # Save discussion artifacts
    session_id = save_discussion_artifacts(
        initial_prompt=initial_prompt,
        patch_operations=patch_operations,
        engine_name=engine,
        model_name=model,
        contract_type=contract_type
    )

    print(f"Discussion session ID: {session_id}")

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
    # Use the new router with TrackContract
    initial_prompt = getattr(args, 'prompt', f'Start a discussion about track {track_id}.')
    engine = getattr(args, 'engine', 'qwen')  # Default to qwen, could be configured differently
    model = getattr(args, 'model', 'default')  # Model name for metadata
    mode = choose_mode(getattr(args, "mode", None)).value  # Convert to string

    patch_operations = run_discussion_with_router(
        initial_prompt=initial_prompt,
        contract_type=ContractType.TRACK,
        engine=engine,
        mode=mode
    )

    # Save discussion artifacts
    session_id = save_discussion_artifacts(
        initial_prompt=initial_prompt,
        patch_operations=patch_operations,
        engine_name=engine,
        model_name=model,
        contract_type=ContractType.TRACK
    )

    print(f"Discussion session ID for track {track_id}: {session_id}")

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


def handle_phase_discuss(phase_id: str, args) -> int:
    # Use the new router with PhaseContract
    initial_prompt = getattr(args, 'prompt', f'Start a discussion about phase {phase_id}.')
    engine = getattr(args, 'engine', 'qwen')  # Default to qwen, could be configured differently
    model = getattr(args, 'model', 'default')  # Model name for metadata
    mode = choose_mode(getattr(args, "mode", None)).value  # Convert to string

    patch_operations = run_discussion_with_router(
        initial_prompt=initial_prompt,
        contract_type=ContractType.PHASE,
        engine=engine,
        mode=mode
    )

    # Save discussion artifacts
    session_id = save_discussion_artifacts(
        initial_prompt=initial_prompt,
        patch_operations=patch_operations,
        engine_name=engine,
        model_name=model,
        contract_type=ContractType.PHASE
    )

    print(f"Discussion session ID for phase {phase_id}: {session_id}")

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
    # Use the new router with TaskContract
    initial_prompt = getattr(args, 'prompt', f'Start a discussion about task {task_id}.')
    engine = getattr(args, 'engine', 'qwen')  # Default to qwen, could be configured differently
    model = getattr(args, 'model', 'default')  # Model name for metadata
    mode = choose_mode(getattr(args, "mode", None)).value  # Convert to string

    patch_operations = run_discussion_with_router(
        initial_prompt=initial_prompt,
        contract_type=ContractType.TASK,
        engine=engine,
        mode=mode
    )

    # Save discussion artifacts
    session_id = save_discussion_artifacts(
        initial_prompt=initial_prompt,
        patch_operations=patch_operations,
        engine_name=engine,
        model_name=model,
        contract_type=ContractType.TASK
    )

    print(f"Discussion session ID for task {task_id}: {session_id}")

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
    mode: Optional[str] = None
) -> list[PatchOperation]:
    """Run discussion using the new DiscussionRouter with appropriate contract."""
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

    return results


def add_discuss_parser(subparsers):
    discuss_parser = subparsers.add_parser(
        "discuss",
        help="Start an AI discussion using the current context",
    )
    # Add mutually exclusive group for selecting context
    context_group = discuss_parser.add_mutually_exclusive_group()
    context_group.add_argument("--track", "--track-id", dest="track_id", help="Select track by ID")
    context_group.add_argument("--phase", "--phase-id", dest="phase_id", help="Select phase by ID")
    context_group.add_argument("--task", "--task-id", dest="task_id", help="Select task by ID")

    discuss_parser.add_argument(
        "--mode",
        choices=["editor", "terminal"],
        help="Discussion mode (editor or terminal)",
    )
    discuss_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview actions without executing them",
    )
    discuss_parser.add_argument(
        "--resume",
        help="Resume previous discussion session"
    )
    return discuss_parser
