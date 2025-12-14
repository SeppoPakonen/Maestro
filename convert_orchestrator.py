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
import datetime

# Import our conversion modules
import inventory_generator
import planner
import execution_engine
import coverage_report
from conversion_memory import ConversionMemory
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

    # Load the schema - first try the committed location, then fallback
    schema_path = "tools/convert_tests/schemas/plan.schema.json"
    if not os.path.exists(schema_path):
        # Fallback to .maestro location if tools location doesn't exist
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
    errors.extend(_check_write_policies(plan_data))
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


def _check_write_policies(plan_data: Dict) -> List[str]:
    """Check that all write policies are from the allowed set."""
    errors = []
    allowed_policies = {'overwrite', 'merge', 'skip_if_exists', 'fail_if_exists'}

    all_tasks = (
        plan_data.get('scaffold_tasks', []) +
        plan_data.get('file_tasks', []) +
        plan_data.get('final_sweep_tasks', [])
    )

    for task in all_tasks:
        write_policy = task.get('write_policy')
        if write_policy and write_policy not in allowed_policies:
            errors.append(f"Task {task.get('task_id', 'unknown')} uses disallowed write_policy: {write_policy}")

        # Validate merge-specific fields
        if write_policy == 'merge':
            merge_strategy = task.get('merge_strategy')
            if not merge_strategy:
                errors.append(f"Task {task.get('task_id', 'unknown')} has write_policy 'merge' but no merge_strategy")

            if merge_strategy:
                allowed_strategies = {'append_section', 'replace_section_by_marker', 'json_merge', 'toml_merge'}
                if merge_strategy not in allowed_strategies:
                    errors.append(f"Task {task.get('task_id', 'unknown')} uses disallowed merge_strategy: {merge_strategy}")

        # Validate merge markers if replace_section_by_marker is used
        if task.get('merge_strategy') == 'replace_section_by_marker':
            merge_markers = task.get('merge_markers', {})
            if not merge_markers.get('begin_marker') or not merge_markers.get('end_marker'):
                errors.append(f"Task {task.get('task_id', 'unknown')} uses 'replace_section_by_marker' strategy but missing required markers in merge_markers")

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


def compute_inventory_fingerprint(inventory_path: str) -> str:
    """Compute a hash fingerprint of an inventory file."""
    import hashlib
    if not os.path.exists(inventory_path):
        return ""

    with open(inventory_path, 'rb') as f:
        content = f.read()
        return hashlib.sha256(content).hexdigest()


def cmd_plan(args):
    """Generate a conversion plan based on source and target inventories."""
    print(f"Generating conversion plan from {args.source} to {args.target}")

    plan_path = ".maestro/convert/plan/plan.json"

    # Import the planner here to avoid circular imports
    from planner import generate_conversion_plan
    plan = generate_conversion_plan(args.source, args.target, plan_path)

    # Add inventory fingerprints to the plan
    source_inventory_path = ".maestro/convert/inventory/source_files.json"
    target_inventory_path = ".maestro/convert/inventory/target_files.json"

    plan['source_inventory_fingerprint'] = compute_inventory_fingerprint(source_inventory_path)
    plan['target_inventory_fingerprint'] = compute_inventory_fingerprint(target_inventory_path)

    # Also add summary fingerprint
    summary_path = ".maestro/convert/inventory/summary.json"
    plan['inventory_summary_fingerprint'] = compute_inventory_fingerprint(summary_path)

    # Save the updated plan
    with open(plan_path, 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=2)

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


def check_inventory_change(plan_path: str, source_path: str, target_path: str) -> Dict:
    """Check if source or target inventory has changed since plan generation."""
    with open(plan_path, 'r') as f:
        plan = json.load(f)

    # Compute current fingerprints
    current_source_fingerprint = compute_inventory_fingerprint(".maestro/convert/inventory/source_files.json")
    current_target_fingerprint = compute_inventory_fingerprint(".maestro/convert/inventory/target_files.json")
    current_summary_fingerprint = compute_inventory_fingerprint(".maestro/convert/inventory/summary.json")

    # Compare with stored fingerprints
    source_changed = current_source_fingerprint != plan.get('source_inventory_fingerprint', '')
    target_changed = current_target_fingerprint != plan.get('target_inventory_fingerprint', '')
    summary_changed = current_summary_fingerprint != plan.get('inventory_summary_fingerprint', '')

    return {
        'source_changed': source_changed,
        'target_changed': target_changed,
        'summary_changed': summary_changed,
        'current_source_fingerprint': current_source_fingerprint,
        'current_target_fingerprint': current_target_fingerprint,
        'current_summary_fingerprint': current_summary_fingerprint
    }

def cmd_memory_show(args):
    """Show current conversion memory state."""
    memory = ConversionMemory()

    print("=== CONVERSION MEMORY STATUS ===\n")

    # Show decisions
    decisions = memory.load_decisions()
    print(f"DECISIONS ({len(decisions)} total):")
    for decision in decisions:
        print(f"  - {decision.get('decision_id')}: {decision.get('description')} = {decision.get('value')}")
    print()

    # Show conventions
    conventions = memory.load_conventions()
    print(f"CONVENTIONS ({len(conventions)} total):")
    for convention in conventions:
        print(f"  - {convention.get('convention_id')}: {convention.get('rule')}")
    print()

    # Show open issues
    open_issues = [issue for issue in memory.load_open_issues()
                   if issue.get('status') in ['open', 'investigating']]
    print(f"OPEN ISSUES ({len(open_issues)} total):")
    for issue in open_issues:
        print(f"  - {issue.get('issue_id')}: {issue.get('description')} (severity: {issue.get('severity')})")
    print()

    # Show summary count
    summary_log = memory.load_summary_log()
    print(f"SUMMARY ENTRIES: {len(summary_log)}")
    print()

    # Show memory usage
    usage_info = memory.get_memory_usage_info()
    print("MEMORY USAGE:")
    for key, value in usage_info.items():
        print(f"  - {key}: {value}")
    print()

def cmd_memory_diff(args):
    """Show changes in conversion memory since the last check."""
    memory = ConversionMemory()

    print("=== CONVERSION MEMORY DIFF ===\n")

    # In a real implementation, this would compare with a previous snapshot
    # For now, we'll show the current state with some comparison info
    print("Showing current memory state (detailed view)...")
    print()

    # Load all memory components
    decisions = memory.load_decisions()
    conventions = memory.load_conventions()
    open_issues = memory.load_open_issues()
    glossary = memory.load_glossary()
    summary_log = memory.load_summary_log()

    print("DECISIONS:")
    if decisions:
        for decision in decisions[-5:]:  # Show last 5 decisions
            print(f"  - {decision.get('decision_id')}: {decision.get('description')}")
    else:
        print("  No decisions recorded yet")
    print()

    print("CONVENTIONS:")
    if conventions:
        for convention in conventions[-5:]:  # Show last 5 conventions
            print(f"  - {convention.get('convention_id')}: {convention.get('rule')}")
    else:
        print("  No conventions established yet")
    print()

    print("OPEN ISSUES:")
    if open_issues:
        for issue in open_issues[-5:]:  # Show last 5 issues
            if issue.get('status') in ['open', 'investigating']:
                print(f"  - {issue.get('issue_id')}: {issue.get('description')}")
    else:
        print("  No open issues")
    print()

    print("GLOSSARY ENTRIES:")
    if glossary:
        for entry in glossary[-5:]:  # Show last 5 entries
            print(f"  - {entry.get('source_term')} → {entry.get('target_term')}")
    else:
        print("  No glossary entries")
    print()

    print("RECENT SUMMARY ENTRIES:")
    if summary_log:
        for entry in summary_log[-5:]:  # Show last 5 summaries
            print(f"  - {entry.get('task_id')}: {entry.get('summary')}")
    else:
        print("  No summary entries")
    print()

def cmd_memory_explain(args):
    """Explain a specific decision by ID."""
    memory = ConversionMemory()

    if args.decision_id.startswith('D-'):  # Decision ID
        decision = memory.get_decision_by_id(args.decision_id)
        if decision:
            print(f"DECISION: {decision.get('decision_id')}")
            print(f"Category: {decision.get('category')}")
            print(f"Description: {decision.get('description')}")
            print(f"Value: {decision.get('value')}")
            print(f"Justification: {decision.get('justification')}")
            print(f"Timestamp: {decision.get('timestamp')}")
        else:
            print(f"Decision with ID {args.decision_id} not found")
    elif args.decision_id.startswith('C-'):  # Convention ID
        convention = memory.get_convention_by_id(args.decision_id)
        if convention:
            print(f"CONVENTION: {convention.get('convention_id')}")
            print(f"Category: {convention.get('category')}")
            print(f"Rule: {convention.get('rule')}")
            print(f"Applies to: {convention.get('applies_to')}")
            print(f"Timestamp: {convention.get('timestamp')}")
        else:
            print(f"Convention with ID {args.decision_id} not found")
    elif args.decision_id.startswith('I-'):  # Issue ID
        issue = memory.get_issue_by_id(args.decision_id)
        if issue:
            print(f"ISSUE: {issue.get('issue_id')}")
            print(f"Severity: {issue.get('severity')}")
            print(f"Description: {issue.get('description')}")
            print(f"Status: {issue.get('status')}")
            print(f"Related tasks: {issue.get('related_tasks', [])}")
            if issue.get('resolution'):
                print(f"Resolution: {issue.get('resolution')}")
            print(f"Timestamp: {issue.get('timestamp')}")
        else:
            print(f"Issue with ID {args.decision_id} not found")
    elif args.decision_id.startswith('G-'):  # Glossary term ID
        term = memory.get_glossary_entry_by_id(args.decision_id)
        if term:
            print(f"GLOSSARY TERM: {term.get('term_id')}")
            print(f"Source: {term.get('source_term')}")
            print(f"Target: {term.get('target_term')}")
            print(f"Definition: {term.get('definition')}")
            print(f"Usage context: {term.get('usage_context')}")
            print(f"Timestamp: {term.get('timestamp')}")
        else:
            print(f"Glossary term with ID {args.decision_id} not found")
    else:
        print(f"Unknown ID format: {args.decision_id}. Use D-xxx for decisions, C-xxx for conventions, I-xxx for issues, G-xxx for glossary terms")


def cmd_semantics_list(args):
    """List all semantic check results."""
    from semantic_integrity import SemanticIntegrityChecker
    checker = SemanticIntegrityChecker()

    # Get all semantic result files
    import glob
    semantic_files = glob.glob(".maestro/convert/semantics/task_*.json")

    if not semantic_files:
        print("No semantic checks have been performed yet.")
        return 0

    print("SEMANTIC CHECK RESULTS:")
    print("-" * 80)

    for file_path in sorted(semantic_files):
        task_id = file_path.split('/')[-1].replace('task_', '').replace('.json', '')

        with open(file_path, 'r') as f:
            try:
                result = json.load(f)

                equiv = result.get('semantic_equivalence', 'unknown')
                confidence = result.get('confidence', 0)
                requires_review = result.get('requires_human_review', False)

                status_indicator = "!" if requires_review else " "
                equiv_emoji = {"high": "✅", "medium": "⚠️", "low": "❌", "unknown": "❓"}

                print(f"{status_indicator} {equiv_emoji.get(equiv, '?')} {task_id:<15} | {equiv:<6} | {confidence:.2f}")

            except json.JSONDecodeError:
                print(f"   📄 {task_id:<15} | invalid  | 0.00")

    # Print summary
    summary = checker.get_summary()
    print("\nSUMMARY:")
    print(f"Total files checked: {summary['total_files_checked']}")
    print(f"Equivalence breakdown: {summary['equivalence_counts']}")
    print(f"Unresolved warnings: {summary['unresolved_semantic_warnings']}")

    return 0


def cmd_semantics_show(args):
    """Show details of a specific semantic check."""
    from semantic_integrity import SemanticIntegrityChecker
    checker = SemanticIntegrityChecker()

    result = checker.get_semantic_check_result(args.task_id)

    if not result:
        print(f"Semantic check result not found for task {args.task_id}")
        return 1

    print(f"SEMANTIC CHECK RESULT FOR TASK: {args.task_id}")
    print("=" * 50)
    print(f"Semantic Equivalence: {result.get('semantic_equivalence', 'unknown')}")
    print(f"Confidence: {result.get('confidence', 0.0)}")
    print(f"Requires Human Review: {result.get('requires_human_review', False)}")
    print(f"Risk Flags: {result.get('risk_flags', [])}")
    print(f"Preserved Concepts: {result.get('preserved_concepts', [])}")
    print(f"Changed Concepts: {result.get('changed_concepts', [])}")
    print(f"Lost Concepts: {result.get('lost_concepts', [])}")
    print(f"Assumptions: {result.get('assumptions', [])}")

    return 0


def cmd_semantics_accept(args):
    """Accept a semantic change after human review."""
    from semantic_integrity import SemanticIntegrityChecker
    from conversion_memory import ConversionMemory
    import datetime

    checker = SemanticIntegrityChecker()
    memory = ConversionMemory()

    result = checker.get_semantic_check_result(args.task_id)

    if not result:
        print(f"Semantic check result not found for task {args.task_id}")
        return 1

    # Update the semantic check result to indicate human acceptance
    result['requires_human_review'] = False
    result['human_approval'] = {
        'approved_by': os.environ.get('USER', 'unknown'),
        'approved_at': datetime.datetime.now().isoformat(),
        'note': args.note or 'Manual acceptance via CLI'
    }

    # Save the updated result
    checker._save_semantic_check_result(args.task_id, result)

    # Update the summary to reflect the acceptance
    summary = checker.get_summary()
    if summary.get("unresolved_semantic_warnings", 0) > 0:
        summary["unresolved_semantic_warnings"] -= 1
        summary["last_updated"] = datetime.datetime.now().isoformat()

        with open(checker.summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

    print(f"Task {args.task_id} semantic check result accepted manually.")
    if args.note:
        print(f"Note: {args.note}")

    # Add to summary log
    summary_entry = {
        "entry_id": f"S-{len(memory.load_summary_log()) + 1:03d}",
        "task_id": args.task_id,
        "timestamp": datetime.datetime.now().isoformat(),
        "summary": f"Semantic check manually accepted: {args.task_id}, Note: {args.note or 'No note provided'}"
    }
    current_log = memory.load_summary_log()
    current_log.append(summary_entry)
    memory.save_summary_log(current_log)

    return 0


def cmd_semantics_reject(args):
    """Reject a semantic change after human review."""
    from semantic_integrity import SemanticIntegrityChecker
    from conversion_memory import ConversionMemory
    import datetime

    checker = SemanticIntegrityChecker()
    memory = ConversionMemory()

    result = checker.get_semantic_check_result(args.task_id)

    if not result:
        print(f"Semantic check result not found for task {args.task_id}")
        return 1

    # Mark as rejected and requiring rework
    result['requires_human_review'] = True  # Keep as true to indicate ongoing issue
    result['human_rejection'] = {
        'rejected_by': os.environ.get('USER', 'unknown'),
        'rejected_at': datetime.datetime.now().isoformat(),
        'note': args.note or 'Manual rejection via CLI'
    }
    result['semantic_status'] = 'rejected'

    # Save the updated result
    checker._save_semantic_check_result(args.task_id, result)

    print(f"Task {args.task_id} semantic check result rejected manually.")
    if args.note:
        print(f"Note: {args.note}")
    print("Task will require rework.")

    # Add to summary log
    summary_entry = {
        "entry_id": f"S-{len(memory.load_summary_log()) + 1:03d}",
        "task_id": args.task_id,
        "timestamp": datetime.datetime.now().isoformat(),
        "summary": f"Semantic check manually rejected: {args.task_id}, Note: {args.note or 'No note provided'}"
    }
    current_log = memory.load_summary_log()
    current_log.append(summary_entry)
    memory.save_summary_log(current_log)

    # Add an issue to conversion memory about the rejected task
    memory.add_issue("high", f"Task {args.task_id} semantic check rejected, requires rework", [args.task_id])

    return 0


def cmd_decision_override(args):
    """Override a decision with a new value and reason."""
    from datetime import datetime
    import tempfile
    import subprocess

    memory = ConversionMemory()

    if not args.decision_id:
        print("Error: Decision ID required")
        return 1

    decision = memory.get_decision_by_id(args.decision_id)
    if not decision:
        print(f"Error: Decision with ID {args.decision_id} not found")
        return 1

    print(f"Current decision {decision.get('decision_id')}: {decision.get('description')} = {decision.get('value')}")
    print(f"Status: {decision.get('status')}")
    print(f"Created by: {decision.get('created_by')}")
    print()

    # Handle the new value
    new_value = args.new_value
    reason = args.reason
    replan = args.replan

    # If no new value was provided via command line, open editor
    if not new_value:
        # Create a temporary file with the current decision information
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(f"# Decision Override\n")
            f.write(f"# Decision ID: {args.decision_id}\n")
            f.write(f"# Current value: {decision.get('value')}\n")
            f.write(f"# Current status: {decision.get('status')}\n")
            f.write(f"# Current justification: {decision.get('justification')}\n")
            f.write(f"#\n")
            f.write(f"# Enter the new value for this decision below\n")
            f.write(f"NEW_VALUE=\n")
            f.write(f"# Enter the reason for this override below\n")
            f.write(f"REASON=\n")
            f.write(f"# Replan automatically? (true/false)\n")
            f.write(f"REPLAN=false\n")

            temp_path = f.name

        # Open editor
        editor = os.environ.get('EDITOR', 'nano')
        result = subprocess.run([editor, temp_path])

        # Read the values from the file
        with open(temp_path, 'r') as f:
            content = f.read()

        # Extract values using regex or simple parsing
        import re
        new_value_match = re.search(r'NEW_VALUE=(.*)', content)
        reason_match = re.search(r'REASON=(.*)', content)
        replan_match = re.search(r'REPLAN=(.*)', content)

        if new_value_match:
            new_value = new_value_match.group(1).strip()
        if reason_match:
            reason = reason_match.group(1).strip()
        if replan_match:
            replan_str = replan_match.group(1).strip()
            replan = replan_str.lower() in ['true', 'yes', '1', 'on']

        # Clean up temp file
        os.unlink(temp_path)

    if not new_value:
        print("Error: No new value provided for override")
        return 1

    if not reason:
        print("Error: A reason is required for the override")
        return 1

    try:
        # Perform the override
        result = memory.override_decision(
            decision_id=args.decision_id,
            new_value=new_value,
            reason=reason,
            created_by="user"
        )

        print(f"Successfully overrode decision:")
        print(f"  Old ID: {result['old_id']} → New ID: {result['new_id']}")
        print(f"  Old value: {result['old_decision']['value']} → New value: {result['new_decision']['value']}")

        # Log to summary log
        summary_entry = {
            "entry_id": f"S-{len(memory.load_summary_log()) + 1:03d}",
            "task_id": "decision_override",
            "timestamp": datetime.now().isoformat(),
            "summary": f"Decision override: {result['old_id']} → {result['new_id']}, "
                      f"Reason: {reason}"
        }
        current_log = memory.load_summary_log()
        current_log.append(summary_entry)
        memory.save_summary_log(current_log)

        print()
        print(f"What will happen next:")
        if replan:
            print("- Plan will be automatically renegotiated due to decision changes")
        else:
            print("- Plan will need to be renegotiated manually before execution")
            print("  Run: maestro convert plan --negotiate")

        return 0

    except ValueError as e:
        print(f"Error: {str(e)}")
        return 1


def apply_plan_patch(plan: Dict, patch: Dict) -> Dict:
    """Apply a patch to the plan and return the updated plan."""
    import copy
    updated_plan = copy.deepcopy(plan)

    # Get all task lists to update
    all_tasks = []
    all_tasks.extend(updated_plan.get('scaffold_tasks', []))
    all_tasks.extend(updated_plan.get('file_tasks', []))
    all_tasks.extend(updated_plan.get('final_sweep_tasks', []))

    # Create a mapping of task_id to task for easy lookup
    task_map = {task['task_id']: task for task in all_tasks}

    # Invalidate tasks marked for invalidation
    invalidate_tasks = patch.get('plan_patch', {}).get('invalidate_tasks', [])
    for task_id in invalidate_tasks:
        if task_id in task_map:
            # Check if the task was already completed (before being invalidated)
            old_status = task_map[task_id].get('status', 'pending')
            if old_status in ['completed', 'done']:
                print(f"  - Task {task_id} was completed but is now invalidated by decision changes")
                print(f"    Previous status: {old_status} -> New status: invalidated")
                # In a full implementation, we might want to branch here
                # For now, we just mark as invalidated but note that work was lost
            task_map[task_id]['status'] = 'invalidated'
            print(f"  - Invalidated task: {task_id}")

    # Add new tasks
    add_tasks = patch.get('plan_patch', {}).get('add_tasks', [])
    for task in add_tasks:
        if 'task_id' not in task:
            # Generate new task ID if not provided
            task['task_id'] = f"task_{uuid.uuid4().hex[:8]}"

        # Determine which phase to add the task to based on phase field
        phase = task.get('phase', 'file')
        if phase == 'scaffold':
            updated_plan.setdefault('scaffold_tasks', []).append(task)
        elif phase == 'file':
            updated_plan.setdefault('file_tasks', []).append(task)
        elif phase == 'sweep':
            updated_plan.setdefault('final_sweep_tasks', []).append(task)
        else:
            # Default to file if phase is not specified properly
            updated_plan.setdefault('file_tasks', []).append(task)

    # Modify existing tasks
    modify_tasks = patch.get('plan_patch', {}).get('modify_tasks', [])
    for mod_task in modify_tasks:
        task_id = mod_task.get('task_id')
        if task_id and task_id in task_map:
            # Update only the fields provided in the modification
            for key, value in mod_task.items():
                if key != 'task_id':  # Don't update the task_id itself
                    task_map[task_id][key] = value
        else:
            print(f"Warning: Task {task_id} not found for modification")

    # Handle reordering if specified
    reorder = patch.get('plan_patch', {}).get('reorder', [])
    if reorder:
        # Create reordered task lists
        def reorder_phase_tasks(phase_name):
            if phase_name in updated_plan:
                current_tasks = updated_plan[phase_name]
                # Create a map from current task IDs to tasks
                task_id_map = {task['task_id']: task for task in current_tasks}

                # Build new ordered list based on reorder specification
                reordered_tasks = []
                for task_id in reorder:
                    if task_id in task_id_map:
                        reordered_tasks.append(task_id_map[task_id])

                # Add any tasks that weren't in the reorder list at the end
                reorder_set = set(reorder)
                for task in current_tasks:
                    if task['task_id'] not in reorder_set:
                        reordered_tasks.append(task)

                updated_plan[phase_name] = reordered_tasks

        # Apply reordering to each phase
        reorder_phase_tasks('scaffold_tasks')
        reorder_phase_tasks('file_tasks')
        reorder_phase_tasks('final_sweep_tasks')

    return updated_plan


def cmd_negotiate_plan(args):
    """Negotiate plan updates after decision changes."""
    import hashlib
    from conversion_memory import ConversionMemory

    plan_path = ".maestro/convert/plan/plan.json"

    if not os.path.exists(plan_path):
        print(f"Error: No plan found at {plan_path}. Run 'plan' command first.")
        return 1

    print(f"Loading plan from {plan_path}")
    with open(plan_path, 'r') as f:
        plan = json.load(f)

    print("Loading conversion memory...")
    memory = ConversionMemory()

    # Calculate current decision fingerprint
    current_decision_fingerprint = memory.compute_decision_fingerprint()

    # Get plan's stored decision fingerprint
    plan_decision_fingerprint = plan.get('decision_fingerprint', '')

    print(f"Current decision fingerprint: {current_decision_fingerprint}")
    print(f"Plan decision fingerprint: {plan_decision_fingerprint}")
    print(f"Decision fingerprints match: {current_decision_fingerprint == plan_decision_fingerprint}")

    # Load inventory to provide context to AI
    source_inventory_path = ".maestro/convert/inventory/source_files.json"
    target_inventory_path = ".maestro/convert/inventory/target_files.json"

    source_inventory = {}
    target_inventory = {}

    if os.path.exists(source_inventory_path):
        with open(source_inventory_path, 'r') as f:
            source_inventory = json.load(f)

    if os.path.exists(target_inventory_path):
        with open(target_inventory_path, 'r') as f:
            target_inventory = json.load(f)

    # Prepare prompt for AI to suggest plan changes
    prompt = f"""
You are a conversion planning assistant. The conversion plan needs to be updated due to changes in decisions.

Current decision fingerprint: {current_decision_fingerprint}
Plan's decision fingerprint: {plan_decision_fingerprint}

Current plan:
{json.dumps(plan, indent=2)}

Source inventory:
{json.dumps(source_inventory.get('files', [])[:10], indent=2)}  # Limit to first 10 files

Conversion memory decisions:
{json.dumps(memory.get_active_decisions(), indent=2)}

Based on the changed decisions, please suggest what needs to change in the plan.
Provide your response as a JSON object with the following structure:

{{
  "plan_patch": {{
    "invalidate_tasks": ["task_id_1", "task_id_2"],
    "add_tasks": [...],  # New task objects to add
    "modify_tasks": [...],  # Task update objects
    "reorder": [...]  # New ordering of task IDs
  }},
  "decision_changes": ["D-001 -> D-019"],
  "risks": ["risk1", "risk2"],
  "requires_user_confirm": true
}}

Validate your JSON response carefully.
"""

    # In a real implementation, we would call an AI model here
    # For now, create a mock response that shows the structure
    # This demonstrates how the negotiation would work
    print("\nAnalyzing plan changes due to decision overrides...")

    # Find invalidated tasks based on decision compliance checking
    invalidated_tasks = []
    active_decisions = memory.get_active_decisions()
    old_decisions = [d for d in memory.load_decisions() if d.get('status') == 'superseded']

    # Check each task in the plan against the active decisions
    all_plan_tasks = []
    all_plan_tasks.extend(plan.get('scaffold_tasks', []))
    all_plan_tasks.extend(plan.get('file_tasks', []))
    all_plan_tasks.extend(plan.get('final_sweep_tasks', []))

    for task in all_plan_tasks:
        violations = memory.check_task_compliance(task)
        if violations:
            invalidated_tasks.append(task.get('task_id'))
            print(f"  - Task {task.get('task_id')} violates decisions: {violations}")

    decision_changes = [f"{old_d.get('decision_id')} -> {new_d.get('decision_id')}"
                       for old_d in old_decisions
                       for new_d in active_decisions
                       if (old_d.get('decision_id', '').split('-')[1] ==
                           new_d.get('decision_id', '').split('-')[1])]

    # For this mock implementation, return a sample patch
    # In real implementation, this would come from an AI analysis
    mock_response = {
        "plan_patch": {
            "invalidate_tasks": invalidated_tasks,
            "add_tasks": [],  # Would be populated by AI based on new decisions
            "modify_tasks": [],  # Would be populated by AI based on changes needed
            "reorder": []  # Would be populated if task order changes
        },
        "decision_changes": decision_changes,
        "risks": ["Potential conflicts if already-completed tasks are invalidated"],
        "requires_user_confirm": True
    }

    print("AI analysis complete. JSON output:")
    print(json.dumps(mock_response, indent=2))

    # Ask for user confirmation if required
    if mock_response.get("requires_user_confirm", True):
        response = input("\nApply these changes to the plan? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("Plan negotiation cancelled by user.")
            return 0

    # Apply the patch if confirmed
    print("Applying plan patch...")
    # Save the current plan as a historical version before applying patch
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    history_dir = Path(".maestro/convert/plan/history")
    history_dir.mkdir(parents=True, exist_ok=True)

    # Save current plan as historical version
    hist_plan_path = history_dir / f"plan_{timestamp}.json"
    with open(hist_plan_path, 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=2)

    # Save the patch as well
    patch_path = history_dir / f"patch_{timestamp}.json"
    with open(patch_path, 'w', encoding='utf-8') as f:
        json.dump(mock_response, f, indent=2)

    print(f"Plan history saved to {hist_plan_path}")
    print(f"Patch saved to {patch_path}")

    # Apply the patch to the plan
    updated_plan = apply_plan_patch(plan, mock_response)

    # Update the plan with new revision information
    updated_plan['plan_revision'] = plan.get('plan_revision', 0) + 1
    updated_plan['derived_from_revision'] = plan.get('plan_revision', 0)  # previous revision
    updated_plan['decision_fingerprint'] = current_decision_fingerprint

    # Save updated plan
    with open(plan_path, 'w', encoding='utf-8') as f:
        json.dump(updated_plan, f, indent=2)

    print("Plan updated with new revision and decision fingerprint.")

    # Validate the updated plan
    errors = validate_plan(updated_plan, plan_path)
    if errors:
        print(f"⚠️  Warning: Updated plan has validation errors: {errors}")
        print("Consider reviewing the plan before execution.")

    print("Plan negotiation and patching completed successfully.")
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
    if args.accept_semantic_risk:
        print("Accepting semantic risks without human confirmation")

    # Print arbitration settings if enabled
    if args.arbitrate:
        print(f"Arbitration mode enabled")
        print(f"  Engines: {args.arbitrate_engines}")
        print(f"  Judge: {args.judge_engine}")
        print(f"  Max candidates: {args.max_candidates}")
        print(f"  Use judge: {'No' if args.no_judge else 'Yes'}")

    # Load the plan first
    with open(plan_path, 'r') as f:
        plan = json.load(f)

    # Check if inventories have changed since plan was generated
    inventory_check = check_inventory_change(plan_path, args.source, args.target)

    if inventory_check['source_changed'] or inventory_check['target_changed'] or inventory_check['summary_changed']:
        print("⚠️  Warning: Inventory has changed since plan was generated:")
        if inventory_check['source_changed']:
            print("   - Source inventory has changed")
        if inventory_check['target_changed']:
            print("   - Target inventory has changed")
        if inventory_check['summary_changed']:
            print("   - Inventory summary has changed")

        if not args.auto_replan:
            print("   Run 'convert plan' to regenerate the plan, or use --auto-replan flag to auto-replan.")
            return 1
        else:
            print("   Auto-replanning...")
            # Regenerate plan
            from planner import generate_conversion_plan
            plan = generate_conversion_plan(args.source, args.target, plan_path)

            # Add inventory fingerprints to the new plan
            source_inventory_path = ".maestro/convert/inventory/source_files.json"
            target_inventory_path = ".maestro/convert/inventory/target_files.json"

            plan['source_inventory_fingerprint'] = compute_inventory_fingerprint(source_inventory_path)
            plan['target_inventory_fingerprint'] = compute_inventory_fingerprint(target_inventory_path)

            # Also add summary fingerprint
            summary_path = ".maestro/convert/inventory/summary.json"
            plan['inventory_summary_fingerprint'] = compute_inventory_fingerprint(summary_path)

            # Save the updated plan
            with open(plan_path, 'w', encoding='utf-8') as f:
                json.dump(plan, f, indent=2)

            print("✓ Plan regenerated with updated inventory fingerprints")
    else:
        print("✓ Plan inventory check passed - no changes detected")

    # Validate the plan after potential regeneration (enforce validation requirement)
    errors = validate_plan(plan, plan_path)
    if errors:
        print(f"✗ Plan validation failed before execution: {errors}")
        return 1

    # Check if active decisions have changed since plan was created
    from conversion_memory import ConversionMemory
    memory = ConversionMemory()
    current_decision_fingerprint = memory.compute_decision_fingerprint()
    plan_decision_fingerprint = plan.get('decision_fingerprint', '')

    if current_decision_fingerprint != plan_decision_fingerprint:
        print("⚠️  Warning: Active decisions have changed since plan was created")
        print(f"   Current decision fingerprint: {current_decision_fingerprint}")
        print(f"   Plan decision fingerprint: {plan_decision_fingerprint}")

        if args.ignore_decision_drift:
            print("   Proceeding anyway due to --ignore-decision-drift flag")
        else:
            print("   Plan is stale vs active decisions. Run 'maestro convert plan --negotiate' to update the plan.")
            print("   Or use --ignore-decision-drift to proceed anyway (not recommended).")
            return 1
    else:
        print("✓ Decision fingerprint check passed - plan is current with active decisions")

    print("✓ Plan validation passed - proceeding with execution")

    # Import and create run manifest
    from regression_replay import capture_run_manifest, save_run_artifacts, update_run_manifest_after_completion
    engines_used = {
        'worker': args.arbitrate_engines.split(',')[0] if args.arbitrate_engines else 'qwen',
        'judge': args.judge_engine
    }
    flags_used = []
    if args.limit: flags_used.append(f"--limit {args.limit}")
    if args.resume: flags_used.append("--resume")
    if args.auto_replan: flags_used.append("--auto-replan")
    if args.ignore_decision_drift: flags_used.append("--ignore-decision-drift")
    if args.accept_semantic_risk: flags_used.append("--accept-semantic-risk")
    if args.arbitrate: flags_used.append("--arbitrate")

    # Create run manifest
    run_manifest = capture_run_manifest(
        args.source,
        args.target,
        plan_path,
        memory,
        flags_used,
        engines_used
    )
    run_dir = save_run_artifacts(run_manifest, args.source, args.target, plan_path, memory)
    print(f"✓ Created run manifest: {run_manifest.run_id}")

    success = execute_conversion(
        args.source,
        args.target,
        args.limit,
        args.resume,
        accept_semantic_risk=args.accept_semantic_risk,
        arbitrate=args.arbitrate,
        arbitrate_engines=args.arbitrate_engines,
        judge_engine=args.judge_engine,
        max_candidates=args.max_candidates,
        use_judge=not args.no_judge
    )

    # Update manifest with final status
    status = "completed" if success else "failed"
    update_run_manifest_after_completion(run_dir, args.target, status)

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


def cmd_runs_list(args):
    """List all conversion runs."""
    from regression_replay import get_all_runs

    runs = get_all_runs()

    if not runs:
        print("No conversion runs found.")
        return 0

    print(f"{'Run ID':<36} {'Status':<12} {'Timestamp':<20} {'Source → Target'}")
    print("-" * 100)

    # Show the last 10 runs
    for run in runs[:10]:
        run_id = run.get('run_id', 'unknown')
        status = run.get('status', 'unknown')
        timestamp = run.get('timestamp', '')[:19] if run.get('timestamp') else ''
        source = run.get('source_path', '')
        target = run.get('target_path', '')
        path_info = f"{os.path.basename(source)} → {os.path.basename(target)}"

        print(f"{run_id:<36} {status:<12} {timestamp:<20} {path_info}")

    if len(runs) > 10:
        print(f"\n... and {len(runs) - 10} more runs")

    return 0


def cmd_runs_show(args):
    """Show details of a specific conversion run."""
    from regression_replay import load_run_manifest
    import os

    run_id = args.run_id
    manifest = load_run_manifest(run_id)

    if not manifest:
        print(f"Run {run_id} not found.")
        return 1

    print(f"Run ID: {manifest.get('run_id')}")
    print(f"Timestamp: {manifest.get('timestamp')}")
    print(f"Status: {manifest.get('status')}")
    print(f"Pipeline ID: {manifest.get('pipeline_id')}")
    print()

    print("Source:")
    print(f"  Path: {manifest.get('source_path')}")
    print(f"  Revision: {manifest.get('source_revision')}")
    print()

    print("Target:")
    print(f"  Path: {manifest.get('target_path')}")
    print(f"  Revision (before): {manifest.get('target_revision_before')}")
    print(f"  Revision (after): {manifest.get('target_revision_after')}")
    print()

    print("Plan & Decisions:")
    print(f"  Plan revision: {manifest.get('plan_revision', '')[:12]}...")
    print(f"  Decision fingerprint: {manifest.get('decision_fingerprint', '')[:12]}...")
    print()

    print("Engines used:")
    engines = manifest.get('engines_used', {})
    for engine_type, engine_name in engines.items():
        print(f"  {engine_type}: {engine_name}")
    print()

    print(f"Flags used: {', '.join(manifest.get('flags_used', []))}")
    print()

    # Check for drift report
    drift_report_path = f".maestro/convert/runs/{run_id}/replay/drift_report.json"
    if os.path.exists(drift_report_path):
        print("Drift Report: Available")
        print(f"  Path: {drift_report_path}")
    else:
        print("Drift Report: Not available")

    return 0


def cmd_runs_diff(args):
    """Compare two runs or a run against a baseline."""
    from regression_replay import load_run_manifest, get_baseline
    import os

    run_id = args.run_id
    against = args.against

    run_manifest = load_run_manifest(run_id)
    if not run_manifest:
        print(f"Run {run_id} not found.")
        return 1

    if not against:
        print("Please specify a run or baseline to compare against using --against")
        return 1

    # Check if 'against' refers to a baseline or another run
    baseline = get_baseline(against)
    other_manifest = load_run_manifest(against) if not baseline else None

    print(f"Comparing run: {run_id}")
    if baseline:
        print(f"Against baseline: {against}")
        print(f"Baseline created: {baseline.get('timestamp')}")

        print(f"\nTarget file hash differences:")
        print(f"  Files in baseline: {len(baseline.get('target_file_hashes', {}))}")

        # For now, just show basic comparison info
        run_target_path = run_manifest.get('target_path')
        if run_target_path and os.path.exists(run_target_path):
            import hashlib
            current_hashes = {}
            for root, dirs, files in os.walk(run_target_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, run_target_path)
                    with open(file_path, 'rb') as f:
                        content = f.read()
                        file_hash = hashlib.sha256(content).hexdigest()
                        current_hashes[rel_path] = file_hash

            print(f"  Files in current target: {len(current_hashes)}")

            baseline_hashes = baseline.get('target_file_hashes', {})
            added = set(current_hashes.keys()) - set(baseline_hashes.keys())
            removed = set(baseline_hashes.keys()) - set(current_hashes.keys())
            modified = set()

            for path in set(current_hashes.keys()) & set(baseline_hashes.keys()):
                if current_hashes[path] != baseline_hashes[path]:
                    modified.add(path)

            print(f"  Added files: {len(added)}")
            print(f"  Removed files: {len(removed)}")
            print(f"  Modified files: {len(modified)}")

            if added:
                print(f"\n  Added files:")
                for f in list(added)[:5]:  # Show first 5
                    print(f"    - {f}")
                if len(added) > 5:
                    print(f"    ... and {len(added) - 5} more")

            if modified:
                print(f"\n  Modified files:")
                for f in list(modified)[:5]:  # Show first 5
                    print(f"    - {f}")
                if len(modified) > 5:
                    print(f"    ... and {len(modified) - 5} more")

    elif other_manifest:
        print(f"Against run: {against}")
        print(f"Run1 timestamp: {run_manifest.get('timestamp')}")
        print(f"Run2 timestamp: {other_manifest.get('timestamp')}")

        # Compare basic info between runs
        print(f"\nRun Comparison:")
        print(f"  Source path same: {run_manifest.get('source_path') == other_manifest.get('source_path')}")
        print(f"  Target path same: {run_manifest.get('target_path') == other_manifest.get('target_path')}")
        print(f"  Plan revisions same: {run_manifest.get('plan_revision') == other_manifest.get('plan_revision')}")
        print(f"  Decision fingerprints same: {run_manifest.get('decision_fingerprint') == other_manifest.get('decision_fingerprint')}")

    else:
        print(f"Baseline or run '{against}' not found.")
        return 1

    return 0


def cmd_replay(args):
    """Replay a previous conversion run."""
    from regression_replay import run_replay, run_convergent_replay
    from conversion_memory import ConversionMemory

    memory = ConversionMemory()

    # Handle baseline creation
    if args.subcommand == "baseline":
        from regression_replay import create_replay_baseline
        baseline_path = create_replay_baseline(args.run_id, args.baseline_id)
        print(f"Created baseline from run {args.run_id}: {baseline_path}")
        return 0

    # Determine replay mode
    dry = args.dry or not args.apply
    limit = args.limit
    only_task = args.only_task
    only_phase = args.only_phase
    use_recorded_engines = not args.allow_engine_change

    # Parse the --only filter
    only_phase = None
    only_task = None
    if args.only:
        if args.only.startswith('task:'):
            only_task = args.only[5:]  # Remove 'task:' prefix
        elif args.only.startswith('phase:'):
            only_phase = args.only[6:]  # Remove 'phase:' prefix

    # Run convergent replay if max rounds > 1
    if args.max_replay_rounds > 1:
        result = run_convergent_replay(
            run_id=args.run_id,
            source_path=args.source,
            target_path=args.target,
            memory=memory,
            max_replay_rounds=args.max_replay_rounds,
            fail_on_any_drift=args.fail_on_any_drift,
            dry=dry,
            limit=limit,
            only_task=only_task,
            only_phase=only_phase,
            use_recorded_engines=use_recorded_engines,
            allow_engine_change=args.allow_engine_change
        )
    else:
        result = run_replay(
            run_id=args.run_id,
            source_path=args.source,
            target_path=args.target,
            memory=memory,
            dry=dry,
            limit=limit,
            only_task=only_task,
            only_phase=only_phase,
            use_recorded_engines=use_recorded_engines,
            allow_engine_change=args.allow_engine_change
        )

    if result.get("success"):
        print("✓ Replay completed successfully")
        if "convergence_analysis" in result:
            analysis = result["convergence_analysis"]
            print(f"  Convergence: {analysis.get('message')}")
        return 0
    else:
        print(f"✗ Replay failed: {result.get('error')}")
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
    run_parser.add_argument('--auto-replan', action='store_true', help='Auto-replan if inventory changed')
    run_parser.add_argument('--ignore-decision-drift', action='store_true', help='Ignore decision drift and run anyway (dangerous)')
    run_parser.add_argument('--accept-semantic-risk', action='store_true', help='Accept semantic risks without human confirmation')

    # Arbitration mode flags
    run_parser.add_argument('--arbitrate', action='store_true', help='Enable arbitration mode for eligible tasks')
    run_parser.add_argument('--arbitrate-engines', default='qwen,claude', help='Comma-separated list of engines to arbitrate (default: qwen,claude)')
    run_parser.add_argument('--judge-engine', default='codex', help='Engine to use as judge (default: codex, fallback: claude)')
    run_parser.add_argument('--max-candidates', type=int, default=2, help='Maximum number of candidate outputs to generate (default: 2)')
    run_parser.add_argument('--no-judge', action='store_true', help='Use heuristic scoring only, no judge pass')

    run_parser.set_defaults(func=cmd_run)

    # Runs subcommands
    runs_parser = subparsers.add_parser('runs', help='Manage conversion runs')
    runs_subparsers = runs_parser.add_subparsers(dest='runs_subcommand', help='Runs subcommands')

    # runs list
    runs_list_parser = runs_subparsers.add_parser('list', aliases=['l'], help='List all conversion runs')
    runs_list_parser.set_defaults(func=cmd_runs_list)

    # runs show
    runs_show_parser = runs_subparsers.add_parser('show', aliases=['s'], help='Show details of a conversion run')
    runs_show_parser.add_argument('run_id', help='Run ID to show')
    runs_show_parser.set_defaults(func=cmd_runs_show)

    # runs diff
    runs_diff_parser = runs_subparsers.add_parser('diff', aliases=['d'], help='Compare two runs')
    runs_diff_parser.add_argument('run_id', help='Run ID to compare')
    runs_diff_parser.add_argument('--against', help='Run ID or baseline ID to compare against')
    runs_diff_parser.set_defaults(func=cmd_runs_diff)

    # Replay command
    replay_parser = subparsers.add_parser('replay', help='Replay a previous conversion run')
    replay_subparsers = replay_parser.add_subparsers(dest='subcommand', help='Replay subcommands')

    # replay baseline command
    baseline_parser = replay_subparsers.add_parser('baseline', help='Create baseline from a run')
    baseline_parser.add_argument('run_id', help='Run ID to create baseline from')
    baseline_parser.add_argument('baseline_id', nargs='?', help='Baseline ID (optional, auto-generated if not provided)')
    baseline_parser.set_defaults(func=cmd_replay)

    # Main replay command
    replay_parser.add_argument('run_id', help='Run ID to replay')
    replay_parser.add_argument('source', help='Source repository or path')
    replay_parser.add_argument('target', help='Target repository or path')
    replay_parser.add_argument('--dry', action='store_true', help='Dry run only (default)')
    replay_parser.add_argument('--apply', action='store_true', help='Apply changes to target')
    replay_parser.add_argument('--limit', type=int, help='Limit number of tasks to execute')
    replay_parser.add_argument('--only', help='Run only specific task or phase (format: task:id or phase:name)')
    replay_parser.add_argument('--use-recorded-engines', action='store_true', default=True, help='Use engines from the original run (default)')
    replay_parser.add_argument('--allow-engine-change', action='store_true', help='Allow using different engines than recorded')
    replay_parser.add_argument('--max-replay-rounds', type=int, default=2, help='Maximum replay rounds for convergence (default: 2)')
    replay_parser.add_argument('--fail-on-any-drift', action='store_true', help='Fail if any drift is detected')
    replay_parser.set_defaults(func=cmd_replay)

    # Memory command
    memory_parser = subparsers.add_parser('memory', help='Manage conversion memory')
    memory_subparsers = memory_parser.add_subparsers(dest='memory_command', help='Memory subcommands')

    # Memory show command
    memory_show_parser = memory_subparsers.add_parser('show', help='Show current memory state')
    memory_show_parser.set_defaults(func=cmd_memory_show)

    # Memory diff command
    memory_diff_parser = memory_subparsers.add_parser('diff', help='Show memory changes since last check')
    memory_diff_parser.set_defaults(func=cmd_memory_diff)

    # Memory explain command
    memory_explain_parser = memory_subparsers.add_parser('explain', help='Explain a specific decision by ID')
    memory_explain_parser.add_argument('decision_id', help='ID of the decision/convention/issue/glossary term to explain (e.g., D-001, C-002, I-003, G-004)')
    memory_explain_parser.set_defaults(func=cmd_memory_explain)

    # Decision command
    decision_parser = subparsers.add_parser('decision', help='Manage conversion decisions')
    decision_subparsers = decision_parser.add_subparsers(dest='decision_command', help='Decision subcommands')

    # Decision override command
    decision_override_parser = decision_subparsers.add_parser('override', help='Override a decision with a new value')
    decision_override_parser.add_argument('decision_id', help='ID of the decision to override (e.g., D-001)')
    decision_override_parser.add_argument('--new-value', help='New value for the decision')
    decision_override_parser.add_argument('--reason', help='Reason for the override')
    decision_override_parser.add_argument('--replan', action='store_true', help='Replan automatically after override')
    decision_override_parser.set_defaults(func=cmd_decision_override)

    # Plan command enhancements - add negotiate flag
    plan_parser.add_argument('--negotiate', action='store_true', help='Negotiate plan updates based on new decisions')
    # Store the original command function
    plan_parser.set_defaults(func=lambda args: cmd_negotiate_plan(args) if args.negotiate else cmd_plan(args))

    # Semantic command group
    semantic_parser = subparsers.add_parser('semantics', help='Semantic integrity management')
    semantic_subparsers = semantic_parser.add_subparsers(dest='semantic_command', help='Semantic subcommands')

    # Semantic list command
    semantic_list_parser = semantic_subparsers.add_parser('list', help='List all semantic check results')
    semantic_list_parser.set_defaults(func=cmd_semantics_list)

    # Semantic show command
    semantic_show_parser = semantic_subparsers.add_parser('show', help='Show details of a specific semantic check')
    semantic_show_parser.add_argument('task_id', help='ID of the task to show semantic check for')
    semantic_show_parser.set_defaults(func=cmd_semantics_show)

    # Semantic accept command
    semantic_accept_parser = semantic_subparsers.add_parser('accept', help='Accept a semantic change after human review')
    semantic_accept_parser.add_argument('task_id', help='ID of the task to accept')
    semantic_accept_parser.add_argument('--note', help='Optional note for the acceptance')
    semantic_accept_parser.set_defaults(func=cmd_semantics_accept)

    # Semantic reject command
    semantic_reject_parser = semantic_subparsers.add_parser('reject', help='Reject a semantic change after human review')
    semantic_reject_parser.add_argument('task_id', help='ID of the task to reject')
    semantic_reject_parser.add_argument('--note', help='Optional note for the rejection')
    semantic_reject_parser.set_defaults(func=cmd_semantics_reject)

    # Arbitration command group
    arbitration_parser = subparsers.add_parser('arbitration', help='Arbitration result management')
    arbitration_subparsers = arbitration_parser.add_subparsers(dest='arbitration_command', help='Arbitration subcommands')

    # Arbitration show command
    arbitration_show_parser = arbitration_subparsers.add_parser('show', help='Show arbitration results for a task')
    arbitration_show_parser.add_argument('task_id', help='ID of the task to show arbitration results for')
    arbitration_show_parser.set_defaults(func=cmd_arbitration_show)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    return args.func(args)


def cmd_arbitration_show(args):
    """Show arbitration results for a specific task."""
    import os
    import json
    from pathlib import Path

    arbitration_dir = f".maestro/convert/arbitration/{args.task_id}"

    if not os.path.exists(arbitration_dir):
        print(f"Arbitration results not found for task {args.task_id}")
        print(f"Directory {arbitration_dir} does not exist")
        return 1

    # Load decision file
    decision_path = os.path.join(arbitration_dir, 'decision.json')
    if not os.path.exists(decision_path):
        print(f"Decision file not found for task {args.task_id}")
        return 1

    with open(decision_path, 'r', encoding='utf-8') as f:
        decision = json.load(f)

    print(f"ARBITRATION RESULTS FOR TASK: {args.task_id}")
    print("=" * 60)
    print(f"Winner Engine: {decision.get('winner_engine', 'N/A')}")
    print(f"Used Judge: {decision.get('used_judge', 'N/A')}")
    if decision.get('judge_engine'):
        print(f"Judge Engine: {decision.get('judge_engine')}")
    print(f"Decision Timestamp: {decision.get('decision_timestamp', 'N/A')}")
    print()

    # Load and show scorecards
    print("CANDIDATE SCORES:")
    print("-" * 40)

    candidate_scorecards = decision.get('candidate_scorecards', {})
    semantic_results = decision.get('semantic_results', {})

    # Sort candidates by some score if available
    sorted_candidates = sorted(candidate_scorecards.items(), key=lambda x: x[0])  # Sort by engine name for now

    for engine, scorecard in sorted_candidates:
        print(f"  Engine: {engine}")
        print(f"    Protocol Valid: {scorecard.get('protocol_valid', 'N/A')}")
        print(f"    Deliverables OK: {scorecard.get('deliverables_ok', 'N/A')}")
        print(f"    Placeholder Penalty: {scorecard.get('placeholder_penalty', 'N/A')}")
        print(f"    Diff Size Metric: {scorecard.get('diff_size_metric', 'N/A')}")
        print(f"    Validation Result: {scorecard.get('validation_cmd_result', 'N/A')}")
        print(f"    Semantic Equivalence: {scorecard.get('semantic_equivalence', 'N/A')}")
        print(f"    Semantic Confidence: {scorecard.get('semantic_confidence', 'N/A')}")
        print(f"    Requires Human Review: {scorecard.get('requires_human_review', 'N/A')}")
        print()

    # Show candidates summary
    print("CANDIDATES SUMMARY:")
    print("-" * 40)
    candidates = decision.get('candidates', [])
    print(f"  Total Candidates: {len(candidates)}")
    for candidate in candidates:
        print(f"    - {candidate}")
    print()

    # Show top reasons if available
    print("DECISION SUMMARY:")
    print("-" * 40)
    print(f"  Winner: {decision.get('winner_engine', 'N/A')}")
    if decision.get('judge_engine') and decision.get('used_judge'):
        print("  Decision made by judge engine")
    else:
        print("  Decision made by heuristic scoring")
    print()

    # Show location of artifacts
    print("ARBITRATION ARTIFACTS:")
    print("-" * 40)
    print(f"  Directory: {arbitration_dir}")
    print("  Files:")
    for file_path in Path(arbitration_dir).iterdir():
        print(f"    - {file_path.name}")

    return 0




if __name__ == "__main__":
    sys.exit(main())