#!/usr/bin/env python3
"""
Realize Stage: Per-File AI Conversion Worker

Implements the actual conversion workhorse for convert run:
- takes a file_task from plan.json
- builds a structured prompt using the saved snapshots + mapping context
- calls the selected AI engine (qwen/gemini/claude/codex) non-interactively
- streams output (unless quiet)
- writes results into the target repo only
- records a deterministic audit trail for every file
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Callable
import hashlib
import re
import copy
import datetime
import maestro.convert.playbook_manager


def create_snapshot(content: str, snapshot_dir: str, prefix: str = "") -> str:
    """Create a snapshot file with the content and return its path."""
    # Create hash of content to use as filename
    content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
    snapshot_filename = f"{prefix}{content_hash}.txt"
    snapshot_path = os.path.join(snapshot_dir, snapshot_filename)
    
    # Ensure snapshot directory exists
    os.makedirs(snapshot_dir, exist_ok=True)
    
    # Write content to snapshot
    with open(snapshot_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return snapshot_path


def get_file_snapshot_path(file_path: str, snapshot_dir: str) -> str:
    """Get the path to the snapshot file for a given source file."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    return create_snapshot(content, snapshot_dir, f"{os.path.basename(file_path)}_")


def build_structured_prompt(task: Dict, source_repo_path: str, target_repo_path: str, 
                          snapshot_dir: str, mapping_context: Optional[Dict] = None) -> str:
    """Build a structured prompt for the file task following the strict sections."""
    
    # GOAL section
    prompt = f"## GOAL\n"
    prompt += f"{task['acceptance_criteria']}\n\n"
    
    # CONTEXT section
    prompt += f"## CONTEXT\n"
    prompt += f"- Source repository: {source_repo_path}\n"
    prompt += f"- Target repository: {target_repo_path}\n"
    
    # Include source path, target path
    source_files = task.get('source_files', [])
    target_files = task.get('target_files', [])
    
    if source_files:
        prompt += f"- Source files to convert: {', '.join(source_files)}\n"
        
    if target_files:
        prompt += f"- Target files to create/update: {', '.join(target_files)}\n"
    
    # Include snapshot refs
    snapshots = []
    for source_file in source_files:
        source_file_path = os.path.join(source_repo_path, source_file)
        if os.path.exists(source_file_path):
            snapshot_path = get_file_snapshot_path(source_file_path, snapshot_dir)
            snapshots.append(snapshot_path)
            
    if snapshots:
        prompt += f"- Snapshots of source files: {', '.join(snapshots)}\n"
    
    # Include mapping summary if provided
    if mapping_context:
        prompt += f"- Mapping context: {mapping_context}\n"
    
    # Include target existing content ref if target files exist
    existing_content_snapshots = []
    for target_file in target_files:
        target_file_path = os.path.join(target_repo_path, target_file)
        if os.path.exists(target_file_path):
            snapshot_path = get_file_snapshot_path(target_file_path, snapshot_dir)
            existing_content_snapshots.append(snapshot_path)
    
    if existing_content_snapshots:
        prompt += f"- Existing target content snapshots: {', '.join(existing_content_snapshots)}\n"
    
    prompt += "\n"
    
    # REQUIREMENTS section
    prompt += f"## REQUIREMENTS\n"
    prompt += f"- Preserve behavior of original code as much as possible\n"
    prompt += f"- Follow language-specific style guidelines for the target technology stack\n"
    prompt += f"- Do not modify any files not explicitly mentioned in the task\n"
    prompt += f"- Maintain comments and documentation where possible\n"
    prompt += f"- Handle dependencies appropriately\n"
    
    if 'requirements' in task:
        for req in task['requirements']:
            prompt += f"- {req}\n"
    
    prompt += "\n"
    
    # ACCEPTANCE CRITERIA section
    prompt += f"## ACCEPTANCE CRITERIA\n"
    if isinstance(task['acceptance_criteria'], list):
        for criteria in task['acceptance_criteria']:
            prompt += f"- {criteria}\n"
    else:
        prompt += f"- {task['acceptance_criteria']}\n"
    
    prompt += f"- Produced file must compile/parses without syntax errors (if applicable)\n"
    prompt += f"- No placeholders like \"TODO\", \"FIXME\", or \"XXX\" unless explicitly allowed\n"
    
    prompt += "\n"
    
    # DELIVERABLES section
    prompt += f"## DELIVERABLES\n"
    deliverables = task.get('deliverables', [])
    if deliverables:
        for deliverable in deliverables:
            prompt += f"- {deliverable}\n"
    else:
        for target_file in target_files:
            prompt += f"- {target_file}\n"
    
    return prompt


def run_engine(engine: str, prompt: str, cwd: str, stream: bool = True, timeout: int = 300,
               extra_args: Optional[List[str]] = None, verbose: bool = False) -> Tuple[int, str, str]:
    """Unified function to run any AI engine with standardized interface."""

    if extra_args is None:
        extra_args = []

    # Map engine names to CLI commands
    engine_commands = {
        'qwen': ['qwen', '--yolo'] + extra_args,
        'gemini': ['gemini', '--approval-mode', 'yolo'] + extra_args,
        'claude': ['claude', '--print', '--output-format', 'text', '--permission-mode', 'bypassPermissions'] + extra_args,
        'codex': ['codex', 'exec', '--dangerously-bypass-approvals-and-sandbox'] + extra_args
    }

    if engine not in engine_commands:
        raise ValueError(f"Unsupported engine: {engine}")

    cmd = engine_commands[engine]

    if verbose:
        print(f"[engine-debug] running: {' '.join(cmd)}", file=sys.stderr)

    # Add the prompt as an argument (or pass via stdin if the command expects that)
    try:
        # For most of these engines, we'll pass the prompt via stdin
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            env=os.environ.copy()
        )

        stdout_data, stderr_data = process.communicate(input=prompt, timeout=timeout)
        exit_code = process.returncode

        if stream and stdout_data:
            print(stdout_data, end='')

        return exit_code, stdout_data, stderr_data

    except subprocess.TimeoutExpired:
        process.kill()
        stdout_data, stderr_data = process.communicate()
        return 124, stdout_data, f"Process timed out after {timeout} seconds"

    except FileNotFoundError:
        return 127, "", f"Command '{cmd[0]}' not found. Make sure the engine is installed."

    except Exception as e:
        return 1, "", f"Error running engine: {str(e)}"


def _get_run_engine() -> Callable:
    """
    Helper function to get the run_engine function, allowing for monkeypatching.
    Checks sys.modules.get('realize_worker') for attribute run_engine not None;
    returns that, else returns the default run_engine (defined in same module).
    """
    import sys

    # Get the realize_worker module from sys.modules
    current_module = sys.modules.get('realize_worker')

    if current_module and hasattr(current_module, 'run_engine') and getattr(current_module, 'run_engine') is not None:
        return getattr(current_module, 'run_engine')
    else:
        # Return the default run_engine function defined in this module
        return run_engine


def parse_ai_output(output: str) -> Optional[Dict]:
    """Parse AI output according to the JSON protocol."""
    # First, try to find JSON content in the output (in case there's surrounding text)
    # Look for JSON object pattern
    # This regex looks for JSON objects with proper nesting handling
    json_pattern = r'\{(?:[^{}]|{[^{}]*})*\}'
    json_match = re.search(json_pattern, output, re.DOTALL)

    if json_match:
        json_str = json_match.group(0)
        try:
            parsed = json.loads(json_str)
            # Validate that it has the required structure
            if 'files' not in parsed:
                raise ValueError("Parsed JSON does not contain 'files' key")
            # Validate files structure - each file should have 'path' and 'content'
            for f in parsed['files']:
                if 'path' not in f or 'content' not in f:
                    raise ValueError("Each file in 'files' must have 'path' and 'content' keys")
            return parsed
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
        except ValueError as e:
            print(f"JSON validation error: {e}")

    # If no JSON found in the content, try to parse the entire output as JSON
    try:
        parsed = json.loads(output)
        if 'files' not in parsed:
            raise ValueError("Parsed JSON does not contain 'files' key")
        # Validate files structure
        for f in parsed['files']:
            if 'path' not in f or 'content' not in f:
                raise ValueError("Each file in 'files' must have 'path' and 'content' keys")
        return parsed
    except json.JSONDecodeError as e:
        print(f"Full output JSON parse error: {e}")
    except ValueError as e:
        print(f"Full output JSON validation error: {e}")

    # If we can't parse as JSON, return None
    return None


def safe_write_file(target_path: str, content: str, target_repo_root: str, task_id: str = None, write_policy: str = "overwrite") -> Dict:
    """
    Safely write a file to the target repository with path normalization and atomic writes,
    including drift detection and write policy enforcement.

    Returns a dict with status information including:
    - success: boolean indicating if the operation succeeded
    - target_before_hash: hash of file before write (if existed)
    - target_after_hash: hash of file after write
    - changed: boolean indicating if file content changed
    - previous_known_hash: previous hash stored for this file (if exists)
    """

    # Normalize the path to prevent directory traversal
    normalized_path = os.path.normpath(target_path)

    # Prevent .. path escapes
    if '..' in normalized_path.split(os.sep):
        raise ValueError(f"Unsafe path detected: {target_path}")

    # Prevent absolute paths that could escape the target repo
    if os.path.isabs(normalized_path):
        # Convert absolute path to relative by removing leading separators
        normalized_path = normalized_path.lstrip(os.sep + os.altsep if os.altsep else '')

    # Ensure the path is under the target repo root
    full_target_path = os.path.abspath(os.path.join(target_repo_root, normalized_path))
    target_repo_abs = os.path.abspath(target_repo_root)

    if not full_target_path.startswith(target_repo_abs):
        raise ValueError(f"Path {full_target_path} is not under target repo root {target_repo_abs}")

    # Check for potentially dangerous paths
    dangerous_patterns = ['../', '..\\', '/etc/', '/proc/', '/sys/', '/dev/']
    for pattern in dangerous_patterns:
        if pattern in full_target_path.replace(target_repo_abs, ''):
            raise ValueError(f"Potentially dangerous path pattern detected: {target_path}")

    # Check if target file already exists
    target_exists = os.path.exists(full_target_path)
    target_before_hash = compute_file_hash(full_target_path) if target_exists else None

    # Load existing target hashes to check for previous ownership
    target_hashes = load_target_hashes()
    previous_known_hash_info = target_hashes.get(target_path, None)
    previous_known_hash = previous_known_hash_info.get('hash') if previous_known_hash_info else None

    # Apply write policy
    if target_exists:
        # Check what kind of file this is - was it previously written by Maestro?
        was_written_by_maestro = previous_known_hash_info is not None

        if write_policy == "skip_if_exists":
            return {
                "success": True,  # Not an error, just skipped
                "target_before_hash": target_before_hash,
                "target_after_hash": target_before_hash,  # Same as before
                "changed": False,
                "previous_known_hash": previous_known_hash,
                "action": "skipped"
            }
        elif write_policy == "fail_if_exists":
            if was_written_by_maestro:
                # File was written by Maestro, so we can overwrite it
                write_policy = "overwrite"  # Allow overwrite for Maestro-owned files
            else:
                # File exists and was not written by Maestro - fail
                raise ValueError(f"File {target_path} already exists and was not written by Maestro. Policy is 'fail_if_exists'")
        elif write_policy == "merge":
            # Merge policy requires specific merge strategy - this will be handled elsewhere
            # For now, just return that action is merge pending
            return {
                "success": True,
                "target_before_hash": target_before_hash,
                "target_after_hash": target_before_hash,
                "changed": False,
                "previous_known_hash": previous_known_hash,
                "action": "merge_pending"
            }

    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(full_target_path), exist_ok=True)

    # Calculate the hash for the content to be written
    content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()

    # Check if content is actually different from existing file
    file_changed = target_before_hash != content_hash

    # Only write if content is different or if we're overwriting anyway
    if file_changed or not target_exists:
        # Write atomically using a temporary file
        temp_dir = os.path.dirname(full_target_path)
        with tempfile.NamedTemporaryFile(mode='w', dir=temp_dir, delete=False, encoding='utf-8') as tmp_file:
            tmp_file.write(content)
            temp_path = tmp_file.name

        # Atomic move from temp file to target
        os.replace(temp_path, full_target_path)

        # Update target hash tracking
        if task_id:
            update_target_hash(target_path, task_id, content_hash)
    else:
        # Content is the same - no write needed
        pass

    # Get the final hash after the operation
    target_after_hash = compute_file_hash(full_target_path)

    return {
        "success": True,
        "target_before_hash": target_before_hash,
        "target_after_hash": target_after_hash,
        "changed": file_changed,
        "previous_known_hash": previous_known_hash,
        "action": "written" if file_changed or not target_exists else "unchanged"
    }


def compute_file_hash(file_path: str) -> Optional[str]:
    """Compute SHA-256 hash of file content."""
    if not os.path.exists(file_path):
        return None

    with open(file_path, 'rb') as f:
        content = f.read()
        return hashlib.sha256(content).hexdigest()


def load_target_hashes() -> Dict:
    """Load target file hashes from state file."""
    hash_file_path = ".maestro/convert/state/target_hashes.json"
    if os.path.exists(hash_file_path):
        try:
            with open(hash_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # If file is invalid, return empty dict
            return {}
    return {}


def save_target_hashes(hashes: Dict):
    """Save target file hashes to state file."""
    os.makedirs(".maestro/convert/state", exist_ok=True)
    hash_file_path = ".maestro/convert/state/target_hashes.json"
    with open(hash_file_path, 'w', encoding='utf-8') as f:
        json.dump(hashes, f, indent=2)


def update_target_hash(target_path: str, task_id: str, new_hash: str):
    """Update the hash for a target file."""
    hashes = load_target_hashes()
    hashes[target_path] = {
        "hash": new_hash,
        "task_id": task_id,
        "timestamp": int(time.time())
    }
    save_target_hashes(hashes)


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to be safe for file system operations."""
    # Remove dangerous characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading dots to prevent hidden files
    sanitized = sanitized.lstrip('.')
    return sanitized


class TaskInterrupted(Exception):
    """Exception raised when a task is interrupted by user."""
    pass


def merge_content(existing_content: str, new_content: str, strategy: str, markers: Dict = None) -> str:
    """
    Merge content using various strategies.

    Args:
        existing_content: The current content of the target file
        new_content: The new content to be merged
        strategy: The merge strategy to use
        markers: Optional markers for section-based strategies

    Returns:
        The merged content
    """
    if strategy == "append_section":
        # Simply append the new content
        return existing_content + "\n" + new_content

    elif strategy == "replace_section_by_marker":
        if not markers or 'begin_marker' not in markers or 'end_marker' not in markers:
            raise ValueError("replace_section_by_marker requires 'begin_marker' and 'end_marker' in markers")

        begin_marker = markers['begin_marker']
        end_marker = markers['end_marker']

        # Find the section between markers
        start_pos = existing_content.find(begin_marker)
        if start_pos == -1:
            # Marker not found, append instead
            return existing_content + "\n" + new_content

        end_pos = existing_content.find(end_marker, start_pos + len(begin_marker))
        if end_pos == -1:
            # End marker not found, append instead
            return existing_content + "\n" + new_content

        # Replace the content between the markers
        new_section = begin_marker + "\n" + new_content + "\n" + end_marker
        merged_content = (existing_content[:start_pos] +
                         new_section +
                         existing_content[end_pos + len(end_marker):])
        return merged_content

    elif strategy == "json_merge":
        import json as json_module
        try:
            existing_json = json_module.loads(existing_content)
            new_json = json_module.loads(new_content)

            # Deep merge the JSON objects
            def deep_merge(base, new):
                result = copy.deepcopy(base)
                for key, value in new.items():
                    if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                        result[key] = deep_merge(result[key], value)
                    else:
                        result[key] = value
                return result

            merged_json = deep_merge(existing_json, new_json)
            return json_module.dumps(merged_json, indent=2)
        except json_module.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON content for json_merge: {e}")

    elif strategy == "toml_merge":
        # For TOML, we need to parse and merge, but since we don't have toml module by default,
        # we'll just append for now (in a real implementation, we'd use toml library)
        return existing_content + "\n" + new_content

    else:
        raise ValueError(f"Unsupported merge strategy: {strategy}")


def get_write_policy_for_task(task: Dict) -> str:
    """
    Get the write policy for a task based on its phase and explicit policy.

    Default policy rules:
    - scaffold tasks: skip_if_exists (do not keep rewriting project files)
    - file tasks: overwrite only if target file was previously produced by Maestro, else fail_if_exists
    - sweep tasks: skip_if_exists
    """
    # Check if task has explicit policy
    explicit_policy = task.get('write_policy')
    if explicit_policy:
        return explicit_policy

    # Apply defaults based on phase
    phase = task.get('phase')
    if phase == 'scaffold':
        return 'skip_if_exists'
    elif phase == 'file':
        return 'overwrite'  # Will be handled with Maestro ownership check in safe_write_file
    elif phase == 'sweep':
        return 'skip_if_exists'
    else:
        return 'overwrite'  # Default fallback


def update_task_status_with_hash_info(plan_path: str, task_id: str, status: str, hash_info: Dict = None):
    """Update the status of a specific task in the plan, including hash information."""
    with open(plan_path, 'r', encoding='utf-8') as f:
        plan = json.load(f)

    # Find the task across all phases
    task_found = False
    for phase in ['scaffold_tasks', 'file_tasks', 'final_sweep_tasks']:
        for task in plan.get(phase, []):
            if task['task_id'] == task_id:
                task['status'] = status
                # Add hash info if provided
                if hash_info:
                    task['target_before_hash'] = hash_info.get('target_before_hash')
                    task['target_after_hash'] = hash_info.get('target_after_hash')
                    task['changed'] = hash_info.get('changed', False)
                    task['previous_known_hash'] = hash_info.get('previous_known_hash')
                task_found = True
                break
        if task_found:
            break

    # Save the updated plan
    with open(plan_path, 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=2)


def update_task_status(plan_path: str, task_id: str, status: str):
    """Update the status of a specific task in the plan."""
    update_task_status_with_hash_info(plan_path, task_id, status, None)


def execute_file_task(task: Dict, source_repo_path: str, target_repo_path: str,
                     verbose: bool = False, plan_path: str = ".maestro/convert/plan/plan.json") -> bool:
    """
    Execute a single file conversion task according to the realization contract.
    Returns True if successful, False otherwise.
    """
    task_id = task['task_id']

    if verbose:
        print(f"Starting file task {task_id}: {task.get('title', 'unnamed task')}")

    # Set up directories for audit artifacts
    os.makedirs(".maestro/convert/snapshots", exist_ok=True)
    os.makedirs(".maestro/convert/inputs", exist_ok=True)
    os.makedirs(".maestro/convert/outputs", exist_ok=True)
    os.makedirs(".maestro/convert/diffs", exist_ok=True)

    try:
        # Create timestamp for this task execution
        timestamp = str(int(time.time()))

        # Set up directories for audit artifacts
        os.makedirs(".maestro/convert/snapshots", exist_ok=True)
        os.makedirs(".maestro/convert/inputs", exist_ok=True)
        os.makedirs(".maestro/convert/outputs", exist_ok=True)
        os.makedirs(".maestro/convert/diffs", exist_ok=True)

        # Determine the realization action (convert, copy, skip, merge)
        realization_action = task.get('realization_action', 'convert')

        if realization_action == 'skip':
            skip_reason = task.get('skip_reason', 'No reason provided')
            print(f"Skipping task {task_id}: {skip_reason}")

            # Record the skip action as an audit artifact
            skip_record = {
                "task_id": task_id,
                "action": "skip",
                "reason": skip_reason,
                "timestamp": timestamp
            }

            skip_filename = f"task_{sanitize_filename(task_id)}_skip_record.json"
            skip_path = os.path.join(".maestro/convert/outputs", skip_filename)

            with open(skip_path, 'w', encoding='utf-8') as f:
                json.dump(skip_record, f, indent=2)

            if verbose:
                print(f"Saved skip record to {skip_path}")

            return True

        elif realization_action == 'copy':
            # Get the write policy for this task
            write_policy = get_write_policy_for_task(task)

            # Copy files from source to target with write policy enforcement
            all_files_copied_successfully = True
            for i, source_file in enumerate(task.get('source_files', [])):
                source_path = os.path.join(source_repo_path, source_file)

                # Determine target path
                if i < len(task.get('target_files', [])):
                    target_file = task['target_files'][i]
                else:
                    target_file = source_file

                # Read source file content
                try:
                    with open(source_path, 'r', encoding='utf-8', errors='ignore') as src:
                        content = src.read()
                except Exception as e:
                    print(f"Error reading source file {source_path}: {str(e)}")
                    all_files_copied_successfully = False
                    continue

                # Write the file to the target repository with write policy
                write_result = safe_write_file(
                    target_file,
                    content,
                    target_repo_path,
                    task_id=task_id,
                    write_policy=write_policy
                )

                if verbose and write_result["success"]:
                    action = write_result.get("action", "written")
                    target_existed = "existed" if write_result.get("target_before_hash") else "new"
                    print(f"[maestro] task {task_id} | src={source_file} -> tgt={target_file} | {target_existed} | policy={write_policy} | action={action}")

                    if write_result.get("changed"):
                        print(f"  Content changed - recording diff...")
                    elif write_result.get("action") == "skipped":
                        print(f"  File was skipped due to policy")
                elif not write_result["success"]:
                    print(f"Failed to write {target_file} to target repository")
                    all_files_copied_successfully = False
                    break

            if not all_files_copied_successfully:
                return False

            # Record copy action as an audit artifact
            copy_record = {
                "task_id": task_id,
                "action": "copy",
                "source_files": task.get('source_files', []),
                "target_files": task.get('target_files', []),
                "timestamp": timestamp
            }

            copy_filename = f"task_{sanitize_filename(task_id)}_copy_record.json"
            copy_path = os.path.join(".maestro/convert/outputs", copy_filename)

            with open(copy_path, 'w', encoding='utf-8') as f:
                json.dump(copy_record, f, indent=2)

            if verbose:
                print(f"Saved copy record to {copy_path}")

            return True

        elif realization_action == 'merge':
            # Get the write policy and merge strategy for this task
            write_policy = get_write_policy_for_task(task)
            merge_strategy = task.get('merge_strategy')
            merge_markers = task.get('merge_markers')

            if not merge_strategy:
                print(f"Merge task {task_id} requires 'merge_strategy' field")
                return False

            # Validate merge strategy
            valid_strategies = ['append_section', 'replace_section_by_marker', 'json_merge', 'toml_merge']
            if merge_strategy not in valid_strategies:
                print(f"Invalid merge strategy '{merge_strategy}' for task {task_id}. Valid strategies: {valid_strategies}")
                return False

            # For merge tasks, we need to determine the target file to merge into
            target_files = task.get('target_files', [])
            if not target_files:
                print(f"Merge task {task_id} requires 'target_files' to specify merge target")
                return False

            # Determine the target file to merge into (first one)
            target_file_path = target_files[0]

            # Get source content that will be merged
            source_files = task.get('source_files', [])
            if not source_files:
                print(f"Merge task {task_id} requires 'source_files' to provide content to merge")
                return False

            # Read the source content that will be merged
            source_content = ""
            for source_file in source_files:
                source_path = os.path.join(source_repo_path, source_file)
                try:
                    with open(source_path, 'r', encoding='utf-8', errors='ignore') as src:
                        source_content += src.read() + "\n"
                except Exception as e:
                    print(f"Error reading merge source file {source_path}: {str(e)}")
                    return False

            # Read existing target content
            target_path = os.path.join(target_repo_path, target_file_path.lstrip('/'))
            existing_content = ""
            if os.path.exists(target_path):
                with open(target_path, 'r', encoding='utf-8', errors='ignore') as f:
                    existing_content = f.read()

            try:
                # Apply merge strategy
                merged_content = merge_content(existing_content, source_content, merge_strategy, merge_markers)
            except Exception as e:
                print(f"Error during merge for task {task_id}, target {target_file_path}: {str(e)}")
                return False

            # Write the merged content to the target file with write policy
            write_result = safe_write_file(
                target_file_path,
                merged_content,
                target_repo_path,
                task_id=task_id,
                write_policy=write_policy
            )

            if not write_result["success"]:
                print(f"Failed to write merged content to {target_file_path}")
                return False

            if verbose:
                action = write_result.get("action", "written")
                target_existed = "existed" if write_result.get("target_before_hash") else "new"
                print(f"[maestro] task {task_id} | merge src -> tgt={target_file_path} | {target_existed} | policy={write_policy} | action={action}")

                if write_result.get("changed"):
                    print(f"  Content changed - recording merge diff...")
                    # Create a patch file for the merge
                    patch_filename = f"task_{sanitize_filename(task_id)}_merge.patch"
                    patch_path = os.path.join(".maestro/convert/diffs", patch_filename)

                    with open(patch_path, 'w', encoding='utf-8') as f:
                        f.write(f"# Merge patch for {target_file_path} by task {task_id}\n")
                        f.write(f"# Merge strategy: {merge_strategy}\n")
                        f.write(f"# Before hash: {write_result.get('target_before_hash', 'N/A')}\n")
                        f.write(f"# After hash: {write_result.get('target_after_hash', 'N/A')}\n")
                        f.write("# This records that a merge operation was performed.\n")
                elif write_result.get("action") == "skipped":
                    print(f"  File was skipped due to policy")

            # Record merge action as an audit artifact
            merge_record = {
                "task_id": task_id,
                "action": "merge",
                "source_files": source_files,
                "target_file": target_file_path,
                "merge_strategy": merge_strategy,
                "timestamp": timestamp,
                "status": "success"
            }

            merge_filename = f"task_{sanitize_filename(task_id)}_merge_record.json"
            merge_path = os.path.join(".maestro/convert/outputs", merge_filename)

            with open(merge_path, 'w', encoding='utf-8') as f:
                json.dump(merge_record, f, indent=2)

            if verbose:
                print(f"Saved merge record to {merge_path}")

            return True

        elif realization_action == 'convert':
            # Standard conversion process

            # Build structured prompt
            prompt = build_structured_prompt(
                task=task,
                source_repo_path=source_repo_path,
                target_repo_path=target_repo_path,
                snapshot_dir=".maestro/convert/snapshots"
            )

            # Save the prompt as audit artifact
            sanitized_task_id = sanitize_filename(task_id)
            prompt_filename = f"task_{sanitized_task_id}_{timestamp}.txt"
            prompt_path = os.path.join(".maestro/convert/inputs", prompt_filename)

            with open(prompt_path, 'w', encoding='utf-8') as f:
                f.write(prompt)

            if verbose:
                print(f"Saved prompt to {prompt_path}")

            # Run the selected AI engine
            engine = task['engine']
            stream_output = not task.get('quiet', False)  # Stream unless quiet is specified

            if verbose:
                print(f"Running {engine} engine for task {task_id}")

            # Prepare extra args based on task configuration
            extra_args = task.get('engine_args', [])

            try:
                # Handle potential interruptions during engine run
                run_engine_func = _get_run_engine()
                exit_code, stdout_data, stderr_data = run_engine_func(
                    engine=engine,
                    prompt=prompt,
                    cwd=source_repo_path,  # Use source repo as working directory
                    stream=stream_output,
                    timeout=task.get('timeout', 300),
                    extra_args=extra_args,
                    verbose=verbose
                )
            except KeyboardInterrupt:
                # Update task status to interrupted
                update_task_status_with_hash_info(plan_path, task_id, 'interrupted')
                print(f"\nTask {task_id} was interrupted by user")
                return False  # Return False to indicate interruption

            # Save raw outputs as audit artifacts
            engine_sanitized = sanitize_filename(engine)
            stdout_filename = f"task_{sanitized_task_id}_{engine_sanitized}_{timestamp}.stdout.txt"
            stderr_filename = f"task_{sanitized_task_id}_{engine_sanitized}_{timestamp}.stderr.txt"

            stdout_path = os.path.join(".maestro/convert/outputs", stdout_filename)
            stderr_path = os.path.join(".maestro/convert/outputs", stderr_filename)

            with open(stdout_path, 'w', encoding='utf-8') as f:
                f.write(stdout_data)

            with open(stderr_path, 'w', encoding='utf-8') as f:
                f.write(stderr_data)

            if verbose:
                print(f"Saved engine output to {stdout_path}")
                print(f"Saved engine errors to {stderr_path}")

            # Check if the engine call was successful
            if exit_code != 0:
                print(f"Engine {engine} failed for task {task_id} with exit code {exit_code}")
                print(f"Error: {stderr_data}")
                return False

            # Parse the AI output
            parsed_result = parse_ai_output(stdout_data)

            if not parsed_result:
                print(f"Could not parse AI output as JSON for task {task_id}")
                print("Raw output:", stdout_data[:500], "..." if len(stdout_data) > 500 else "")
                return False

            # Validate the parsed result structure
            if 'files' not in parsed_result:
                print(f"AI output missing required 'files' key for task {task_id}")
                return False

            files_to_write = parsed_result['files']

            # Check if there's an active playbook and validate against its constraints
            playbook_manager_instance = playbook_manager.PlaybookManager()
            active_binding = playbook_manager_instance.get_active_playbook_binding()
            active_playbook = None

            if active_binding:
                playbook_id = active_binding['playbook_id']
                active_playbook = playbook_manager_instance.load_playbook(playbook_id)
                if active_playbook:
                    if verbose:
                        print(f"[WORKER] Applying playbook constraints from: {active_playbook.id}")

                    # Check for forbidden constructs in the output
                    forbidden_constructs = active_playbook.forbidden_constructs.get('target', [])
                    if forbidden_constructs:
                        violations_found = []
                        for file_info in files_to_write:
                            content = file_info.get('content', '')
                            for forbidden in forbidden_constructs:
                                if forbidden in content:
                                    violations_found.append({
                                        'file': file_info.get('path', 'unknown'),
                                        'construct': forbidden
                                    })

                        # If violations were found, check for overrides
                        if violations_found:
                            # Check if there's an override file with permission for this violation
                            override_needed = True
                            for violation in violations_found:
                                print(f"[ERROR] Task {task_id} output contains forbidden construct: '{violation['construct']}' in file '{violation['file']}'")
                                print(f"       Playbook {active_playbook.id} prohibits this construct in output files")

                            # For now, we'll fail the task if forbidden constructs are found
                            # In a more sophisticated system, this might prompt for an override decision
                            return False

            # Get the write policy for this task
            write_policy = get_write_policy_for_task(task)

            # Write the output files to the target repository
            all_files_written_successfully = True
            hash_tracking_info = []

            for file_info in files_to_write:
                file_path = file_info.get('path')
                file_content = file_info.get('content', '')

                if not file_path:
                    print(f"File info missing path in AI output for task {task_id}")
                    all_files_written_successfully = False
                    continue

                # Get merge strategy if applicable
                merge_strategy = task.get('merge_strategy')
                merge_markers = task.get('merge_markers')

                # If this is a merge task, prepare the merged content
                if write_policy == 'merge':
                    if not merge_strategy:
                        print(f"Merge policy requires merge_strategy for task {task_id}")
                        all_files_written_successfully = False
                        continue

                    # Read existing content if file exists
                    target_full_path = os.path.join(target_repo_path, file_path.lstrip('/'))
                    existing_content = ""
                    if os.path.exists(target_full_path):
                        with open(target_full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            existing_content = f.read()

                    try:
                        # Apply merge strategy
                        if merge_strategy in ['append_section', 'replace_section_by_marker']:
                            file_content = merge_content(existing_content, file_content, merge_strategy, merge_markers)
                        elif merge_strategy in ['json_merge', 'toml_merge']:
                            file_content = merge_content(existing_content, file_content, merge_strategy)
                        else:
                            print(f"Unsupported merge strategy '{merge_strategy}' for task {task_id}")
                            all_files_written_successfully = False
                            continue
                    except Exception as e:
                        print(f"Error during merge for task {task_id}, file {file_path}: {str(e)}")
                        all_files_written_successfully = False
                        continue

                # Write the file to the target repository with write policy
                write_result = safe_write_file(
                    file_path,
                    file_content,
                    target_repo_path,
                    task_id=task_id,
                    write_policy=write_policy
                )

                hash_tracking_info.append({
                    "file_path": file_path,
                    "write_result": write_result
                })

                if write_result["success"]:
                    if verbose:
                        action = write_result.get("action", "written")
                        target_existed = "existed" if write_result.get("target_before_hash") else "new"
                        print(f"[maestro] task {task_id} | src=AI -> tgt={file_path} | {target_existed} | policy={write_policy} | action={action}")

                        if write_result.get("changed"):
                            print(f"  Content changed - recording diff...")
                            # Create a patch file for the change
                            patch_filename = f"task_{sanitize_filename(task_id)}_{sanitize_filename(file_path.replace('/', '_'))}.patch"
                            patch_path = os.path.join(".maestro/convert/diffs", patch_filename)

                            # Create simple diff - just log the before/after hashes for now
                            with open(patch_path, 'w', encoding='utf-8') as f:
                                f.write(f"# Patch for {file_path} by task {task_id}\n")
                                f.write(f"# Before hash: {write_result.get('target_before_hash', 'N/A')}\n")
                                f.write(f"# After hash: {write_result.get('target_after_hash', 'N/A')}\n")
                                f.write("# This is a hash-based diff. For detailed diff, use git diff.\n")
                        elif write_result.get("action") == "skipped":
                            print(f"  File was skipped due to policy")
                else:
                    print(f"Failed to write {file_path} to target repository")
                    all_files_written_successfully = False

            if not all_files_written_successfully:
                return False

            # Record diff snapshot (capture git diff if git is available)
            try:
                diff_result = subprocess.run(
                    ['git', 'diff'],
                    cwd=target_repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10  # Short timeout for git operations
                )

                if diff_result.returncode == 0 and diff_result.stdout.strip():
                    diff_filename = f"task_{sanitized_task_id}.patch"
                    diff_path = os.path.join(".maestro/convert/diffs", diff_filename)

                    with open(diff_path, 'w', encoding='utf-8') as f:
                        f.write(diff_result.stdout)

                    if verbose:
                        print(f"Saved diff to {diff_path}")
                else:
                    if verbose:
                        print(f"No changes to diff for task {task_id} or git not available")
            except subprocess.TimeoutExpired:
                if verbose:
                    print(f"Git diff timed out for task {task_id}")
            except Exception as e:
                if verbose:
                    print(f"Error running git diff for task {task_id}: {str(e)}")

            # Run optional validation command if specified
            validation_cmd = task.get('validation_cmd')
            if validation_cmd:
                if verbose:
                    print(f"Running validation command for task {task_id}: {validation_cmd}")

                try:
                    validation_result = subprocess.run(
                        validation_cmd,
                        shell=True,
                        cwd=target_repo_path,
                        capture_output=True,
                        text=True,
                        timeout=30  # 30 second timeout for validation
                    )

                    # Record validation results as audit artifact
                    validation_record = {
                        "task_id": task_id,
                        "validation_cmd": validation_cmd,
                        "exit_code": validation_result.returncode,
                        "stdout": validation_result.stdout,
                        "stderr": validation_result.stderr,
                        "timestamp": timestamp
                    }

                    validation_filename = f"task_{sanitized_task_id}_validation.json"
                    validation_path = os.path.join(".maestro/convert/outputs", validation_filename)

                    with open(validation_path, 'w', encoding='utf-8') as f:
                        json.dump(validation_record, f, indent=2)

                    if verbose:
                        print(f"Saved validation record to {validation_path}")

                    if validation_result.returncode != 0:
                        print(f"Validation failed for task {task_id}: {validation_result.stderr}")
                        print(f"Validation output: {validation_result.stdout}")
                        # Should we fail the task if validation fails? For now, we'll just warn
                        print(f"WARNING: Validation failed for task {task_id}, but continuing...")
                    else:
                        if verbose:
                            print(f"Validation passed for task {task_id}")

                except subprocess.TimeoutExpired:
                    print(f"Validation command for task {task_id} timed out")
                    return False
                except Exception as e:
                    print(f"Error running validation for task {task_id}: {str(e)}")
                    return False

            # Determine hash information for successful task
            # Find the final hash info from the last written file (or aggregate info)
            final_hash_info = {}
            if hash_tracking_info:
                # Aggregate hash information - let's use the information from the last changed file
                for hash_info in hash_tracking_info:
                    write_result = hash_info['write_result']
                    if write_result.get('changed'):
                        # Use the last file that actually changed as the representative
                        final_hash_info = {
                            'target_before_hash': write_result.get('target_before_hash'),
                            'target_after_hash': write_result.get('target_after_hash'),
                            'changed': write_result.get('changed'),
                            'previous_known_hash': write_result.get('previous_known_hash')
                        }
                        break
                # If no file changed, use the first one's info
                if not final_hash_info and hash_tracking_info:
                    write_result = hash_tracking_info[0]['write_result']
                    final_hash_info = {
                        'target_before_hash': write_result.get('target_before_hash'),
                        'target_after_hash': write_result.get('target_after_hash'),
                        'changed': write_result.get('changed'),
                        'previous_known_hash': write_result.get('previous_known_hash')
                    }

            # Update task status to completed with hash information
            update_task_status_with_hash_info(plan_path, task_id, 'completed', final_hash_info)

            if verbose:
                print(f"Completed file task {task_id}")

            return True

        else:
            print(f"Unknown realization action '{realization_action}' for task {task_id}")
            return False

    except KeyboardInterrupt:
        # Update task status to interrupted
        update_task_status_with_hash_info(plan_path, task_id, 'interrupted')
        print(f"\nTask {task_id} was interrupted by user")
        return False  # Return False to indicate interruption
    except Exception as e:
        print(f"Error executing file task {task_id}: {str(e)}")
        return False




def execute_file_task_with_arbitration(task: Dict, source_repo_path: str, target_repo_path: str,
                                      verbose: bool = False, plan_path: str = ".maestro/convert/plan/plan.json",
                                      arbitrate_engines: List[str] = ['qwen', 'claude'],
                                      judge_engine: str = 'codex', max_candidates: int = 2, use_judge: bool = True) -> bool:
    """
    Execute a file task with multi-engine arbitration mode.
    Runs multiple engines for the same task, scores outputs, and selects the best one.
    """
    task_id = task['task_id']

    if verbose:
        print(f"Starting arbitration for task {task_id}: {task.get('title', 'unnamed task')}")
        print(f"  Engines: {', '.join(arbitrate_engines)}")
        print(f"  Max candidates: {max_candidates}")

    # Set up directories for arbitration artifacts
    os.makedirs(".maestro/convert/inputs", exist_ok=True)
    os.makedirs(".maestro/convert/outputs", exist_ok=True)
    os.makedirs(".maestro/convert/diffs", exist_ok=True)
    os.makedirs(".maestro/convert/snapshots", exist_ok=True)
    arbitration_dir = f".maestro/convert/arbitration/{task_id}"
    os.makedirs(arbitration_dir, exist_ok=True)

    # Timestamp for this arbitration run
    timestamp = str(int(time.time()))

    # Step 1: Generate candidates from multiple engines
    candidates = {}
    candidate_scorecards = {}

    print(f"  Generating candidates from {len(arbitrate_engines)} engines...")

    for engine in arbitrate_engines[:max_candidates]:  # Limit to max_candidates
        print(f"    Running engine: {engine}")

        # Create a copy of the task with the current engine
        task_with_engine = copy.deepcopy(task)
        task_with_engine['engine'] = engine

        # Build structured prompt for this engine
        prompt = build_structured_prompt(
            task=task_with_engine,
            source_repo_path=source_repo_path,
            target_repo_path=target_repo_path,
            snapshot_dir=".maestro/convert/snapshots"
        )

        # Save the prompt as audit artifact
        sanitized_task_id = sanitize_filename(task_id)
        prompt_filename = f"task_{sanitized_task_id}_{engine}_{timestamp}.txt"
        prompt_path = os.path.join(".maestro/convert/inputs", prompt_filename)

        with open(prompt_path, 'w', encoding='utf-8') as f:
            f.write(prompt)

        if verbose:
            print(f"    Saved prompt to {prompt_path}")

        # Run the selected AI engine
        stream_output = not task_with_engine.get('quiet', False)

        if verbose:
            print(f"    Running {engine} engine for task {task_id}")

        # Prepare extra args based on task configuration
        extra_args = task_with_engine.get('engine_args', [])

        try:
            # Handle potential interruptions during engine run
            run_engine_func = _get_run_engine()
            exit_code, stdout_data, stderr_data = run_engine_func(
                engine=engine,
                prompt=prompt,
                cwd=source_repo_path,
                stream=stream_output,
                timeout=task_with_engine.get('timeout', 300),
                extra_args=extra_args,
                verbose=verbose
            )
        except KeyboardInterrupt:
            print(f"\nTask {task_id} was interrupted during arbitration")
            return False

        # Save raw outputs as audit artifacts
        engine_sanitized = sanitize_filename(engine)
        stdout_filename = f"candidate_{engine}_{timestamp}.stdout.txt"
        stderr_filename = f"candidate_{engine}_{timestamp}.stderr.txt"

        stdout_path = os.path.join(arbitration_dir, stdout_filename)
        stderr_path = os.path.join(arbitration_dir, stderr_filename)

        with open(stdout_path, 'w', encoding='utf-8') as f:
            f.write(stdout_data)

        with open(stderr_path, 'w', encoding='utf-8') as f:
            f.write(stderr_data)

        if verbose:
            print(f"    Saved engine outputs to {arbitration_dir}")

        # Check if the engine call was successful
        if exit_code != 0:
            print(f"    Engine {engine} failed with exit code {exit_code}")
            print(f"    Error: {stderr_data}")
            continue  # Skip to next engine

        # Parse the AI output for this candidate
        parsed_result = parse_ai_output(stdout_data)

        if not parsed_result:
            print(f"    Could not parse AI output as JSON for {engine}")
            continue

        # Validate the parsed result structure
        if 'files' not in parsed_result:
            print(f"    AI output missing required 'files' key for {engine}")
            continue

        # Save the raw candidate output as JSON
        candidate_filename = f"candidate_{engine}_{timestamp}.json"
        candidate_path = os.path.join(arbitration_dir, candidate_filename)

        with open(candidate_path, 'w', encoding='utf-8') as f:
            json.dump(parsed_result, f, indent=2)

        # Store the candidate
        candidates[engine] = {
            'output': parsed_result,
            'engine': engine,
            'timestamp': timestamp,
            'stdout_path': stdout_path,
            'stderr_path': stderr_path,
            'candidate_path': candidate_path,
            'exit_code': exit_code
        }

        print(f"    Generated candidate from {engine}")

    # If no candidates were generated successfully, return failure
    if not candidates:
        print(f"  No candidates generated successfully for task {task_id}")
        return False

    # Step 2: Score each candidate
    print(f"  Scoring {len(candidates)} candidates...")

    for engine, candidate_data in candidates.items():
        scorecard = _score_candidate(
            candidate_data,
            task,
            source_repo_path,
            target_repo_path,
            arbitration_dir
        )
        candidate_scorecards[engine] = scorecard

        # Save the scorecard
        scorecard_filename = f"scorecard_{engine}.json"
        scorecard_path = os.path.join(arbitration_dir, scorecard_filename)

        with open(scorecard_path, 'w', encoding='utf-8') as f:
            json.dump(scorecard, f, indent=2)

    # Step 3: Run semantic integrity checks on each candidate
    print(f"  Running semantic checks on candidates...")

    semantic_results = {}
    for engine, candidate_data in candidates.items():
        # Get the target files for this candidate to run semantic checks
        candidate_files = candidate_data['output'].get('files', [])

        # Create a temporary directory to test this candidate's output
        with tempfile.TemporaryDirectory() as temp_dir:
            # Write candidate files to temp directory for semantic analysis
            for file_info in candidate_files:
                file_path = file_info.get('path')
                file_content = file_info.get('content', '')

                if file_path:
                    temp_file_path = os.path.join(temp_dir, file_path.lstrip('/'))
                    os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)

                    with open(temp_file_path, 'w', encoding='utf-8') as f:
                        f.write(file_content)

            # Create a temporary task for semantic check with the candidate's output
            temp_task = copy.deepcopy(task)
            temp_task['target_files'] = [f['path'] for f in candidate_files if 'path' in f]

            # Run semantic check on this candidate
            from maestro.convert.semantic_integrity import SemanticIntegrityChecker
            semantic_checker = SemanticIntegrityChecker()
            semantic_result = semantic_checker._analyze_semantic_equivalence(
                source_snapshot_hash=semantic_checker.compute_source_snapshot_hash(task.get('source_files', []), source_repo_path),
                target_content="\n".join([f.get('content', '') for f in candidate_files]),
                conversion_summary=task.get('acceptance_criteria', 'No summary available'),
                active_decisions=[],  # No active decisions for candidate analysis
                glossary=[]   # No glossary for candidate analysis
            )

            semantic_results[engine] = semantic_result

            # Save semantic result
            semantic_filename = f"semantic_{engine}.json"
            semantic_path = os.path.join(arbitration_dir, semantic_filename)

            with open(semantic_path, 'w', encoding='utf-8') as f:
                json.dump(semantic_result, f, indent=2)

        # Add semantic results to the scorecard
        if engine in candidate_scorecards:
            candidate_scorecards[engine]['semantic_equivalence'] = semantic_result.get('semantic_equivalence', 'unknown')
            candidate_scorecards[engine]['semantic_confidence'] = semantic_result.get('confidence', 0.0)
            candidate_scorecards[engine]['requires_human_review'] = semantic_result.get('requires_human_review', False)
            candidate_scorecards[engine]['semantic_risk_flags'] = semantic_result.get('risk_flags', [])

    # Step 4: Select winner based on scores and semantic checks
    print(f"  Selecting winner...")

    winner_engine = _select_winner(
        candidates,
        candidate_scorecards,
        semantic_results,
        use_judge,
        judge_engine,
        task,
        source_repo_path,
        target_repo_path,
        arbitration_dir
    )

    if not winner_engine:
        print(f"  No valid winner selected for task {task_id}")
        return False

    # Step 5: Apply winner output to target repository
    print(f"  Applying winner output from {winner_engine}...")

    winner_candidate = candidates[winner_engine]
    winner_files = winner_candidate['output'].get('files', [])

    # Get the write policy for this task
    write_policy = get_write_policy_for_task(task)

    # Write the winning files to the target repository
    all_files_written_successfully = True
    hash_tracking_info = []

    for file_info in winner_files:
        file_path = file_info.get('path')
        file_content = file_info.get('content', '')

        if not file_path:
            print(f"    Winner file info missing path for {winner_engine}")
            all_files_written_successfully = False
            continue

        # Get merge strategy if applicable
        merge_strategy = task.get('merge_strategy')
        merge_markers = task.get('merge_markers')

        # If this is a merge task, prepare the merged content
        if write_policy == 'merge':
            if not merge_strategy:
                print(f"    Merge policy requires merge_strategy for {winner_engine}")
                all_files_written_successfully = False
                continue

            # Read existing content if file exists
            target_full_path = os.path.join(target_repo_path, file_path.lstrip('/'))
            existing_content = ""
            if os.path.exists(target_full_path):
                with open(target_full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    existing_content = f.read()

            try:
                # Apply merge strategy
                if merge_strategy in ['append_section', 'replace_section_by_marker']:
                    file_content = merge_content(existing_content, file_content, merge_strategy, merge_markers)
                elif merge_strategy in ['json_merge', 'toml_merge']:
                    file_content = merge_content(existing_content, file_content, merge_strategy)
                else:
                    print(f"    Unsupported merge strategy '{merge_strategy}' for {winner_engine}")
                    all_files_written_successfully = False
                    continue
            except Exception as e:
                print(f"    Error during merge for {winner_engine}, file {file_path}: {str(e)}")
                all_files_written_successfully = False
                continue

        # Write the file to the target repository with write policy
        write_result = safe_write_file(
            file_path,
            file_content,
            target_repo_path,
            task_id=task_id,
            write_policy=write_policy
        )

        hash_tracking_info.append({
            "file_path": file_path,
            "write_result": write_result
        })

        if write_result["success"]:
            if verbose:
                action = write_result.get("action", "written")
                target_existed = "existed" if write_result.get("target_before_hash") else "new"
                print(f"[maestro] task {task_id} | src=AI -> tgt={file_path} | {target_existed} | policy={write_policy} | action={action}")

                if write_result.get("changed"):
                    print(f"    Content changed - recording diff...")
                    # Create a patch file for the change
                    patch_filename = f"task_{sanitize_filename(task_id)}_{sanitize_filename(file_path.replace('/', '_'))}.patch"
                    patch_path = os.path.join(".maestro/convert/diffs", patch_filename)

                    # Create simple diff - just log the before/after hashes for now
                    with open(patch_path, 'w', encoding='utf-8') as f:
                        f.write(f"# Patch for {file_path} by task {task_id}\n")
                        f.write(f"# Before hash: {write_result.get('target_before_hash', 'N/A')}\n")
                        f.write(f"# After hash: {write_result.get('target_after_hash', 'N/A')}\n")
                        f.write("# This is a hash-based diff. For detailed diff, use git diff.\n")
                elif write_result.get("action") == "skipped":
                    print(f"    File was skipped due to policy")
        else:
            print(f"    Failed to write {file_path} to target repository")
            all_files_written_successfully = False

    if not all_files_written_successfully:
        return False

    # Step 6: Record decision
    decision_data = {
        'winner_engine': winner_engine,
        'candidates': list(candidates.keys()),
        'candidate_scorecards': candidate_scorecards,
        'semantic_results': semantic_results,
        'used_judge': use_judge,
        'judge_engine': judge_engine if use_judge else None,
        'decision_timestamp': timestamp,
        'task_id': task_id
    }

    decision_path = os.path.join(arbitration_dir, 'decision.json')
    with open(decision_path, 'w', encoding='utf-8') as f:
        json.dump(decision_data, f, indent=2)

    if verbose:
        print(f"  Decision recorded to {decision_path}")

    # Determine hash information for successful task
    final_hash_info = {}
    if hash_tracking_info:
        for hash_info in hash_tracking_info:
            write_result = hash_info['write_result']
            if write_result.get('changed'):
                final_hash_info = {
                    'target_before_hash': write_result.get('target_before_hash'),
                    'target_after_hash': write_result.get('target_after_hash'),
                    'changed': write_result.get('changed'),
                    'previous_known_hash': write_result.get('previous_known_hash')
                }
                break
        if not final_hash_info and hash_tracking_info:
            write_result = hash_tracking_info[0]['write_result']
            final_hash_info = {
                'target_before_hash': write_result.get('target_before_hash'),
                'target_after_hash': write_result.get('target_after_hash'),
                'changed': write_result.get('changed'),
                'previous_known_hash': write_result.get('previous_known_hash')
            }

    # Update task status to completed with hash information
    update_task_status_with_hash_info(plan_path, task_id, 'completed', final_hash_info)

    if verbose:
        print(f"  Completed arbitration for task {task_id}, winner: {winner_engine}")

    return True


def _score_candidate(candidate_data: Dict, task: Dict, source_repo_path: str, target_repo_path: str, arbitration_dir: str) -> Dict:
    """Score a candidate output based on multiple heuristics."""
    output = candidate_data['output']
    scorecard = {
        'protocol_valid': False,
        'deliverables_ok': False,
        'placeholder_penalty': 0,
        'diff_size_metric': 0,
        'estimated_risk_flags': [],
        'validation_cmd_result': 'pending',
        'semantic_equivalence': 'unknown',
        'semantic_confidence': 0.0,
        'requires_human_review': False,
        'semantic_risk_flags': []
    }

    # Protocol validation
    if 'files' in output:
        scorecard['protocol_valid'] = True

        # Deliverables check - do all required files exist?
        required_files = set(task.get('target_files', []))
        output_files = set([f.get('path', '') for f in output['files'] if 'path' in f])
        scorecard['deliverables_ok'] = required_files.issubset(output_files)

        # Calculate diff size and placeholder penalties
        placeholder_penalty = 0
        total_content_size = 0

        for file_info in output['files']:
            content = file_info.get('content', '')
            total_content_size += len(content)

            # Check for placeholder content
            lower_content = content.lower()
            if 'todo' in lower_content or 'fixme' in lower_content or '...' in lower_content or 'not implemented' in lower_content:
                placeholder_penalty += 10  # Significant penalty for placeholders

        scorecard['placeholder_penalty'] = placeholder_penalty
        scorecard['diff_size_metric'] = total_content_size

        # Check for estimated risk flags
        content = "\n".join([f.get('content', '') for f in output['files']])
        if 'unsafe' in content.lower():
            scorecard['estimated_risk_flags'].append('unsafe_code')
        if 'eval' in content.lower():
            scorecard['estimated_risk_flags'].append('dynamic_execution')

        # Run validation command if available
        validation_cmd = task.get('validation_cmd')
        if validation_cmd:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create a temp target to validate against
                for file_info in output['files']:
                    file_path = file_info.get('path')
                    file_content = file_info.get('content', '')

                    if file_path:
                        temp_file_path = os.path.join(temp_dir, file_path.lstrip('/'))
                        os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)

                        with open(temp_file_path, 'w', encoding='utf-8') as f:
                            f.write(file_content)

                try:
                    validation_result = subprocess.run(
                        validation_cmd,
                        shell=True,
                        cwd=temp_dir,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    scorecard['validation_cmd_result'] = validation_result.returncode == 0
                except subprocess.TimeoutExpired:
                    scorecard['validation_cmd_result'] = False
                except Exception:
                    scorecard['validation_cmd_result'] = False
        else:
            scorecard['validation_cmd_result'] = True  # No validation means pass

    return scorecard


def _select_winner(candidates: Dict, scorecards: Dict, semantic_results: Dict, use_judge: bool,
                   judge_engine: str, task: Dict, source_repo_path: str, target_repo_path: str,
                   arbitration_dir: str) -> Optional[str]:
    """Select the winning candidate based on scores and semantic checks."""

    # Filter out candidates with semantic equivalence = 'low' or requires_human_review = true
    valid_candidates = {}
    for engine, scorecard in scorecards.items():
        semantic_result = semantic_results.get(engine, {})
        semantic_equiv = semantic_result.get('semantic_equivalence', 'unknown')
        requires_review = semantic_result.get('requires_human_review', False)

        # Disqualify candidates with low semantic equivalence or requiring human review
        if semantic_equiv == 'low' or requires_review:
            print(f"    Disqualifying {engine}: semantic equivalence = {semantic_equiv}, requires review = {requires_review}")
            continue

        valid_candidates[engine] = {
            'scorecard': scorecard,
            'semantic_result': semantic_result
        }

    if not valid_candidates:
        print("    No valid candidates after semantic filtering")
        return None

    # Score remaining candidates
    candidate_scores = {}
    for engine, data in valid_candidates.items():
        scorecard = data['scorecard']
        semantic_result = data['semantic_result']

        # Calculate score based on various factors
        score = 0

        # Semantic equivalence is primary factor
        equiv = semantic_result.get('semantic_equivalence', 'unknown')
        if equiv == 'high':
            score += 100
        elif equiv == 'medium':
            score += 50
        elif equiv == 'low':
            score += 0  # This should already be filtered out
        else:  # unknown
            score += 25

        # Confidence is secondary
        confidence = semantic_result.get('confidence', 0.0)
        score += confidence * 50

        # Deliverables correctness
        if scorecard.get('deliverables_ok', False):
            score += 20

        # Low placeholder penalty is better
        score -= scorecard.get('placeholder_penalty', 0) * 5

        # Validation command result
        if scorecard.get('validation_cmd_result', True):
            score += 15

        candidate_scores[engine] = score

    # If we have a clear winner or don't need a judge, return the highest score
    sorted_candidates = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)

    if not use_judge or len(sorted_candidates) == 1:
        winner = sorted_candidates[0][0]
        print(f"    Winner selected: {winner} (score: {sorted_candidates[0][1]})")
        return winner

    # If there's a tie or low confidence, use the judge engine
    highest_score = sorted_candidates[0][1]
    tied_or_low_confidence = False

    # Check if top two candidates are close in score or if confidence is low
    if len(sorted_candidates) > 1:
        second_score = sorted_candidates[1][1]
        if abs(highest_score - second_score) <= 10:  # Within 10 points
            tied_or_low_confidence = True
        else:
            # Check if semantic confidence is low for the top candidate
            top_engine = sorted_candidates[0][0]
            top_semantic_conf = semantic_results[top_engine].get('confidence', 0.0)
            if top_semantic_conf < 0.6:  # Low confidence
                tied_or_low_confidence = True

    if tied_or_low_confidence:
        print(f"    Using judge engine {judge_engine} for decision...")

        # Create judge prompt
        judge_prompt = _create_judge_prompt(task, candidates, semantic_results, scorecards)

        # Run judge engine to make final decision
        try:
            run_engine_func = _get_run_engine()
            exit_code, stdout_data, stderr_data = run_engine_func(
                engine=judge_engine,
                prompt=judge_prompt,
                cwd=source_repo_path,
                stream=False,
                timeout=300
            )

            if exit_code == 0:
                # Parse judge output
                judge_result = parse_ai_output(stdout_data)

                if judge_result and 'winner_engine' in judge_result:
                    judge_winner = judge_result['winner_engine']
                    print(f"    Judge selected: {judge_winner}")

                    # Save judge output
                    judge_filename = f"judge_{int(time.time())}.json"
                    judge_path = os.path.join(arbitration_dir, judge_filename)

                    with open(judge_path, 'w', encoding='utf-8') as f:
                        json.dump(judge_result, f, indent=2)

                    return judge_winner
                else:
                    print(f"    Judge output invalid, using top scorer: {sorted_candidates[0][0]}")
                    return sorted_candidates[0][0]
            else:
                print(f"    Judge engine failed, using top scorer: {sorted_candidates[0][0]}")
                return sorted_candidates[0][0]
        except Exception as e:
            print(f"    Judge engine error: {str(e)}, using top scorer: {sorted_candidates[0][0]}")
            return sorted_candidates[0][0]
    else:
        winner = sorted_candidates[0][0]
        print(f"    Winner selected: {winner} (score: {sorted_candidates[0][1]})")
        return winner


def _create_judge_prompt(task: Dict, candidates: Dict, semantic_results: Dict, scorecards: Dict) -> str:
    """Create a prompt for the judge engine to select the best candidate."""

    prompt = f"""# ARBITRATION JUDGE TASK

You are a code quality and correctness judge. Select the best output from multiple AI engines for the following conversion task.

## TASK REQUIREMENTS
{task.get('acceptance_criteria', 'No criteria specified')}

## CANDIDATE OUTPUTS
"""

    for engine, candidate_data in candidates.items():
        output = candidate_data['output']
        semantic_result = semantic_results.get(engine, {})
        scorecard = scorecards.get(engine, {})

        prompt += f"""
### ENGINE: {engine}
- Deliverables OK: {scorecard.get('deliverables_ok', 'N/A')}
- Semantic Equivalence: {semantic_result.get('semantic_equivalence', 'unknown')}
- Confidence: {semantic_result.get('confidence', 0.0)}
- Placeholder Penalty: {scorecard.get('placeholder_penalty', 0)}
- Validation Result: {scorecard.get('validation_cmd_result', 'N/A')}
- Risk Flags: {scorecard.get('estimated_risk_flags', [])}

OUTPUT:
{json.dumps(output, indent=2)}
"""

    prompt += """
## SELECTION CRITERIA
- Semantic equivalence to original functionality is most important
- Avoid outputs with placeholders (TODO, FIXME, etc.)
- Prefer outputs that fully satisfy deliverables
- Consider code quality and maintainability
- Consider risk flags

## OUTPUT FORMAT
Respond with a JSON object containing:
{
  "winner_engine": "engine_name",
  "reasons": ["reason1", "reason2"],
  "risks": ["risk1", "risk2"],
  "requires_human_confirm": false
}

Only respond with the JSON object.
"""

    return prompt


if __name__ == "__main__":
    # Example usage - test with command line arguments
    parser = argparse.ArgumentParser(description="Execute a single file conversion task")
    parser.add_argument("--task-id", required=True, help="ID of the task to execute")
    parser.add_argument("--source-repo", required=True, help="Path to source repository")
    parser.add_argument("--target-repo", required=True, help="Path to target repository")
    parser.add_argument("--plan-path", default=".maestro/convert/plan/plan.json", help="Path to plan file")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    # Load the plan and find the task
    with open(args.plan_path, 'r', encoding='utf-8') as f:
        plan = json.load(f)

    task = None
    for phase in ['scaffold_tasks', 'file_tasks', 'final_sweep_tasks']:
        for t in plan.get(phase, []):
            if t['task_id'] == args.task_id:
                task = t
                break
        if task:
            break

    if not task:
        print(f"Task {args.task_id} not found in plan")
        exit(1)

    # Update status to running
    update_task_status_with_hash_info(args.plan_path, args.task_id, 'running')

    # Execute the task
    success = execute_file_task(task, args.source_repo, args.target_repo, args.verbose)

    # Update final status
    final_status = 'completed' if success else 'failed'
    update_task_status_with_hash_info(args.plan_path, args.task_id, final_status)

    if success:
        print(f"Task {args.task_id} completed successfully")
        exit(0)
    else:
        print(f"Task {args.task_id} failed")
        exit(1)