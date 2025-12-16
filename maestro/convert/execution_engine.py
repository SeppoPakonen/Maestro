import json
import os
import signal
import sys
from pathlib import Path
from typing import Dict, List, Optional
import subprocess
import threading
import time
import hashlib
from datetime import datetime

# Import the conversion memory module
from maestro.convert.conversion_memory import ConversionMemory, TaskSummary, compute_file_hash

class ConversionExecutor:
    def __init__(self, plan_path: str):
        self.plan_path = plan_path
        self.plan = self._load_plan(plan_path)
        self.running = True
        self.interrupted_task = None
        self.accept_semantic_risk = False  # Default value, can be overridden
        self.setup_signal_handlers()

        # Default arbitration settings
        self.arbitrate = False
        self.arbitrate_engines = 'qwen,claude'
        self.judge_engine = 'codex'
        self.max_candidates = 2
        self.use_judge = True
        
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)
    
    def _handle_interrupt(self, signum, frame):
        """Handle interrupt signals gracefully."""
        print(f"\nReceived signal {signum}. Stopping current task...")
        self.running = False
        # The current subprocess will be terminated by the calling code
        
    def _load_plan(self, plan_path: str) -> Dict:
        """Load the conversion plan from JSON file."""
        with open(plan_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _update_task_status(self, task_id: str, status: str):
        """Update the status of a specific task in the plan."""
        # Find the task across all phases
        for phase in ['scaffold_tasks', 'file_tasks', 'final_sweep_tasks']:
            for task in self.plan.get(phase, []):
                if task['task_id'] == task_id:
                    task['status'] = status
                    break
        
        # Save the updated plan
        with open(self.plan_path, 'w', encoding='utf-8') as f:
            json.dump(self.plan, f, indent=2)
    
    def _create_prompt_for_task(self, task: Dict, source_repo_path: str = ".", target_repo_path: str = ".") -> str:
        """Create prompt content for a given task based on the prompt contract."""
        # Create the prompt template
        prompt = f"""## CONVERSION TASK

### GOAL
{task['acceptance_criteria']}

### CONTEXT
The conversion is taking place between two repositories:
- Source repository: {source_repo_path}
- Target repository: {target_repo_path}

"""
        
        # Add source file contents or references
        if task['source_files']:
            prompt += "### SOURCE FILES\n"
            for source_file in task['source_files']:
                source_file_path = os.path.join(source_repo_path, source_file)
                if os.path.exists(source_file_path):
                    # For large files, create snapshots; for small files, include content
                    file_size = os.path.getsize(source_file_path)
                    if file_size > 10000:  # 10KB threshold - use snapshot
                        snapshot_path = f".maestro/convert/snapshots/{task['task_id']}_{os.path.basename(source_file)}.txt"
                        os.makedirs(os.path.dirname(snapshot_path), exist_ok=True)
                        
                        # Copy content to snapshot
                        with open(source_file_path, 'r', encoding='utf-8', errors='ignore') as sf:
                            content = sf.read()
                        
                        with open(snapshot_path, 'w', encoding='utf-8') as ss:
                            ss.write(content)
                        
                        prompt += f"- File: `{source_file}` (large file - see snapshot: {snapshot_path})\n"
                    else:
                        # Include small file content directly
                        with open(source_file_path, 'r', encoding='utf-8', errors='ignore') as sf:
                            content = sf.read()
                        prompt += f"- File: `{source_file}`\n```\n{content}\n```\n\n"
                else:
                    prompt += f"- File: `{source_file}` (not found)\n"
        
        prompt += f"""
### REQUIREMENTS
- Follow best practices for the target technology stack
- Maintain functionality of the original code
- Write clean, maintainable code
- {task['acceptance_criteria']}
"""
        
        prompt += f"""
### ACCEPTANCE CRITERIA
- {task['acceptance_criteria']}

### DELIVERABLES
- {task['deliverables']}

### ADDITIONAL NOTES
- Use appropriate tools and libraries for the target platform
- Preserve comments and documentation where possible
- Handle dependencies appropriately
"""

        return prompt
    
    def _save_prompt_for_task(self, task_id: str, prompt: str):
        """Save the prompt for a task to a file."""
        prompt_path = f".maestro/convert/inputs/prompt_{task_id}.txt"
        os.makedirs(os.path.dirname(prompt_path), exist_ok=True)
        
        with open(prompt_path, 'w', encoding='utf-8') as f:
            f.write(prompt)
        
        return prompt_path
    
    def _execute_task(self, task: Dict, source_repo_path: str = ".", target_repo_path: str = ".", limit: int = None) -> bool:
        """Execute a single task."""
        task_id = task['task_id']
        print(f"Executing task {task_id}: {task['acceptance_criteria'][:50]}...")

        # Check for violations before executing the task
        memory = ConversionMemory()
        violations = memory.check_task_compliance(task)

        if violations:
            print(f"ERROR: Task {task_id} violates established decisions or conventions:")
            for violation in violations:
                print(f"  - {violation}")

            # Update status to failed due to violation
            self._update_task_status(task_id, 'failed')
            print(f"Task {task_id} was blocked due to violation of established decisions/conventions")
            return False

        # Capture file hashes before task execution
        hashes_before = {}
        for source_file in task.get('source_files', []):
            full_path = os.path.join(source_repo_path, source_file)
            if os.path.exists(full_path):
                hashes_before[source_file] = compute_file_hash(full_path)

        try:
            # Update status to running
            self._update_task_status(task_id, 'running')

            # Check if this is a file task and arbitration is enabled
            if task['phase'] == 'file' and self.arbitrate:
                # Import the realize worker with arbitration support
                from maestro.convert.realize_worker import execute_file_task_with_arbitration

                rehearsal_target = target_repo_path
                # If in rehearsal mode, redirect to rehearsal directory
                if getattr(self, 'rehearsal_mode', False):
                    rehearsal_target = f".maestro/convert/rehearsal/{self.plan.get('pipeline_id', 'default')}/target"
                    os.makedirs(rehearsal_target, exist_ok=True)

                success = execute_file_task_with_arbitration(
                    task,
                    source_repo_path,
                    rehearsal_target,  # Use rehearsal target if in rehearsal mode
                    verbose=True,
                    plan_path=self.plan_path,
                    arbitrate_engines=self.arbitrate_engines.split(','),
                    judge_engine=self.judge_engine,
                    max_candidates=self.max_candidates,
                    use_judge=self.use_judge
                )

                if success:
                    # Update status to completed
                    self._update_task_status(task_id, 'completed')
                    print(f"Task {task_id} completed successfully")
                else:
                    # Update status to failed (unless already marked as interrupted)
                    current_status = task.get('status', 'pending')
                    if current_status != 'interrupted':
                        self._update_task_status(task_id, 'failed')
                    print(f"Task {task_id} failed")
            elif task['phase'] == 'file':
                # Import the realize worker
                from maestro.convert.realize_worker import execute_file_task

                rehearsal_target = target_repo_path
                # If in rehearsal mode, redirect to rehearsal directory
                if getattr(self, 'rehearsal_mode', False):
                    rehearsal_target = f".maestro/convert/rehearsal/{self.plan.get('pipeline_id', 'default')}/target"
                    os.makedirs(rehearsal_target, exist_ok=True)

                success = execute_file_task(task, source_repo_path, rehearsal_target, verbose=True, plan_path=self.plan_path)

                if success:
                    # Update status to completed
                    self._update_task_status(task_id, 'completed')
                    print(f"Task {task_id} completed successfully")
                else:
                    # Update status to failed (unless already marked as interrupted)
                    current_status = task.get('status', 'pending')
                    if current_status != 'interrupted':
                        self._update_task_status(task_id, 'failed')
                    print(f"Task {task_id} failed")
            else:
                # For non-file tasks (scaffold/sweep), use the original logic
                # Create prompt for the task
                prompt = self._create_prompt_for_task(task, source_repo_path, target_repo_path)
                prompt_path = self._save_prompt_for_task(task_id, prompt)

                # Prepare the output directory for this task
                output_dir = f".maestro/convert/outputs/{task_id}"
                os.makedirs(output_dir, exist_ok=True)

                # Select appropriate AI engine based on task['engine']
                if task['engine'] in ['codex', 'gpt4', 'gpt3.5', 'claude']:
                    # Simulate AI processing by calling a mock function
                    # In a real implementation, this would call an AI service
                    success = self._call_ai_engine(task, prompt_path, output_dir)
                elif task['engine'] == 'file_copy':
                    # Copy files directly
                    rehearsal_target = target_repo_path
                    # If in rehearsal mode, redirect to rehearsal directory
                    if getattr(self, 'rehearsal_mode', False):
                        rehearsal_target = f".maestro/convert/rehearsal/{self.plan.get('pipeline_id', 'default')}/target"
                        os.makedirs(rehearsal_target, exist_ok=True)
                    success = self._copy_files(task, source_repo_path, rehearsal_target)
                elif task['engine'] == 'directory_create':
                    # Create directories
                    rehearsal_target = target_repo_path
                    # If in rehearsal mode, redirect to rehearsal directory
                    if getattr(self, 'rehearsal_mode', False):
                        rehearsal_target = f".maestro/convert/rehearsal/{self.plan.get('pipeline_id', 'default')}/target"
                        os.makedirs(rehearsal_target, exist_ok=True)
                    success = self._create_directories(task, rehearsal_target)
                else:
                    # Custom converter or other engines
                    success = self._execute_custom_engine(task, prompt_path, output_dir)

                if success:
                    # Update status to completed
                    self._update_task_status(task_id, 'completed')
                    print(f"Task {task_id} completed successfully")
                else:
                    # Update status to failed
                    self._update_task_status(task_id, 'failed')
                    print(f"Task {task_id} failed")

            # Capture file hashes after task execution
            hashes_after = {}
            target_files = task.get('target_files', [])

            # Determine which target directory to use for hashing
            actual_target_path = target_repo_path
            if getattr(self, 'rehearsal_mode', False):
                actual_target_path = f".maestro/convert/rehearsal/{self.plan.get('pipeline_id', 'default')}/target"

            for target_file in target_files:
                full_path = os.path.join(actual_target_path, target_file)
                if os.path.exists(full_path):
                    hashes_after[target_file] = compute_file_hash(full_path)

            # Generate structured summary regardless of success/failure
            self._generate_structured_summary(task, source_repo_path, target_repo_path, hashes_before, hashes_after, success)

            # Run semantic integrity check for file tasks
            # Run regardless of rehearsal mode to test the semantic analysis
            if task['phase'] == 'file':
                from maestro.convert.semantic_integrity import SemanticIntegrityChecker

                # Use rehearsal target for semantic check if in rehearsal mode
                semantic_target_path = target_repo_path
                if getattr(self, 'rehearsal_mode', False):
                    semantic_target_path = f".maestro/convert/rehearsal/{self.plan.get('pipeline_id', 'default')}/target"

                semantic_checker = SemanticIntegrityChecker()

                # Run semantic check
                semantic_result = semantic_checker.run_semantic_check(task, source_repo_path, semantic_target_path)

                # Classify risk and potentially block pipeline
                risk_level = semantic_checker.classify_risk_level(semantic_result, accept_semantic_risk=self.accept_semantic_risk)

                if risk_level == "block":
                    print(f"BLOCKING: Task {task_id} has low semantic equivalence, blocking pipeline")
                    self._update_task_status(task_id, 'failed')  # Mark as failed due to semantic risk
                    return False
                elif risk_level == "pause":
                    print(f"PAUSING: Task {task_id} requires human review for semantic integrity")
                    # For now, we'll continue in the automated flow, but in interactive mode this would pause
                    # This would be handled differently if we had command-line flags like --accept-semantic-risk
                    accept_semantic_risk = os.environ.get('MAESTRO_ACCEPT_SEMANTIC_RISK', '').lower() == 'true'
                    if not accept_semantic_risk:
                        print(f"Task {task_id} paused for semantic review. Use --accept-semantic-risk to continue.")
                        self._update_task_status(task_id, 'paused_for_review')
                        return False  # Pause execution
                elif risk_level == "escalate":
                    print(f"ESCALATING: Task {task_id} has risky patterns and low confidence")
                    # Log as an issue for further review
                    memory = ConversionMemory()
                    memory.add_issue("medium", f"Task {task_id} has semantic risks: {semantic_result.get('risk_flags', [])}", [task_id])

                # Check semantic drift thresholds - if exceeded, block the entire pipeline
                if not semantic_checker.check_semantic_drift_thresholds():
                    print(f"BLOCKING: Semantic drift thresholds exceeded, blocking entire pipeline")
                    # This would block all further tasks, but let's mark this task as failed and return False
                    # In a real implementation, this would affect the entire plan execution
                    self._update_task_status(task_id, 'failed')
                    return False

                # Check cross-file semantic consistency
                inconsistencies = semantic_checker.check_cross_file_consistency()
                if not semantic_checker.process_cross_file_inconsistencies(inconsistencies):
                    print(f"BLOCKING: Cross-file semantic inconsistencies detected, blocking pipeline")
                    self._update_task_status(task_id, 'failed')
                    return False

            return success

        except KeyboardInterrupt:
            # Handle Ctrl+C during task execution
            self._update_task_status(task_id, 'interrupted')
            print(f"Task {task_id} was interrupted")

            # Even if interrupted, try to generate partial summary
            hashes_after = {}
            target_files = task.get('target_files', [])

            # Determine which target directory to use for hashing
            actual_target_path = target_repo_path
            if getattr(self, 'rehearsal_mode', False):
                actual_target_path = f".maestro/convert/rehearsal/{self.plan.get('pipeline_id', 'default')}/target"

            for target_file in target_files:
                full_path = os.path.join(actual_target_path, target_file)
                if os.path.exists(full_path):
                    hashes_after[target_file] = compute_file_hash(full_path)

            self._generate_structured_summary(task, source_repo_path, target_repo_path, hashes_before, hashes_after, False, ["Task interrupted by user"])
            return False
        except Exception as e:
            # Handle other exceptions
            self._update_task_status(task_id, 'failed')
            print(f"Task {task_id} failed with error: {str(e)}")

            # Generate summary with error info
            hashes_after = {}
            target_files = task.get('target_files', [])

            # Determine which target directory to use for hashing
            actual_target_path = target_repo_path
            if getattr(self, 'rehearsal_mode', False):
                actual_target_path = f".maestro/convert/rehearsal/{self.plan.get('pipeline_id', 'default')}/target"

            for target_file in target_files:
                full_path = os.path.join(actual_target_path, target_file)
                if os.path.exists(full_path):
                    hashes_after[target_file] = compute_file_hash(full_path)

            self._generate_structured_summary(task, source_repo_path, target_repo_path, hashes_before, hashes_after, False, [], [str(e)])
            return False
    
    def _call_ai_engine(self, task: Dict, prompt_path: str, output_dir: str) -> bool:
        """Call the appropriate AI engine to process the task."""
        # This is a simulation since we don't have actual AI services
        # In a real implementation, this would connect to OpenAI, Anthropic, etc.
        
        # For now, just simulate the AI processing by creating dummy output
        for i, target_file in enumerate(task.get('target_files', [])):
            output_path = os.path.join(output_dir, os.path.basename(target_file))
            
            # Create dummy content based on the source files
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# Converted content for {target_file}\n")
                f.write("# This file was generated by the AI conversion process\n")
                f.write(f"# Original source files: {task.get('source_files', [])}\n\n")
                f.write("# [CONVERSION OUTPUT PLACEHOLDER]\n")
                f.write("# Actual AI-generated content would appear here\n")
        
        return True
    
    def _copy_files(self, task: Dict, source_repo_path: str, target_repo_path: str) -> bool:
        """Copy source files to target location."""
        import shutil

        # Determine the actual target path based on rehearsal mode
        actual_target_path = target_repo_path
        if getattr(self, 'rehearsal_mode', False):
            actual_target_path = f".maestro/convert/rehearsal/{self.plan.get('pipeline_id', 'default')}/target"
            os.makedirs(actual_target_path, exist_ok=True)

        for source_file in task.get('source_files', []):
            source_path = os.path.join(source_repo_path, source_file)
            # Use the corresponding target file path or derive from source path
            target_file_index = task['source_files'].index(source_file)
            if target_file_index < len(task.get('target_files', [])):
                target_file = task['target_files'][target_file_index]
            else:
                target_file = source_file  # Default to same name

            target_path = os.path.join(actual_target_path, target_file)

            # Create target directory if it doesn't exist
            os.makedirs(os.path.dirname(target_path), exist_ok=True)

            # Copy the file
            if os.path.exists(source_path):
                shutil.copy2(source_path, target_path)
            else:
                # If source doesn't exist, create an empty file
                with open(target_path, 'w') as f:
                    f.write(f"# Created as part of conversion task\n")
                    f.write(f"# Original file {source_file} was not found\n")

        return True
    
    def _create_directories(self, task: Dict, target_repo_path: str) -> bool:
        """Create directories as specified in target_files."""
        # Determine the actual target path based on rehearsal mode
        actual_target_path = target_repo_path
        if getattr(self, 'rehearsal_mode', False):
            actual_target_path = f".maestro/convert/rehearsal/{self.plan.get('pipeline_id', 'default')}/target"
            os.makedirs(actual_target_path, exist_ok=True)

        for target_dir in task.get('target_files', []):
            # Only create if it represents a directory (ends with / or looks like directory)
            if target_dir.endswith('/') or '.' not in os.path.basename(target_dir):
                dir_path = os.path.join(actual_target_path, target_dir.lstrip('/'))
                os.makedirs(dir_path, exist_ok=True)

        return True
    
    def _generate_structured_summary(self, task: Dict, source_repo_path: str, target_repo_path: str,
                                     hashes_before: Dict[str, str], hashes_after: Dict[str, str],
                                     success: bool, warnings: List[str] = None, errors: List[str] = None):
        """Generate a structured summary of the task execution."""
        if warnings is None:
            warnings = []
        if errors is None:
            errors = []

        # Create a task summary object
        summary = TaskSummary(
            task_id=task['task_id'],
            source_files=task.get('source_files', []),
            target_files=task.get('target_files', [])
        )

        # Add policy information
        write_policy = task.get('write_policy', 'overwrite')
        merge_strategy = task.get('merge_strategy', None)
        summary.add_policy_info(write_policy, merge_strategy)

        # Add any semantic decisions taken (would come from AI processing)
        # In a real implementation, this would be populated from the AI's decisions
        if success and not errors:
            summary.add_semantic_decision(f"Successfully processed {len(task.get('target_files', []))} target files")

        # Add warnings and errors
        for warning in warnings:
            summary.add_warning(warning)

        for error in errors:
            summary.add_error(error)

        # Set hash information
        summary.set_hashes(hashes_before, hashes_after)

        # Add diff references (in a real implementation, actual diff files would be generated)
        # For now, we'll just note that this task was processed
        summary.add_diff_reference(f"task_{task['task_id']}_diff")

        # Save structured summary to file
        summary_file_path = summary.save_to_file()

        print(f"Structured summary saved to: {summary_file_path}")

        # Update the conversion memory with the summary
        memory = ConversionMemory()
        summary_text = f"Task {task['task_id']} completed with {len(task.get('target_files', []))} target files. Success: {success}"
        if errors:
            summary_text += f" Errors: {len(errors)}"
        if warnings:
            summary_text += f" Warnings: {len(warnings)}"

        memory.add_summary_entry(task['task_id'], summary_text)

        # If there were errors, add them as open issues
        if errors:
            for error in errors:
                memory.add_issue("high", f"Error during task {task['task_id']}: {error}", [task['task_id']])

    def _call_ai_engine(self, task: Dict, prompt_path: str, output_dir: str) -> bool:
        """Call the appropriate AI engine to process the task."""
        # This is a simulation since we don't have actual AI services
        # In a real implementation, this would connect to OpenAI, Anthropic, etc.

        # For now, just simulate the AI processing by creating dummy output
        for i, target_file in enumerate(task.get('target_files', [])):
            output_path = os.path.join(output_dir, os.path.basename(target_file))

            # Create dummy content based on the source files
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# Converted content for {target_file}\n")
                f.write("# This file was generated by the AI conversion process\n")
                f.write(f"# Original source files: {task.get('source_files', [])}\n\n")
                f.write("# [CONVERSION OUTPUT PLACEHOLDER]\n")
                f.write("# Actual AI-generated content would appear here\n")

        return True

    def _execute_custom_engine(self, task: Dict, prompt_path: str, output_dir: str) -> bool:
        """Execute custom conversion engine."""
        # Placeholder for custom engines
        for target_file in task.get('target_files', []):
            output_path = os.path.join(output_dir, os.path.basename(target_file))

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# Custom engine output for {target_file}\n")
                f.write("# This file was generated by a custom conversion process\n")
                f.write(f"# Task: {task.get('acceptance_criteria', 'N/A')}\n")

        return True
    
    def _resolve_dependencies(self, task: Dict) -> bool:
        """Check if task dependencies are met."""
        for dep_id in task.get('depends_on', []):
            # Find the dependent task across all phases
            found = False
            for phase in ['scaffold_tasks', 'file_tasks', 'final_sweep_tasks']:
                for t in self.plan.get(phase, []):
                    if t['task_id'] == dep_id:
                        if t['status'] != 'completed':
                            return False  # Dependency not met
                        found = True
                        break
                if found:
                    break
            else:
                print(f"Warning: Dependency task {dep_id} not found in plan")
        
        return True
    
    def execute_plan(self, source_repo_path: str = ".", target_repo_path: str = ".", limit: int = None, rehearsal_mode: bool = False) -> bool:
        """Execute the conversion plan task by task."""
        print(f"Starting execution of conversion plan: {self.plan_path}")
        print(f"Source: {source_repo_path}, Target: {target_repo_path}")
        if rehearsal_mode:
            print("⚠️  REHEARSAL MODE: No writes to target will occur")

        tasks_executed = 0

        # Store rehearsal mode for use in task execution
        self.rehearsal_mode = rehearsal_mode

        # Execute scaffold tasks first
        for task in self.plan.get('scaffold_tasks', []):
            if limit and tasks_executed >= limit:
                print(f"Reached execution limit of {limit} tasks")
                break

            if not self.running:
                print("Execution was interrupted")
                return False

            # Check dependencies before executing
            if not self._resolve_dependencies(task):
                print(f"Skipping task {task['task_id']} due to unmet dependencies")
                continue

            success = self._execute_task(task, source_repo_path, target_repo_path)
            if success:
                tasks_executed += 1

            # Check for checkpoints after the task
            checkpoint = self._find_checkpoint_after_task(task['task_id'])
            if checkpoint:
                checkpoint_result = self._handle_checkpoint(checkpoint, source_repo_path, target_repo_path, tasks_executed)
                if checkpoint_result == 'reject':
                    print(f"Checkpoint {checkpoint['checkpoint_id']} rejected. Stopping execution.")
                    return False
                elif checkpoint_result == 'override':
                    print(f"Checkpoint {checkpoint['checkpoint_id']} overridden. Continuing execution.")
                elif checkpoint_result == 'approve':
                    print(f"Checkpoint {checkpoint['checkpoint_id']} approved. Continuing execution.")
                else:
                    # Default is to wait for approval if auto_continue is false
                    if not checkpoint.get('auto_continue', False):
                        # Wait for user approval
                        user_action = self._wait_for_checkpoint_approval(checkpoint['checkpoint_id'])
                        if user_action == 'reject':
                            print(f"Checkpoint {checkpoint['checkpoint_id']} rejected by user. Stopping execution.")
                            return False
                        elif user_action == 'override':
                            print(f"Checkpoint {checkpoint['checkpoint_id']} overridden by user. Continuing execution.")
                        else:  # approve
                            print(f"Checkpoint {checkpoint['checkpoint_id']} approved by user. Continuing execution.")

        # Execute file tasks next
        for task in self.plan.get('file_tasks', []):
            if limit and tasks_executed >= limit:
                print(f"Reached execution limit of {limit} tasks")
                break

            if not self.running:
                print("Execution was interrupted")
                return False

            # Check dependencies before executing
            if not self._resolve_dependencies(task):
                print(f"Skipping task {task['task_id']} due to unmet dependencies")
                continue

            success = self._execute_task(task, source_repo_path, target_repo_path)
            if success:
                tasks_executed += 1

            # Check for checkpoints after the task
            checkpoint = self._find_checkpoint_after_task(task['task_id'])
            if checkpoint:
                checkpoint_result = self._handle_checkpoint(checkpoint, source_repo_path, target_repo_path, tasks_executed)
                if checkpoint_result == 'reject':
                    print(f"Checkpoint {checkpoint['checkpoint_id']} rejected. Stopping execution.")
                    return False
                elif checkpoint_result == 'override':
                    print(f"Checkpoint {checkpoint['checkpoint_id']} overridden. Continuing execution.")
                elif checkpoint_result == 'approve':
                    print(f"Checkpoint {checkpoint['checkpoint_id']} approved. Continuing execution.")
                else:
                    # Default is to wait for approval if auto_continue is false
                    if not checkpoint.get('auto_continue', False):
                        # Wait for user approval
                        user_action = self._wait_for_checkpoint_approval(checkpoint['checkpoint_id'])
                        if user_action == 'reject':
                            print(f"Checkpoint {checkpoint['checkpoint_id']} rejected by user. Stopping execution.")
                            return False
                        elif user_action == 'override':
                            print(f"Checkpoint {checkpoint['checkpoint_id']} overridden by user. Continuing execution.")
                        else:  # approve
                            print(f"Checkpoint {checkpoint['checkpoint_id']} approved by user. Continuing execution.")

        # Execute final sweep tasks last
        for task in self.plan.get('final_sweep_tasks', []):
            if limit and tasks_executed >= limit:
                print(f"Reached execution limit of {limit} tasks")
                break

            if not self.running:
                print("Execution was interrupted")
                return False

            # Check dependencies before executing
            if not self._resolve_dependencies(task):
                print(f"Skipping task {task['task_id']} due to unmet dependencies")
                continue

            success = self._execute_task(task, source_repo_path, target_repo_path)
            if success:
                tasks_executed += 1

            # Check for checkpoints after the task
            checkpoint = self._find_checkpoint_after_task(task['task_id'])
            if checkpoint:
                checkpoint_result = self._handle_checkpoint(checkpoint, source_repo_path, target_repo_path, tasks_executed)
                if checkpoint_result == 'reject':
                    print(f"Checkpoint {checkpoint['checkpoint_id']} rejected. Stopping execution.")
                    return False
                elif checkpoint_result == 'override':
                    print(f"Checkpoint {checkpoint['checkpoint_id']} overridden. Continuing execution.")
                elif checkpoint_result == 'approve':
                    print(f"Checkpoint {checkpoint['checkpoint_id']} approved. Continuing execution.")
                else:
                    # Default is to wait for approval if auto_continue is false
                    if not checkpoint.get('auto_continue', False):
                        # Wait for user approval
                        user_action = self._wait_for_checkpoint_approval(checkpoint['checkpoint_id'])
                        if user_action == 'reject':
                            print(f"Checkpoint {checkpoint['checkpoint_id']} rejected by user. Stopping execution.")
                            return False
                        elif user_action == 'override':
                            print(f"Checkpoint {checkpoint['checkpoint_id']} overridden by user. Continuing execution.")
                        else:  # approve
                            print(f"Checkpoint {checkpoint['checkpoint_id']} approved by user. Continuing execution.")

        print(f"Plan execution completed. {tasks_executed} tasks processed.")
        return True

    def _find_checkpoint_after_task(self, task_id: str) -> Optional[Dict]:
        """Find a checkpoint that should trigger after the specified task."""
        checkpoints = self.plan.get('checkpoints', [])
        for checkpoint in checkpoints:
            if task_id in checkpoint.get('after_tasks', []):
                # Check if checkpoint has already been processed
                if checkpoint.get('status', 'pending') in ['pending', 'approved', 'skipped']:
                    return checkpoint
        return None

    def _handle_checkpoint(self, checkpoint: Dict, source_repo_path: str, target_repo_path: str, tasks_completed: int) -> str:
        """Handle a checkpoint by summarizing and checking requirements."""
        checkpoint_id = checkpoint['checkpoint_id']

        print(f"\n🚨 REACHED CHECKPOINT: {checkpoint_id} - {checkpoint.get('label', 'No label')}")

        # Create checkpoint artifact directory
        checkpoint_artifact_dir = f".maestro/convert/checkpoints/{checkpoint_id}"
        os.makedirs(checkpoint_artifact_dir, exist_ok=True)

        # Generate checkpoint summary
        summary = self._generate_checkpoint_summary(checkpoint, source_repo_path, target_repo_path, tasks_completed)

        # Save checkpoint summary to artifact
        checkpoint_summary_path = os.path.join(checkpoint_artifact_dir, "summary.json")
        with open(checkpoint_summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

        print(f"Checkpoint summary saved to: {checkpoint_summary_path}")

        # Check requirements
        requires = checkpoint.get('requires', [])
        all_requirements_met = True

        for requirement in requires:
            if requirement == "semantic_ok":
                # Check if recent semantic issues are resolved
                from maestro.convert.semantic_integrity import SemanticIntegrityChecker
                checker = SemanticIntegrityChecker()
                summary = checker.get_summary()
                if summary.get('unresolved_semantic_warnings', 0) > 0:
                    print(f"⚠️  Requirement '{requirement}' not met: {summary['unresolved_semantic_warnings']} unresolved semantic warnings")
                    all_requirements_met = False
            elif requirement == "build_pass":
                # In a real implementation, this would run the build command
                print(f"ℹ️  Requirement '{requirement}' needs to be checked with build command")

        if not all_requirements_met:
            print(f"⚠️  Some requirements not met for checkpoint {checkpoint_id}")
            print(f"   You may need to address issues before approving this checkpoint")

        # Return based on auto_continue setting
        if checkpoint.get('auto_continue', False):
            self._update_checkpoint_status(checkpoint_id, 'completed')
            return 'approve'
        else:
            self._update_checkpoint_status(checkpoint_id, 'pending')
            return 'pending'  # Indicates we need human action

    def _generate_checkpoint_summary(self, checkpoint: Dict, source_repo_path: str, target_repo_path: str, tasks_completed: int) -> Dict:
        """Generate a summary for the checkpoint."""
        # Get recent tasks since last checkpoint
        # For now, we'll just return the checkpoint information and basic stats
        from semantic_integrity import SemanticIntegrityChecker
        from maestro.convert.conversion_memory import ConversionMemory

        memory = ConversionMemory()
        checker = SemanticIntegrityChecker()

        # Gather semantic summary
        semantic_summary = checker.get_summary()

        # Get recent issues
        recent_issues = [issue for issue in memory.load_open_issues()
                        if issue.get('status', 'open') in ['open', 'investigating']]

        # Create checkpoint summary object
        summary = {
            "checkpoint_id": checkpoint['checkpoint_id'],
            "label": checkpoint.get('label', ''),
            "timestamp": datetime.now().isoformat(),
            "tasks_completed_since_last_checkpoint": tasks_completed,  # This is cumulative, improve in actual implementation
            "semantic_summary": semantic_summary,
            "open_issues_added_since_last_checkpoint": len(recent_issues),
            "top_risks": semantic_summary.get('cumulative_risk_flags', {}),
            "requires": checkpoint.get('requires', []),
            "auto_continue": checkpoint.get('auto_continue', False)
        }

        return summary

    def _update_checkpoint_status(self, checkpoint_id: str, status: str):
        """Update the status of a checkpoint in the plan."""
        checkpoints = self.plan.get('checkpoints', [])
        for checkpoint in checkpoints:
            if checkpoint['checkpoint_id'] == checkpoint_id:
                checkpoint['status'] = status
                break

        # Save the updated plan
        with open(self.plan_path, 'w', encoding='utf-8') as f:
            json.dump(self.plan, f, indent=2)

    def _wait_for_checkpoint_approval(self, checkpoint_id: str) -> str:
        """Wait for user approval of a checkpoint. In rehearsal mode, auto-approve."""
        # If we're in rehearsal mode, we'll auto-approve since no real changes are made
        if getattr(self, 'rehearsal_mode', False):
            print(f"Rehearsal mode: Auto-approving checkpoint {checkpoint_id}")
            self._update_checkpoint_status(checkpoint_id, 'approved')
            return 'approve'

        # Otherwise, user needs to approve via CLI command
        print(f"Checkpoint {checkpoint_id} requires your approval.")
        print(f"Run one of the following commands to continue:")
        print(f"  maestro convert checkpoint approve {checkpoint_id}")
        print(f"  maestro convert checkpoint reject {checkpoint_id}")
        print(f"  maestro convert checkpoint override {checkpoint_id}")

        # In a real implementation, this would wait for the user to run the CLI command
        # For now, we'll just return 'approve' to allow the simulation to continue
        # But in practice, the execution engine would need to pause and resume
        return 'wait'  # This would indicate the need to pause execution

def execute_conversion(source_repo_path: str, target_repo_path: str, limit: int = None, resume: bool = False, accept_semantic_risk: bool = False, arbitrate: bool = False, arbitrate_engines: str = 'qwen,claude', judge_engine: str = 'codex', max_candidates: int = 2, use_judge: bool = True, rehearsal_mode: bool = False):
    """Main function to execute the conversion process."""
    plan_path = ".maestro/convert/plan/plan.json"

    if not os.path.exists(plan_path):
        print(f"No plan found at {plan_path}. Run 'convert plan' first.")
        return False

    executor = ConversionExecutor(plan_path)

    # Store the accept_semantic_risk flag in the executor so it can be used during task execution
    executor.accept_semantic_risk = accept_semantic_risk

    # Store arbitration parameters
    executor.arbitrate = arbitrate
    executor.arbitrate_engines = arbitrate_engines
    executor.judge_engine = judge_engine
    executor.max_candidates = max_candidates
    executor.use_judge = use_judge

    # Store rehearsal mode
    executor.rehearsal_mode = rehearsal_mode

    # If resuming, we'll pick up from where we left off based on task statuses
    # The executor already handles status tracking in the plan file
    success = executor.execute_plan(source_repo_path, target_repo_path, limit, rehearsal_mode=rehearsal_mode)

    return success