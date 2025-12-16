import json
import os
from typing import Dict, List
from inventory_generator import load_inventory

def generate_coverage_report(source_inventory_path: str, target_inventory_path: str, plan_path: str, output_path: str = ".maestro/convert/reports/coverage.json"):
    """Generate a coverage report showing the status of all source files."""
    
    # Load inventories and plan
    source_inventory = load_inventory(source_inventory_path)
    target_inventory = load_inventory(target_inventory_path)
    
    with open(plan_path, 'r', encoding='utf-8') as f:
        plan = json.load(f)
    
    # Initialize coverage report
    coverage_report = {
        "generated_at": "TODO",  # Will be set to current timestamp
        "source_inventory": source_inventory_path,
        "target_inventory": target_inventory_path,
        "plan_used": plan_path,
        "total_source_files": 0,
        "converted_files": [],
        "copied_files": [],
        "skipped_files": [],
        "missing_files": [],
        "coverage_percentage": 0.0,
        "unmapped_count": 0,
        "details": {
            "converted": [],
            "copied": [],
            "skipped": [],
            "missing": []
        }
    }
    
    if not source_inventory:
        print(f"Error: Could not load source inventory from {source_inventory_path}")
        return coverage_report
    
    # Extract source file paths
    source_files = [f['path'] for f in source_inventory.get('files', [])]
    coverage_report["total_source_files"] = len(source_files)
    
    # If no target inventory exists, all files are missing
    if not target_inventory:
        coverage_report["missing_files"] = source_files[:]
        coverage_report["unmapped_count"] = len(source_files)
        coverage_report["coverage_percentage"] = 0.0
        coverage_report["details"]["missing"] = [{"source_path": path, "reason": "Target repository empty"} for path in source_files]
    else:
        # Get target file paths for comparison
        target_files = [f['path'] for f in target_inventory.get('files', [])]
        
        # Analyze the plan to determine how source files were handled
        all_plan_tasks = plan.get('scaffold_tasks', []) + plan.get('file_tasks', []) + plan.get('final_sweep_tasks', [])
        
        # Track which source files were processed by tasks
        processed_source_files = set()
        converted_files = []
        copied_files = []
        skipped_files = []
        
        for task in all_plan_tasks:
            # Determine how this task affects source files
            for source_file in task.get('source_files', []):
                if task['engine'] == 'file_copy':
                    copied_files.append(source_file)
                    processed_source_files.add(source_file)
                elif task['engine'] == 'directory_create':
                    # These don't directly process source files
                    continue
                else:
                    # Regular conversion tasks
                    converted_files.append(source_file)
                    processed_source_files.add(source_file)
        
        # Files in source but not processed are considered missing/unmapped
        missing_files = [f for f in source_files if f not in processed_source_files]
        
        coverage_report["converted_files"] = converted_files
        coverage_report["copied_files"] = copied_files
        coverage_report["skipped_files"] = skipped_files  # This could be populated by tasks that explicitly skip files
        coverage_report["missing_files"] = missing_files
        
        coverage_report["unmapped_count"] = len(missing_files)
        
        # Calculate coverage percentage (accounted-for files / total source files)
        accounted_files = len(processed_source_files)
        coverage_report["coverage_percentage"] = (accounted_files / len(source_files)) * 100 if len(source_files) > 0 else 0.0
        
        # Add detailed breakdown
        coverage_report["details"]["converted"] = [{"source_path": path, "target_path": path} for path in converted_files]
        coverage_report["details"]["copied"] = [{"source_path": path, "target_path": path} for path in copied_files]
        coverage_report["details"]["skipped"] = [{"source_path": path, "reason": "explicitly_skipped"} for path in skipped_files]
        coverage_report["details"]["missing"] = [{"source_path": path, "reason": "not_included_in_plan"} for path in missing_files]
    
    # Add timestamp
    from datetime import datetime
    coverage_report["generated_at"] = datetime.utcnow().isoformat()
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Write the report
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(coverage_report, f, indent=2)
    
    print(f"Coverage report generated at {output_path}")
    print(f"Coverage: {coverage_report['coverage_percentage']:.2f}% ({accounted_files}/{len(source_files)} files)")
    print(f"Unmapped files: {coverage_report['unmapped_count']}")
    
    return coverage_report


def validate_coverage_success(coverage_report: Dict, allowed_unmapped: int = 0) -> bool:
    """Validate if coverage meets success criteria."""
    return coverage_report["unmapped_count"] <= allowed_unmapped


def print_coverage_summary(coverage_report_path: str):
    """Print a human-readable summary of the coverage."""
    if not os.path.exists(coverage_report_path):
        print(f"Coverage report not found at {coverage_report_path}")
        return
    
    with open(coverage_report_path, 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    print("\n=== CONVERSION COVERAGE REPORT ===")
    print(f"Generated at: {report['generated_at']}")
    print(f"Source files: {report['total_source_files']}")
    print(f"Converted files: {len(report['converted_files'])}")
    print(f"Copied files: {len(report['copied_files'])}")
    print(f"Skipped files: {len(report['skipped_files'])}")
    print(f"Missing/unmapped files: {report['unmapped_count']}")
    print(f"Coverage percentage: {report['coverage_percentage']:.2f}%")
    
    if report['missing_files']:
        print("\nUnmapped files:")
        for f in report['missing_files'][:10]:  # Show first 10
            print(f"  - {f}")
        if len(report['missing_files']) > 10:
            print(f"  ... and {len(report['missing_files']) - 10} more")
    
    print("=" * 35)