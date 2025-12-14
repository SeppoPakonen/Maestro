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

# Import our conversion modules
import inventory_generator
import planner
import execution_engine
import coverage_report
from inventory_generator import generate_inventory, save_inventory
from planner import generate_conversion_plan, validate_conversion_plan
from execution_engine import execute_conversion
from coverage_report import generate_coverage_report


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
    plan = generate_conversion_plan(args.source, args.target, plan_path)
    print(f"✓ Conversion plan generated at {plan_path}")

    # Validate the plan
    errors = validate_conversion_plan(plan)
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


def cmd_run(args):
    """Execute the conversion plan."""
    plan_path = ".maestro/convert/plan/plan.json"
    
    if not os.path.exists(plan_path):
        print(f"Error: No plan found at {plan_path}. Run 'plan' command first.")
        return 1

    print(f"Starting conversion execution from {args.source} to {args.target}")
    if args.limit:
        print(f"Limited to {args.limit} tasks")
    
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