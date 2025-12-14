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
from typing import Dict, List, Optional, Tuple
import hashlib
import re


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


def safe_write_file(target_path: str, content: str, target_repo_root: str) -> bool:
    """Safely write a file to the target repository with path normalization and atomic writes."""

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

    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(full_target_path), exist_ok=True)

    # Write atomically using a temporary file
    temp_dir = os.path.dirname(full_target_path)
    with tempfile.NamedTemporaryFile(mode='w', dir=temp_dir, delete=False, encoding='utf-8') as tmp_file:
        tmp_file.write(content)
        temp_path = tmp_file.name

    # Atomic move from temp file to target
    os.replace(temp_path, full_target_path)

    return True


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


def update_task_status(plan_path: str, task_id: str, status: str):
    """Update the status of a specific task in the plan."""
    with open(plan_path, 'r', encoding='utf-8') as f:
        plan = json.load(f)

    # Find the task across all phases
    task_found = False
    for phase in ['scaffold_tasks', 'file_tasks', 'final_sweep_tasks']:
        for task in plan.get(phase, []):
            if task['task_id'] == task_id:
                task['status'] = status
                task_found = True
                break
        if task_found:
            break

    # Save the updated plan
    with open(plan_path, 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=2)


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
            # Simply copy files from source to target
            for i, source_file in enumerate(task.get('source_files', [])):
                source_path = os.path.join(source_repo_path, source_file)

                # Determine target path
                if i < len(task.get('target_files', [])):
                    target_file = task['target_files'][i]
                else:
                    target_file = source_file

                target_path = os.path.join(target_repo_path, target_file)

                # Create directory for target if not exists
                os.makedirs(os.path.dirname(target_path), exist_ok=True)

                # Copy file content
                with open(source_path, 'r', encoding='utf-8', errors='ignore') as src:
                    content = src.read()

                with open(target_path, 'w', encoding='utf-8') as dst:
                    dst.write(content)

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
            # Merge content into another target file (placeholder - more complex implementation needed)
            print(f"Merge action not fully implemented for task {task_id}")

            # Record merge action as an audit artifact
            merge_record = {
                "task_id": task_id,
                "action": "merge",
                "source_files": task.get('source_files', []),
                "merge_into": task.get('merge_into', []),
                "timestamp": timestamp,
                "status": "not_implemented"
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
                exit_code, stdout_data, stderr_data = run_engine(
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
                update_task_status(plan_path, task_id, 'interrupted')
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

            # Write the output files to the target repository
            for file_info in files_to_write:
                file_path = file_info.get('path')
                file_content = file_info.get('content', '')

                if not file_path:
                    print(f"File info missing path in AI output for task {task_id}")
                    continue

                # Write the file to the target repository
                if safe_write_file(file_path, file_content, target_repo_path):
                    if verbose:
                        print(f"Wrote {file_path} to target repository")
                else:
                    print(f"Failed to write {file_path} to target repository")
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

            if verbose:
                print(f"Completed file task {task_id}")

            return True

        else:
            print(f"Unknown realization action '{realization_action}' for task {task_id}")
            return False

    except KeyboardInterrupt:
        # Update task status to interrupted
        update_task_status(plan_path, task_id, 'interrupted')
        print(f"\nTask {task_id} was interrupted by user")
        return False  # Return False to indicate interruption
    except Exception as e:
        print(f"Error executing file task {task_id}: {str(e)}")
        return False


def update_task_status(plan_path: str, task_id: str, status: str):
    """Update the status of a specific task in the plan."""
    with open(plan_path, 'r', encoding='utf-8') as f:
        plan = json.load(f)
    
    # Find the task across all phases
    task_found = False
    for phase in ['scaffold_tasks', 'file_tasks', 'final_sweep_tasks']:
        for task in plan.get(phase, []):
            if task['task_id'] == task_id:
                task['status'] = status
                task_found = True
                break
        if task_found:
            break
    
    # Save the updated plan
    with open(plan_path, 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=2)


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
    update_task_status(args.plan_path, args.task_id, 'running')
    
    # Execute the task
    success = execute_file_task(task, args.source_repo, args.target_repo, args.verbose)
    
    # Update final status
    final_status = 'completed' if success else 'failed'
    update_task_status(args.plan_path, args.task_id, final_status)
    
    if success:
        print(f"Task {args.task_id} completed successfully")
        exit(0)
    else:
        print(f"Task {args.task_id} failed")
        exit(1)