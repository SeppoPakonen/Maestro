import json
import os
import signal
import sys
from pathlib import Path
from typing import Dict, List, Optional
import subprocess
import threading
import time

class ConversionExecutor:
    def __init__(self, plan_path: str):
        self.plan_path = plan_path
        self.plan = self._load_plan(plan_path)
        self.running = True
        self.interrupted_task = None
        self.setup_signal_handlers()
        
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
        
        try:
            # Update status to running
            self._update_task_status(task_id, 'running')
            
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
                success = self._copy_files(task, source_repo_path, target_repo_path)
            elif task['engine'] == 'directory_create':
                # Create directories
                success = self._create_directories(task, target_repo_path)
            else:
                # Custom converter or other engines
                success = self._execute_custom_engine(task, prompt_path, output_dir)
            
            if success:
                # Update status to completed
                self._update_task_status(task_id, 'completed')
                print(f"Task {task_id} completed successfully")
                return True
            else:
                # Update status to failed
                self._update_task_status(task_id, 'failed')
                print(f"Task {task_id} failed")
                return False
                
        except KeyboardInterrupt:
            # Handle Ctrl+C during task execution
            self._update_task_status(task_id, 'interrupted')
            print(f"Task {task_id} was interrupted")
            return False
        except Exception as e:
            # Handle other exceptions
            self._update_task_status(task_id, 'failed')
            print(f"Task {task_id} failed with error: {str(e)}")
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
        
        for source_file in task.get('source_files', []):
            source_path = os.path.join(source_repo_path, source_file)
            # Use the corresponding target file path or derive from source path
            target_file_index = task['source_files'].index(source_file)
            if target_file_index < len(task.get('target_files', [])):
                target_file = task['target_files'][target_file_index]
            else:
                target_file = source_file  # Default to same name
            
            target_path = os.path.join(target_repo_path, target_file)
            
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
        for target_dir in task.get('target_files', []):
            # Only create if it represents a directory (ends with / or looks like directory)
            if target_dir.endswith('/') or '.' not in os.path.basename(target_dir):
                dir_path = os.path.join(target_repo_path, target_dir.lstrip('/'))
                os.makedirs(dir_path, exist_ok=True)
        
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
    
    def execute_plan(self, source_repo_path: str = ".", target_repo_path: str = ".", limit: int = None) -> bool:
        """Execute the conversion plan task by task."""
        print(f"Starting execution of conversion plan: {self.plan_path}")
        print(f"Source: {source_repo_path}, Target: {target_repo_path}")
        
        tasks_executed = 0
        
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
        
        print(f"Plan execution completed. {tasks_executed} tasks processed.")
        return True

def execute_conversion(source_repo_path: str, target_repo_path: str, limit: int = None, resume: bool = False):
    """Main function to execute the conversion process."""
    plan_path = ".maestro/convert/plan/plan.json"
    
    if not os.path.exists(plan_path):
        print(f"No plan found at {plan_path}. Run 'convert plan' first.")
        return False
    
    executor = ConversionExecutor(plan_path)
    
    # If resuming, we'll pick up from where we left off based on task statuses
    # The executor already handles status tracking in the plan file
    success = executor.execute_plan(source_repo_path, target_repo_path, limit)
    
    return success