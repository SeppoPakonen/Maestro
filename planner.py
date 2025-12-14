import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from inventory_generator import load_inventory

def generate_task_id():
    """Generate a unique task ID."""
    return f"task_{uuid.uuid4().hex[:8]}"

def create_scaffold_tasks(target_inventory: Dict) -> List[Dict]:
    """Create scaffold tasks to establish project structure."""
    tasks = []
    
    # If target is empty, create basic scaffolding tasks
    if not target_inventory or target_inventory.get('total_count', 0) == 0:
        # Create basic project infrastructure
        scaffold_tasks = [
            {
                "task_id": generate_task_id(),
                "phase": "scaffold",
                "source_files": [],
                "target_files": ["README.md", "package.json", "requirements.txt", ".gitignore"],
                "engine": "claude",
                "prompt_ref": "scaffold_project_setup.txt",
                "acceptance_criteria": "Basic project files created with appropriate content",
                "deliverables": ["README.md", "package.json", "requirements.txt", ".gitignore"],
                "depends_on": [],
                "status": "pending"
            },
            {
                "task_id": generate_task_id(),
                "phase": "scaffold",
                "source_files": [],
                "target_files": ["src/", "tests/", "docs/"],
                "engine": "directory_create",
                "prompt_ref": "scaffold_directory_structure.txt",
                "acceptance_criteria": "Directory structure created according to best practices for target language",
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
        
        # Map languages to appropriate AI engines
        lang_to_engine = {
            'Python': 'codex',
            'JavaScript': 'gpt4',
            'TypeScript': 'gpt4',
            'Java': 'claude',
            'C++': 'claude',
            'C': 'claude',
            'C#': 'gpt4',
            'Go': 'gpt4',
            'Rust': 'claude',
            'Ruby': 'gpt4',
            'PHP': 'gpt4',
            'Swift': 'gpt4',
            'Kotlin': 'gpt4',
            'Scala': 'gpt4',
            'HTML': 'gpt3.5',
            'CSS': 'gpt3.5',
            'JSON': 'gpt3.5',
            'YAML': 'gpt3.5',
            'Markdown': 'gpt3.5',
            'Shell': 'gpt3.5',
            'Configuration': 'gpt3.5',
            'Text': 'gpt3.5',
            'Dockerfile': 'gpt3.5'
        }
        
        engine = lang_to_engine.get(sample_lang, 'gpt3.5')
        
        # Create a task for this group of files
        source_paths = [f['path'] for f in files]
        target_paths = [f['path'] for f in files]  # Same names initially
        
        # Decide on conversion vs copy based on file type
        if sample_lang in ['Image', 'Binary', 'Unknown']:  # Placeholder - will be handled differently
            task_type = "file_copy"
            engine = "file_copy"
            acceptance = "Files copied to target location without modification"
        else:
            task_type = "file_conversion"
            acceptance = "Source files converted appropriately to target technology stack"
        
        task = {
            "task_id": generate_task_id(),
            "phase": "file",
            "source_files": source_paths,
            "target_files": target_paths,
            "engine": engine,
            "prompt_ref": f"convert_files_{ext}.txt",
            "acceptance_criteria": acceptance,
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
            "source_files": [f['path'] for f in source_inventory.get('files', [])],
            "target_files": [f['path'] for f in target_inventory.get('files', []) if f.get('path', '')],
            "engine": "gpt4",
            "prompt_ref": "verify_conversion_coverage.txt",
            "acceptance_criteria": "All source files have been accounted for in target conversion",
            "deliverables": [".maestro/convert/reports/coverage.json"],
            "depends_on": [],
            "status": "pending"
        },
        {
            "task_id": generate_task_id(),
            "phase": "sweep",
            "source_files": [],
            "target_files": [".maestro/convert/reports/final_summary.md"],
            "engine": "gpt4",
            "prompt_ref": "generate_final_report.txt",
            "acceptance_criteria": "Comprehensive report of conversion process and results",
            "deliverables": [".maestro/convert/reports/final_summary.md"],
            "depends_on": [sweep_tasks[0]['task_id']] if 'sweep_tasks' in locals() else [],
            "status": "pending"
        }
    ]
    
    return sweep_tasks

def generate_conversion_plan(source_repo_path: str, target_repo_path: str, plan_output_path: str) -> Dict:
    """Generate a complete conversion plan JSON based on source and target inventories."""
    
    # Load inventories
    source_inventory_path = ".maestro/convert/inventory/source_files.json"
    target_inventory_path = ".maestro/convert/inventory/target_files.json"
    
    source_inventory = load_inventory(source_inventory_path)
    target_inventory = load_inventory(target_inventory_path)
    
    if not source_inventory:
        raise ValueError(f"Source inventory not found at {source_inventory_path}")
    
    # Create the plan
    plan = {
        "version": "1.0",
        "source_inventory": source_inventory_path,
        "target_inventory": target_inventory_path,
        "scaffold_tasks": [],
        "file_tasks": [],
        "final_sweep_tasks": [],
        "metadata": {
            "created_at": datetime.utcnow().isoformat(),
            "source_repo": source_repo_path,
            "target_repo": target_repo_path,
            "ai_model_used": "claude-sonnet"  # This can be configurable
        }
    }
    
    # Create scaffold tasks (these come first)
    plan['scaffold_tasks'] = create_scaffold_tasks(target_inventory)
    
    # Create file conversion tasks (these process the source files)
    plan['file_tasks'] = create_file_conversion_tasks(source_inventory, target_inventory)
    
    # Create final sweep tasks (these verify completion)
    plan['final_sweep_tasks'] = create_sweep_tasks(source_inventory, target_inventory)
    
    # Save the plan
    with open(plan_output_path, 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=2)
    
    return plan

def validate_conversion_plan(plan: Dict) -> List[str]:
    """Validate the conversion plan structure and completeness."""
    errors = []
    
    # Basic structure validation
    required_fields = ["version", "source_inventory", "target_inventory", "scaffold_tasks", "file_tasks", "final_sweep_tasks"]
    for field in required_fields:
        if field not in plan:
            errors.append(f"Missing required field: {field}")
    
    # Validate task IDs are unique
    all_tasks = plan.get("scaffold_tasks", []) + plan.get("file_tasks", []) + plan.get("final_sweep_tasks", [])
    task_ids = [task.get("task_id") for task in all_tasks if "task_id" in task]
    if len(task_ids) != len(set(task_ids)):
        errors.append("Duplicate task IDs found in plan")
    
    # Validate task structure
    required_task_fields = ["task_id", "phase", "source_files", "engine", "prompt_ref", "acceptance_criteria", "deliverables", "depends_on", "status"]
    for i, task in enumerate(all_tasks):
        for field in required_task_fields:
            if field not in task:
                errors.append(f"Task {i} ({task.get('task_id', 'unknown')}) missing required field: {field}")
        
        # Validate phase
        if task.get("phase") not in ["scaffold", "file", "sweep"]:
            errors.append(f"Task {task.get('task_id')} has invalid phase: {task.get('phase')}")
        
        # Validate status
        if task.get("status") not in ["pending", "running", "completed", "failed", "interrupted", "skipped"]:
            errors.append(f"Task {task.get('task_id')} has invalid status: {task.get('status')}")
    
    return errors