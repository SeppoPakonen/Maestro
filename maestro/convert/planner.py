import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from maestro.convert.inventory_generator import load_inventory
from maestro.convert.conversion_memory import ConversionMemory, TaskSummary
from maestro.convert.context_builder import ContextBuilder
import maestro.convert.playbook_manager

def generate_task_id():
    """Generate a unique task ID."""
    return f"task_{uuid.uuid4().hex[:8]}"

def create_scaffold_tasks(target_inventory: Dict) -> List[Dict]:
    """Create scaffold tasks to establish project structure."""
    tasks = []

    # If target is empty, create basic scaffolding tasks
    if not target_inventory or target_inventory.get('total_count', 0) == 0:
        # Create basic project infrastructure
        # Use gemini for scaffolding tasks (broad context for project structure)
        scaffold_tasks = [
            {
                "task_id": generate_task_id(),
                "phase": "scaffold",
                "title": "Set up basic project files",
                "source_files": [],
                "target_files": ["README.md", "package.json", "requirements.txt", ".gitignore"],
                "engine": "gemini",  # Default for scaffolding: broad context
                "prompt_ref": "inputs/scaffold_project_setup.txt",
                "acceptance_criteria": ["Basic project files created with appropriate content"],
                "deliverables": ["README.md", "package.json", "requirements.txt", ".gitignore"],
                "depends_on": [],
                "status": "pending"
            },
            {
                "task_id": generate_task_id(),
                "phase": "scaffold",
                "title": "Create directory structure",
                "source_files": [],
                "target_files": ["src/", "tests/", "docs/"],
                "engine": "qwen",  # Default for directory creation: efficient for simple tasks
                "prompt_ref": "inputs/scaffold_directory_structure.txt",
                "acceptance_criteria": ["Directory structure created according to best practices for target language"],
                "deliverables": ["src/", "tests/", "docs/"],
                "depends_on": [],
                "status": "pending"
            }
        ]

        for task in scaffold_tasks:
            tasks.append(task)

    return tasks

def create_file_conversion_tasks(source_inventory: Dict, target_inventory: Dict) -> List[Dict]:
    """Create file-by-file conversion tasks based on source inventory."""
    tasks = []
    
    if not source_inventory or 'files' not in source_inventory:
        return tasks

    # Group source files by characteristics for optimized processing
    files_by_ext = {}
    for file_info in source_inventory.get('files', []):
        ext = file_info['path'].split('.')[-1] if '.' in file_info['path'] else 'no_ext'
        if ext not in files_by_ext:
            files_by_ext[ext] = []
        files_by_ext[ext].append(file_info)
    
    # Create tasks for each group of files
    for ext, files in files_by_ext.items():
        # Determine appropriate engine based on language
        sample_lang = files[0]['language'] if files else 'Unknown'
        
        # Map languages to appropriate AI engines (only allowed engines from schema)
        lang_to_engine = {
            'Python': 'codex',
            'JavaScript': 'claude',
            'TypeScript': 'claude',
            'Java': 'claude',
            'C++': 'claude',
            'C': 'claude',
            'C#': 'claude',
            'Go': 'claude',
            'Rust': 'claude',
            'Ruby': 'claude',
            'PHP': 'claude',
            'Swift': 'claude',
            'Kotlin': 'claude',
            'Scala': 'claude',
            'HTML': 'qwen',
            'CSS': 'qwen',
            'JSON': 'qwen',
            'YAML': 'qwen',
            'Markdown': 'qwen',
            'Shell': 'qwen',
            'Configuration': 'qwen',
            'Text': 'qwen',
            'Dockerfile': 'qwen'
        }
        
        # Use specific engine if available, otherwise default to 'qwen' for file tasks
        engine = lang_to_engine.get(sample_lang, 'qwen')

        # Create a task for this group of files
        source_paths = [f['path'] for f in files]
        target_paths = [f['path'] for f in files]  # Same names initially

        # Decide on conversion vs copy based on file type
        if sample_lang in ['Image', 'Binary', 'Unknown']:  # Placeholder - will be handled differently
            task_type = "file_copy"
            engine = "file_copy"
            acceptance_criteria = ["Files copied to target location without modification"]
        else:
            task_type = "file_conversion"
            acceptance_criteria = ["Source files converted appropriately to target technology stack"]

        task = {
            "task_id": generate_task_id(),
            "phase": "file",
            "title": f"Convert {ext} files",
            "source_files": source_paths,
            "target_files": target_paths,
            "engine": engine,
            "prompt_ref": f"inputs/convert_files_{ext}.txt",
            "acceptance_criteria": acceptance_criteria,
            "deliverables": target_paths,
            "depends_on": [],  # Dependencies will be determined later
            "status": "pending"
        }
        
        tasks.append(task)
    
    return tasks

def create_sweep_tasks(source_inventory: Dict, target_inventory: Dict) -> List[Dict]:
    """Create final sweep tasks to verify completeness."""
    sweep_tasks = [
        {
            "task_id": generate_task_id(),
            "phase": "sweep",
            "title": "Verify conversion coverage",
            "source_files": [f['path'] for f in source_inventory.get('files', [])],
            "target_files": [f['path'] for f in target_inventory.get('files', []) if f.get('path', '')],
            "engine": "gemini",  # Default for sweep: large text synthesis for verification
            "prompt_ref": "inputs/verify_conversion_coverage.txt",
            "acceptance_criteria": ["All source files have been accounted for in target conversion"],
            "deliverables": [".maestro/convert/reports/coverage.json"],
            "depends_on": [],
            "status": "pending"
        },
        {
            "task_id": generate_task_id(),
            "phase": "sweep",
            "title": "Generate final summary report",
            "source_files": [],
            "target_files": [".maestro/convert/reports/final_summary.md"],
            "engine": "gemini",  # Default for sweeps: good for comprehensive reporting
            "prompt_ref": "inputs/generate_final_report.txt",
            "acceptance_criteria": ["Comprehensive report of conversion process and results"],
            "deliverables": [".maestro/convert/reports/final_summary.md"],
            "depends_on": [sweep_tasks[0]['task_id']] if 'sweep_tasks' in locals() else [],
            "status": "pending"
        }
    ]

    return sweep_tasks

def generate_conversion_plan(source_repo_path: str, target_repo_path: str, plan_output_path: str, rehearsal_mode: bool = False) -> Dict:
    """Generate a complete conversion plan JSON based on source and target inventories."""

    # Check if there's an active playbook binding
    playbook_manager_instance = maestro.convert.playbook_manager.PlaybookManager()
    active_binding = playbook_manager_instance.get_active_playbook_binding()
    active_playbook = None

    if active_binding:
        playbook_id = active_binding['playbook_id']
        active_playbook = playbook_manager_instance.load_playbook(playbook_id)
        if active_playbook:
            print(f"[PLANNER] Using active playbook: {active_playbook.id} (version {active_playbook.version})")
        else:
            print(f"[WARNING] Active binding exists for playbook {playbook_id} but playbook not found")

    # Load inventories
    source_inventory_path = ".maestro/convert/inventory/source_files.json"
    target_inventory_path = ".maestro/convert/inventory/target_files.json"

    source_inventory = load_inventory(source_inventory_path)
    target_inventory = load_inventory(target_inventory_path)

    if not source_inventory:
        raise ValueError(f"Source inventory not found at {source_inventory_path}")

    # Initialize conversion memory
    memory = ConversionMemory()

    # Make initial decisions based on source/target analysis
    # Determine target language based on source characteristics
    source_extensions = {}
    for file in source_inventory.get('files', []):
        ext = file['path'].split('.')[-1] if '.' in file['path'] else 'no_ext'
        source_extensions[ext] = source_extensions.get(ext, 0) + 1

    # Determine likely target language (this is a simplified approach)
    # In a real implementation, the user would specify this
    most_common_ext = max(source_extensions, key=source_extensions.get) if source_extensions else 'unknown'

    # Record the target language decision if not already decided
    if not memory.get_applicable_decisions(['language_target']):
        memory.add_decision(
            category="language_target",
            description="Target language for conversion",
            value=determine_target_language_from_source(most_common_ext),  # Helper function
            justification=f"Inferred from source language extension: {most_common_ext}"
        )

    # Create the plan following the new schema
    plan = {
        "plan_version": "1.0",
        "pipeline_id": f"conversion-plan-{uuid.uuid4().hex[:8]}",
        "intent": f"Convert {source_repo_path} to {target_repo_path}",
        "created_at": datetime.utcnow().isoformat(),
        "source": {
            "path": source_repo_path
        },
        "target": {
            "path": target_repo_path
        },
        "scaffold_tasks": [],
        "file_tasks": [],
        "final_sweep_tasks": [],
        "source_inventory": source_inventory_path,
        "target_inventory": target_inventory_path
    }

    # Apply playbook-specific modifications if active
    if active_playbook:
        # Ensure the conversion intent matches playbook intent
        plan['intent'] = f"{active_playbook.intent}: Convert {source_repo_path} to {target_repo_path} using playbook {active_playbook.id}"

        # Apply checkpoint policy from playbook
        if active_playbook.checkpoint_policy:
            # Store the checkpoint policy in the plan for later use
            plan['checkpoint_policy'] = active_playbook.checkpoint_policy

    # Create scaffold tasks (these come first)
    plan['scaffold_tasks'] = create_scaffold_tasks(target_inventory)

    # Create file conversion tasks (these process the source files)
    plan['file_tasks'] = create_file_conversion_tasks(source_inventory, target_inventory)

    # Create final sweep tasks (these verify completion)
    plan['final_sweep_tasks'] = create_sweep_tasks(source_inventory, target_inventory)

    # Apply memory-driven enhancements to the plan
    plan = apply_memory_guidance_to_plan(plan, memory)

    # Add checkpoints based on playbook policy, rehearsal mode, or auto-checkpoints
    if rehearsal_mode or (active_playbook and active_playbook.checkpoint_policy):
        # Add checkpoints to allow human review during rehearsal or according to playbook
        plan = add_auto_checkpoints(plan, memory, active_playbook)

    # Save the plan
    plan_dir = os.path.dirname(plan_output_path)
    if plan_dir:
        os.makedirs(plan_dir, exist_ok=True)
    with open(plan_output_path, 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=2)

    # Add a summary for the planning phase
    summary = TaskSummary(
        task_id="planning_phase",
        source_files=[source_inventory_path],
        target_files=[plan_output_path]
    )
    summary.add_semantic_decision(f"Generated conversion plan with memory guidance (rehearsal_mode: {rehearsal_mode})")
    summary.save_to_file()

    return plan


def add_auto_checkpoints(plan: Dict, memory: ConversionMemory, active_playbook=None) -> Dict:
    """Add automatic checkpoints to the plan based on risk assessment and playbook policy."""

    # Get all task IDs for checkpoint insertion
    all_task_ids = []
    all_task_ids.extend([task['task_id'] for task in plan.get('scaffold_tasks', [])])
    all_task_ids.extend([task['task_id'] for task in plan.get('file_tasks', [])])
    all_task_ids.extend([task['task_id'] for task in plan.get('final_sweep_tasks', [])])

    # Create checkpoints automatically
    checkpoints = []

    # Add checkpoint after scaffold tasks
    scaffold_tasks = plan.get('scaffold_tasks', [])
    if scaffold_tasks:
        checkpoint = {
            "checkpoint_id": "CP-Scaffold-Setup",
            "after_tasks": [task['task_id'] for task in scaffold_tasks],
            "label": "Scaffold tasks completed - Basic structure in place",
            "requires": ["semantic_ok"],
            "auto_continue": False,
            "status": "pending"
        }
        checkpoints.append(checkpoint)

    # Add checkpoint after every N file tasks according to playbook policy or default
    file_tasks = plan.get('file_tasks', [])
    if file_tasks:
        # Use playbook policy for checkpoint frequency, default to 5 if not specified
        checkpoint_frequency = 5
        if active_playbook and active_playbook.checkpoint_policy:
            freq = active_playbook.checkpoint_policy.get('after_files', 5)
            checkpoint_frequency = freq

        for i in range(0, len(file_tasks), checkpoint_frequency):
            batch_end = min(i + checkpoint_frequency, len(file_tasks))
            batch_task_ids = [task['task_id'] for task in file_tasks[i:batch_end]]

            checkpoint = {
                "checkpoint_id": f"CP-FileBatch-{i//checkpoint_frequency + 1}",
                "after_tasks": batch_task_ids,
                "label": f"File conversion batch {i//checkpoint_frequency + 1} completed",
                "requires": ["semantic_ok"],
                "auto_continue": False,
                "status": "pending"
            }
            checkpoints.append(checkpoint)

    # Add checkpoint after sweep tasks
    sweep_tasks = plan.get('final_sweep_tasks', [])
    if sweep_tasks:
        checkpoint = {
            "checkpoint_id": "CP-Final-Sweep",
            "after_tasks": [task['task_id'] for task in sweep_tasks],
            "label": "Final sweep tasks completed",
            "requires": ["build_pass", "semantic_ok"],
            "auto_continue": False,
            "status": "pending"
        }
        checkpoints.append(checkpoint)

    # Add the checkpoints to the plan
    plan['checkpoints'] = checkpoints

    return plan


def determine_target_language_from_source(source_ext: str) -> str:
    """Determine appropriate target language based on source extension."""
    # Simple mapping - in reality this would be more sophisticated
    ext_to_lang = {
        'js': 'python',
        'ts': 'python',
        'java': 'python',
        'cpp': 'python',
        'c': 'python',
        'py': 'python',  # No conversion needed, but for example
        'cs': 'python',
        'go': 'python',
        'rs': 'python',
    }
    return ext_to_lang.get(source_ext, 'python')  # Default to python


def apply_memory_guidance_to_plan(plan: Dict, memory: ConversionMemory) -> Dict:
    """Apply memory-based guidance to enhance the plan."""
    # Get relevant decisions and conventions to guide the plan
    decisions = memory.load_decisions()
    conventions = memory.load_conventions()

    # Apply engine decisions if specified
    for decision in decisions:
        if decision.get('category') == 'engine_choice':
            # Apply this engine choice to all tasks of the specified type
            engine_value = decision.get('value')
            for phase in ['scaffold_tasks', 'file_tasks', 'final_sweep_tasks']:
                for task in plan.get(phase, []):
                    # Override engine if decision applies to this task type
                    task['engine'] = engine_value

    # Apply language target decisions to file paths if needed
    language_decisions = [d for d in decisions if d.get('category') == 'language_target']
    if language_decisions:
        target_language = language_decisions[0].get('value', 'python')
        # Update file extensions based on target language
        ext_mapping = {
            'python': {'.js': '.py', '.ts': '.py', '.java': '.py', '.cpp': '.py'},
            'javascript': {'.py': '.js', '.java': '.js', '.cpp': '.js'},
            # Add more mappings as needed
        }

        mapping = ext_mapping.get(target_language, {})

        for phase in ['file_tasks']:
            for task in plan.get(phase, []):
                new_target_files = []
                for target_file in task.get('target_files', []):
                    for old_ext, new_ext in mapping.items():
                        if target_file.endswith(old_ext):
                            new_target_files.append(target_file[:-len(old_ext)] + new_ext)
                            break
                    else:
                        new_target_files.append(target_file)
                task['target_files'] = new_target_files

    # Integrate semantic awareness into the plan
    integrate_semantic_awareness(plan, memory)

    return plan


def integrate_semantic_awareness(plan: Dict, memory: ConversionMemory):
    """Integrate semantic awareness into the plan by considering past semantic warnings."""
    try:
        # Import semantic integrity module to get semantic summary and issues
        from semantic_integrity import SemanticIntegrityChecker

        checker = SemanticIntegrityChecker()

        # Add semantic summary information to the plan
        plan['semantic_summary'] = checker.get_summary()

        # Get open semantic issues that might affect the planning
        open_semantic_issues = checker.get_open_issues()

        if open_semantic_issues:
            plan['open_semantic_issues'] = open_semantic_issues
            print(f"Planner aware of {len(open_semantic_issues)} open semantic issues")

        # Adjust plan based on semantic health
        semantic_summary = checker.get_summary()
        low_eq_count = semantic_summary['equivalence_counts'].get('low', 0)
        total_checked = semantic_summary.get('total_files_checked', 0)

        if total_checked > 0:
            low_eq_ratio = low_eq_count / total_checked
            if low_eq_ratio > 0.2:  # If more than 20% of files had low equivalence
                print(f"Warning: {low_eq_ratio:.1%} files had low semantic equivalence. Planner should avoid risky transformations.")

                # In such cases, we could adjust the plan to be more conservative
                # For example, use engines with higher accuracy, add more verification steps, etc.
                for task in plan.get('file_tasks', []):
                    # Add additional verification for risky files
                    if 'validation_cmd' not in task:
                        task['validation_cmd'] = 'echo "Semantic validation recommended for this task"'

        # Check for specific patterns in inconsistent tasks and avoid repeating them
        memory.add_summary_entry(
            "planning_phase",
            f"Planner consulted semantic summary: {low_eq_count}/{total_checked} files with low equivalence"
        )

    except ImportError:
        # If semantic_integrity module is not available, continue without semantic awareness
        print("Warning: Semantic integrity module not available, proceeding without semantic awareness")
        pass
    except Exception as e:
        # If there's an error accessing semantic data, continue anyway
        print(f"Warning: Could not access semantic data: {e}")
        pass

def validate_conversion_plan(plan: Dict) -> List[str]:
    """This function is deprecated. Use the validate_plan function in convert_orchestrator.py instead."""
    print("Warning: validate_conversion_plan in planner.py is deprecated. Use the one in convert_orchestrator.py.")
    return []
