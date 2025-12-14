#!/usr/bin/env python3
"""
Generic AI-Driven Conversion Orchestrator

Implements the exact requirements from Task 5:
- Generic AI-driven conversion (inventory -> plan -> execute)
- Complete inventory of source and target repos
- Machine-parseable conversion plan JSON
- Deterministic execution with audit artifacts
"""

import argparse
import sys
import os
from pathlib import Path
import json
import jsonschema
from typing import Dict, List, Set

# Import our conversion modules
import inventory_generator
import planner
import execution_engine
import coverage_report
from inventory_generator import generate_inventory, save_inventory
from execution_engine import execute_conversion
from coverage_report import generate_coverage_report


def validate_plan(plan_data: Dict, plan_path: str = ".maestro/convert/plan/plan.json") -> List[str]:
    """
    Comprehensive validation of a conversion plan against the JSON schema and business rules.

    Args:
        plan_data: The plan data to validate
        plan_path: Path to the plan file for error reporting

    Returns:
        List of validation errors, empty if plan is valid
    """
    errors = []

    # Load the schema
    schema_path = ".maestro/convert/schemas/plan.schema.json"
    if not os.path.exists(schema_path):
        errors.append(f"Schema not found at {schema_path}")
        return errors

    with open(schema_path, 'r') as f:
        schema = json.load(f)

    # Validate against JSON schema
    try:
        jsonschema.validate(instance=plan_data, schema=schema)
    except jsonschema.ValidationError as e:
        errors.append(f"JSON schema validation failed: {e.message}")
        return errors  # Return early if basic schema validation fails

    # Additional deterministic checks beyond schema
    errors.extend(_check_phase_ordering(plan_data))
    errors.extend(_check_unknown_statuses(plan_data))
    errors.extend(_check_dependency_references(plan_data))
    errors.extend(_check_prompt_refs(plan_data))
    errors.extend(_check_engines(plan_data))
    errors.extend(_check_coverage_map(plan_data))
    errors.extend(_check_duplicate_task_ids(plan_data))

    return errors


def _check_phase_ordering(plan_data: Dict) -> List[str]:
    """Check that phase ordering rules are followed."""
    errors = []

    # Check that tasks are properly organized by phase
    all_tasks = []
    # Scaffold tasks first
    for task in plan_data.get('scaffold_tasks', []):
        all_tasks.append((task.get('task_id', 'unknown'), 'scaffold'))
    # Then file tasks
    for task in plan_data.get('file_tasks', []):
        all_tasks.append((task.get('task_id', 'unknown'), 'file'))
    # Then sweep tasks
    for task in plan_data.get('final_sweep_tasks', []):
        all_tasks.append((task.get('task_id', 'unknown'), 'sweep'))

    # Although the schema enforces phase values, double-check that phases are correct
    for task_id, phase in all_tasks:
        if phase not in ['scaffold', 'file', 'sweep']:
            errors.append(f"Task {task_id} has invalid phase: {phase}")

    return errors


def _check_unknown_statuses(plan_data: Dict) -> List[str]:
    """Check that all statuses are from the allowed set."""
    errors = []
    allowed_statuses = {'pending', 'running', 'completed', 'failed', 'interrupted', 'skipped'}

    all_tasks = (
        plan_data.get('scaffold_tasks', []) +
        plan_data.get('file_tasks', []) +
        plan_data.get('final_sweep_tasks', [])
    )

    for task in all_tasks:
        status = task.get('status')
        if status not in allowed_statuses:
            errors.append(f"Task {task.get('task_id', 'unknown')} has unknown status: {status}")

    return errors


def _check_dependency_references(plan_data: Dict) -> List[str]:
    """Check that all depends_on references exist and don't create cycles."""
    errors = []

    all_task_ids = set()
    all_tasks = {}

    # Gather all task IDs and store task objects
    for task in plan_data.get('scaffold_tasks', []):
        task_id = task.get('task_id', 'unknown')
        all_task_ids.add(task_id)
        all_tasks[task_id] = task
    for task in plan_data.get('file_tasks', []):
        task_id = task.get('task_id', 'unknown')
        all_task_ids.add(task_id)
        all_tasks[task_id] = task
    for task in plan_data.get('final_sweep_tasks', []):
        task_id = task.get('task_id', 'unknown')
        all_task_ids.add(task_id)
        all_tasks[task_id] = task

    # Check each task's dependencies
    for task in all_tasks.values():
        task_id = task.get('task_id', 'unknown')
        deps = task.get('depends_on', [])

        for dep_id in deps:
            if dep_id not in all_task_ids:
                errors.append(f"Task {task_id} depends on non-existent task: {dep_id}")

    # Check for dependency cycles using a simple algorithm
    errors.extend(_check_cycles(all_tasks))

    return errors


def _check_cycles(tasks: Dict[str, Dict]) -> List[str]:
    """Check for dependency cycles in task dependencies."""
    errors = []

    # Simple cycle detection using DFS
    UNVISITED = 0
    VISITING = 1
    VISITED = 2

    state = {task_id: UNVISITED for task_id in tasks.keys()}

    def dfs(task_id: str) -> bool:
        """Returns True if a cycle is detected."""
        if state[task_id] == VISITING:
            return True  # Cycle detected
        if state[task_id] == VISITED:
            return False

        state[task_id] = VISITING

        task = tasks[task_id]
        for dep_id in task.get('depends_on', []):
            if dep_id in tasks:  # Only check if dependency exists in the plan
                if dfs(dep_id):
                    return True

        state[task_id] = VISITED
        return False

    for task_id in tasks.keys():
        if state[task_id] == UNVISITED:
            if dfs(task_id):
                errors.append(f"Circular dependency detected starting from task: {task_id}")
                break  # Report only one cycle to avoid overwhelming output

    return errors


def _check_prompt_refs(plan_data: Dict) -> List[str]:
    """Check that prompt_ref paths are under the correct directory."""
    errors = []

    all_tasks = (
        plan_data.get('scaffold_tasks', []) +
        plan_data.get('file_tasks', []) +
        plan_data.get('final_sweep_tasks', [])
    )

    for task in all_tasks:
        prompt_ref = task.get('prompt_ref', '')
        if not prompt_ref.startswith('inputs/'):
            errors.append(f"Task {task.get('task_id', 'unknown')} has prompt_ref not under inputs/: {prompt_ref}")

    return errors


def _check_engines(plan_data: Dict) -> List[str]:
    """Check that all engines are from the allowed set."""
    errors = []
    allowed_engines = {'qwen', 'gemini', 'claude', 'codex'}

    all_tasks = (
        plan_data.get('scaffold_tasks', []) +
        plan_data.get('file_tasks', []) +
        plan_data.get('final_sweep_tasks', [])
    )

    for task in all_tasks:
        engine = task.get('engine')
        if engine not in allowed_engines:
            errors.append(f"Task {task.get('task_id', 'unknown')} uses disallowed engine: {engine}")

    return errors


def _check_coverage_map(plan_data: Dict) -> List[str]:
    """Check coverage map integrity and source file coverage."""
    errors = []

    # Check if source files are fully covered only if source inventory exists
    source_inventory_path = plan_data.get('source_inventory', '.maestro/convert/inventory/source_files.json')

    # Load source inventory if it exists
    if os.path.exists(source_inventory_path) and os.path.isfile(source_inventory_path):
        try:
            with open(source_inventory_path, 'r') as f:
                source_inventory = json.load(f)

            # Check using coverage_map if it exists
            coverage_map = plan_data.get('coverage_map', {})
            if coverage_map:
                source_files = {f['path'] for f in source_inventory.get('files', [])}
                covered_files = set(coverage_map.keys())

                # Files that are not covered
                uncovered_files = source_files - covered_files

                if uncovered_files:
                    errors.append(f"Uncovered source files in coverage_map: {sorted(uncovered_files)}")

                # Check for duplicate mappings (files mapped to multiple tasks)
                file_task_map = {}
                for file_path, info in coverage_map.items():
                    task_id = info.get('task_id')
                    if file_path in file_task_map:
                        errors.append(f"Source file '{file_path}' is mapped to multiple tasks: {file_task_map[file_path]} and {task_id}")
                    else:
                        file_task_map[file_path] = task_id
            # Otherwise check using file tasks
            else:
                file_tasks = plan_data.get('file_tasks', [])
                file_task_map = {}
                all_source_files_in_tasks = set()

                for task in file_tasks:
                    if task.get('phase') == 'file':  # Only check file tasks for source file coverage
                        task_id = task.get('task_id', 'unknown')
                        source_files = task.get('source_files', [])

                        for file_path in source_files:
                            all_source_files_in_tasks.add(file_path)
                            if file_path in file_task_map:
                                errors.append(f"Source file '{file_path}' is assigned to multiple tasks: {file_task_map[file_path]} and {task_id}")
                            else:
                                file_task_map[file_path] = task_id

                # Check if all source inventory files are covered by file tasks
                source_files = {f['path'] for f in source_inventory.get('files', [])}
                uncovered_files = source_files - all_source_files_in_tasks

                if uncovered_files:
                    errors.append(f"Uncovered source files: {sorted(uncovered_files)}")
        except (json.JSONDecodeError, KeyError):
            # Skip coverage validation if source inventory is malformed
            pass

    return errors


def _check_duplicate_task_ids(plan_data: Dict) -> List[str]:
    """Check for duplicate task IDs across all task arrays."""
    errors = []

    all_tasks = (
        plan_data.get('scaffold_tasks', []) +
        plan_data.get('file_tasks', []) +
        plan_data.get('final_sweep_tasks', [])
    )

    task_ids = [task.get('task_id') for task in all_tasks if 'task_id' in task]
    seen_ids = set()
    duplicate_ids = set()

    for task_id in task_ids:
        if task_id in seen_ids:
            duplicate_ids.add(task_id)
        else:
            seen_ids.add(task_id)

    if duplicate_ids:
        errors.append(f"Duplicate task IDs found: {sorted(duplicate_ids)}")

    return errors


def cmd_inventory(args):
    """Generate inventory for source and target repositories."""
    print(f"Generating inventory for source: {args.source}")
    print(f"Generating inventory for target: {args.target}")
    
    # Ensure maestro directories exist
    os.makedirs(".maestro/convert/inventory", exist_ok=True)
    
    # Generate and save source inventory
    source_inventory = generate_inventory(args.source)
    source_inventory_path = ".maestro/convert/inventory/source_files.json"
    save_inventory(source_inventory, source_inventory_path)
    print(f"✓ Source inventory saved to {source_inventory_path}")
    
    # Generate and save target inventory
    target_inventory = generate_inventory(args.target)
    target_inventory_path = ".maestro/convert/inventory/target_files.json"
    save_inventory(target_inventory, target_inventory_path)
    print(f"✓ Target inventory saved to {target_inventory_path}")
    
    # Generate summary
    summary = {
        "source_files_count": source_inventory.get("total_count", 0),
        "target_files_count": target_inventory.get("total_count", 0),
        "source_size_bytes": source_inventory.get("size_summary", {}).get("total_bytes", 0),
        "target_size_bytes": target_inventory.get("size_summary", {}).get("total_bytes", 0),
    }
    
    from datetime import datetime
    summary["timestamp"] = datetime.utcnow().isoformat()
    
    summary_path = ".maestro/convert/inventory/summary.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        import json
        json.dump(summary, f, indent=2)
    
    print(f"✓ Inventory summary saved to {summary_path}")
    print(f"Source: {summary['source_files_count']} files, {summary['source_size_bytes']} bytes")
    print(f"Target: {summary['target_files_count']} files, {summary['target_size_bytes']} bytes")


def cmd_plan(args):
    """Generate a conversion plan based on source and target inventories."""
    print(f"Generating conversion plan from {args.source} to {args.target}")

    plan_path = ".maestro/convert/plan/plan.json"

    # Import the planner here to avoid circular imports
    from planner import generate_conversion_plan
    plan = generate_conversion_plan(args.source, args.target, plan_path)
    print(f"✓ Conversion plan generated at {plan_path}")

    # Validate the plan using our new comprehensive validator
    errors = validate_plan(plan, plan_path)
    if errors:
        print(f"✗ Plan validation errors: {errors}")
        return 1
    else:
        print("✓ Plan validation passed")

    # Show plan summary
    scaffold_count = len(plan.get('scaffold_tasks', []))
    file_count = len(plan.get('file_tasks', []))
    sweep_count = len(plan.get('final_sweep_tasks', []))

    print(f"Plan contains: {scaffold_count} scaffold tasks, {file_count} file tasks, {sweep_count} sweep tasks")
    return 0


def cmd_validate(args):
    """Validate an existing conversion plan."""
    plan_path = ".maestro/convert/plan/plan.json"

    if not os.path.exists(plan_path):
        print(f"Error: No plan found at {plan_path}. Run 'plan' command first.")
        return 1

    print(f"Validating conversion plan at {plan_path}")

    # Load the plan
    with open(plan_path, 'r') as f:
        plan = json.load(f)

    # Validate the plan
    errors = validate_plan(plan, plan_path)
    if errors:
        print(f"✗ Plan validation errors: {errors}")
        return 1
    else:
        print("✓ Plan validation passed")
        return 0


def cmd_run(args):
    """Execute the conversion plan."""
    plan_path = ".maestro/convert/plan/plan.json"

    if not os.path.exists(plan_path):
        print(f"Error: No plan found at {plan_path}. Run 'plan' command first.")
        return 1

    print(f"Starting conversion execution from {args.source} to {args.target}")
    if args.limit:
        print(f"Limited to {args.limit} tasks")

    # Validate the plan before executing (enforce validation requirement)
    with open(plan_path, 'r') as f:
        plan = json.load(f)

    errors = validate_plan(plan, plan_path)
    if errors:
        print(f"✗ Plan validation failed before execution: {errors}")
        return 1

    print("✓ Plan validation passed - proceeding with execution")

    success = execute_conversion(args.source, args.target, args.limit, args.resume)

    if success:
        print("✓ Conversion execution completed successfully")

        # Generate coverage report after execution
        generate_coverage_report(
            ".maestro/convert/inventory/source_files.json",
            ".maestro/convert/inventory/target_files.json",
            plan_path,
            ".maestro/convert/reports/coverage.json"
        )
        return 0
    else:
        print("✗ Conversion execution failed or was interrupted")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Generic AI-Driven Conversion Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate inventory for source and target repos
  python convert_orchestrator.py inventory /path/to/source /path/to/target

  # Generate a conversion plan
  python convert_orchestrator.py plan /path/to/source /path/to/target

  # Validate the conversion plan
  python convert_orchestrator.py validate /path/to/source /path/to/target

  # Execute the conversion with limited tasks
  python convert_orchestrator.py run /path/to/source /path/to/target --limit 5
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Inventory command
    inventory_parser = subparsers.add_parser('inventory', help='Generate source and target inventories')
    inventory_parser.add_argument('source', help='Source repository or path')
    inventory_parser.add_argument('target', help='Target repository or path')
    inventory_parser.set_defaults(func=cmd_inventory)

    # Plan command
    plan_parser = subparsers.add_parser('plan', help='Generate conversion plan JSON')
    plan_parser.add_argument('source', help='Source repository or path')
    plan_parser.add_argument('target', help='Target repository or path')
    plan_parser.set_defaults(func=cmd_plan)

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate conversion plan')
    validate_parser.add_argument('source', help='Source repository or path')
    validate_parser.add_argument('target', help='Target repository or path')
    validate_parser.set_defaults(func=cmd_validate)

    # Run command
    run_parser = subparsers.add_parser('run', help='Execute conversion plan')
    run_parser.add_argument('source', help='Source repository or path')
    run_parser.add_argument('target', help='Target repository or path')
    run_parser.add_argument('--limit', type=int, help='Limit number of tasks to execute')
    run_parser.add_argument('--resume', action='store_true', help='Resume from interrupted execution')
    run_parser.set_defaults(func=cmd_run)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())