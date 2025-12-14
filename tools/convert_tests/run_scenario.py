#!/usr/bin/env python3
"""
Maestro Convert Test Harness - Dual-Repo Conversion Runner

This script provides a standardized way to run Maestro's convert functionality
with two separate repos (source and target) for testing purposes.
"""

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Run Maestro convert tests in dual-repo mode")
    parser.add_argument("--scenario", help="Name of scenario to run")
    parser.add_argument("--list", action="store_true", help="List all available scenarios")
    parser.add_argument("--keep-target", action="store_true", help="Don't delete target repo between runs")
    parser.add_argument("--force-clean", action="store_true", help="Wipe target repo and rerun")
    parser.add_argument("--verbose", action="store_true", help="Show verbose output")
    parser.add_argument("--no-ai", action="store_true", help="Dry mode; runs inventory + validates wiring")
    parser.add_argument("--interrupt-after", type=int, help="Send SIGINT after N seconds")
    parser.add_argument("--update-golden", action="store_true", help="Update golden files instead of checking them")
    
    return parser.parse_args()


def list_scenarios():
    """List all available scenarios in the scenarios directory."""
    scenarios_dir = Path("tools/convert_tests/scenarios")
    if scenarios_dir.exists():
        for item in scenarios_dir.iterdir():
            if item.is_dir():
                print(item.name)


def get_git_rev(repo_path):
    """Get the current git revision of a repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "unknown"


def create_target_repo(target_path):
    """Initialize the target repo as a git repository."""
    target_path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=target_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=target_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=target_path, check=True, capture_output=True)


def take_source_snapshot(source_path):
    """Take a snapshot of the source repo's file modification times to detect writes."""
    snapshot = {}
    for root, dirs, files in os.walk(source_path):
        for file in files:
            filepath = Path(root) / file
            snapshot[str(filepath)] = filepath.stat().st_mtime
    return snapshot


def check_source_write_protection(initial_snapshot, source_path):
    """Check if any files in the source repo were modified."""
    current_snapshot = {}
    for root, dirs, files in os.walk(source_path):
        for file in files:
            filepath = Path(root) / file
            current_snapshot[str(filepath)] = filepath.stat().st_mtime
    
    changed_files = []
    for filepath, initial_time in initial_snapshot.items():
        current_time = current_snapshot.get(filepath)
        if current_time != initial_time:
            changed_files.append(filepath)
    
    # Check for newly added files
    for filepath in current_snapshot:
        if filepath not in initial_snapshot:
            changed_files.append(filepath)
    
    return len(changed_files) == 0, changed_files


def capture_target_diff(target_path, run_path):
    """Capture git diff and status from the target repo."""
    diff_path = run_path / "diff"
    diff_path.mkdir(exist_ok=True)
    
    try:
        # Git status
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=target_path,
            capture_output=True,
            text=True
        )
        with open(diff_path / "status.txt", "w") as f:
            f.write(status_result.stdout)
        
        # Git diff
        diff_result = subprocess.run(
            ["git", "diff"],
            cwd=target_path,
            capture_output=True,
            text=True
        )
        with open(diff_path / "diff.patch", "w") as f:
            f.write(diff_result.stdout)
        
        # Git log
        log_result = subprocess.run(
            ["git", "log", "-1", "--oneline"],
            cwd=target_path,
            capture_output=True,
            text=True
        )
        with open(diff_path / "log.txt", "w") as f:
            f.write(log_result.stdout)
    except Exception as e:
        print(f"Error capturing target diff: {e}")


def copy_artifacts(scenario_path, run_path):
    """Copy or symlink Maestro convert artifacts."""
    artifacts_path = run_path / "artifacts"
    artifacts_path.mkdir(exist_ok=True)
    
    maestro_convert_path = Path(".maestro/convert")
    if maestro_convert_path.exists():
        try:
            shutil.copytree(maestro_convert_path, artifacts_path / "convert", dirs_exist_ok=True)
        except Exception as e:
            print(f"Error copying artifacts: {e}")
    
    # Also copy any report files
    report_md = Path("report.md")
    if report_md.exists():
        shutil.copy2(report_md, artifacts_path / "report.md")


def capture_summary_json(scenario_name, intent, source_path, target_path, stages_status, cmd_exit_codes, writes_to_source, run_path):
    """Generate a summary JSON file with execution details."""
    summary_data = {
        "scenario_name": scenario_name,
        "timestamp": datetime.now().isoformat(),
        "intent": intent,
        "source_repo_path": str(source_path),
        "source_repo_rev": get_git_rev(source_path),
        "target_repo_path": str(target_path),
        "target_repo_rev": get_git_rev(target_path),
        "stages_executed": stages_status,
        "command_exit_codes": cmd_exit_codes,
        "writes_detected_to_source": not writes_to_source[0],  # True if writes detected
        "changed_files_in_source": writes_to_source[1] if not writes_to_source[0] else []
    }
    
    reports_path = run_path / "reports"
    reports_path.mkdir(exist_ok=True)
    
    with open(reports_path / "summary.json", "w") as f:
        json.dump(summary_data, f, indent=2)


def run_maestro_convert_subprocess(cmd, timeout=None, interrupt_after=None):
    """Run Maestro convert as a subprocess with optional interruption."""
    try:
        # Prepare the process
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if interrupt_after:
            # Wait for specified time then interrupt
            time.sleep(interrupt_after)
            proc.send_signal(signal.SIGINT)
            try:
                stdout, stderr = proc.communicate(timeout=5)  # Give process some time to handle SIGINT gracefully
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
        else:
            # Wait for process to complete normally
            stdout, stderr = proc.communicate(timeout=timeout)
        
        return proc.returncode, stdout, stderr
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        return proc.returncode, stdout, stderr


def main():
    args = parse_args()
    
    # Handle --list flag
    if args.list:
        list_scenarios()
        return 0
    
    # Validate scenario argument
    if not args.scenario:
        print("Error: --scenario is required", file=sys.stderr)
        return 1
    
    scenario_path = Path(f"tools/convert_tests/scenarios/{args.scenario}")
    if not scenario_path.exists():
        print(f"Error: Scenario '{args.scenario}' not found", file=sys.stderr)
        return 1
    
    # Determine intent from scenario's notes.md if it exists
    notes_file = scenario_path / "notes.md"
    intent = "Generic conversion test"
    if notes_file.exists():
        with open(notes_file, 'r') as f:
            content = f.read()
            # Simple extraction of intent from notes - look for "Intent:" or "## Intent" or similar
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if "## Intent" in line:
                    # Get the next non-empty line which should contain the actual intent
                    j = i + 1
                    while j < len(lines):
                        next_line = lines[j].strip()
                        if next_line and not next_line.startswith("#"):
                            intent = next_line
                            break
                        j += 1
                    break
            # If we couldn't find a specific intent line, look for any line containing the word intent
            if intent == "Generic conversion test":
                for line in lines:
                    if "intent" in line.lower() and not line.startswith("#"):
                        intent = line.strip()
                        break
    
    # Setup run directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_path = Path(f"tools/convert_tests/runs/{args.scenario}/{timestamp}")
    run_path.mkdir(parents=True, exist_ok=True)
    
    # Setup logging
    log_file = run_path / "logs" / "run.log"
    log_file.parent.mkdir(exist_ok=True)
    
    def log(message):
        timestamped_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"
        if args.verbose:
            print(timestamped_msg)
        with open(log_file, "a") as f:
            f.write(timestamped_msg + "\n")
    
    log(f"Starting scenario: {args.scenario}")
    log(f"Run path: {run_path}")
    
    # Get source and target paths
    source_path = scenario_path / "source_repo"
    target_path = scenario_path / "target_repo"
    
    # Take initial snapshot of source for write protection
    source_snapshot_before = take_source_snapshot(source_path)
    log("Source repo snapshot taken before conversion")
    
    # Initialize or clean target repo
    if args.force_clean and target_path.exists():
        log("Force cleaning target repo")
        shutil.rmtree(target_path)
    
    if not target_path.exists():
        log("Creating and initializing target repo")
        create_target_repo(target_path)
    elif not args.keep_target:
        log("Cleaning target repo for fresh run")
        subprocess.run(["git", "reset", "--hard"], cwd=target_path, check=True, capture_output=True)
        subprocess.run(["git", "clean", "-fd"], cwd=target_path, check=True, capture_output=True)
    
    stages_status = {}
    cmd_exit_codes = {}
    
    if args.no_ai:
        log("Dry run mode enabled - not executing Maestro commands")
        # Just validate that necessary files exist
        if not source_path.exists():
            log("ERROR: Source repo not found")
            return 1
        if not target_path.exists():
            log("ERROR: Target repo not found")
            return 1
        log("Dry run validation successful")
    else:
        # Run Maestro convert pipeline
        log("Running Maestro convert pipeline")
        
        # Create pipeline
        create_cmd = [
            sys.executable, "maestro.py", "convert", "new",
            str(source_path),
            str(target_path),
            "--intent", intent
        ]
        log(f"Running: {' '.join(create_cmd)}")
        
        exit_code, stdout, stderr = run_maestro_convert_subprocess(create_cmd, interrupt_after=args.interrupt_after)
        cmd_exit_codes["create"] = exit_code
        log(f"Create command exit code: {exit_code}")
        
        if exit_code == 0:
            stages_status["create"] = "success"
            
            # Run pipeline
            # For language_to_language conversions, run specific stages as per requirements
            if intent == "language_to_language":
                # Run semantic_mapping stage first
                semantic_cmd = [sys.executable, "maestro.py", "convert", "run", "--stage", "semantic_mapping"]
                log(f"Running: {' '.join(semantic_cmd)}")

                exit_code, stdout, stderr = run_maestro_convert_subprocess(semantic_cmd, interrupt_after=args.interrupt_after)
                cmd_exit_codes["semantic_mapping"] = exit_code
                log(f"Semantic mapping stage exit code: {exit_code}")

                if exit_code == 0:
                    stages_status["semantic_mapping"] = "success"
                else:
                    stages_status["semantic_mapping"] = "failed"

                # Run overview stage
                overview_cmd = [sys.executable, "maestro.py", "convert", "run", "--stage", "overview"]
                log(f"Running: {' '.join(overview_cmd)}")

                exit_code, stdout, stderr = run_maestro_convert_subprocess(overview_cmd, interrupt_after=args.interrupt_after)
                cmd_exit_codes["overview"] = exit_code
                log(f"Overview stage exit code: {exit_code}")

                if exit_code == 0:
                    stages_status["overview"] = "success"
                else:
                    stages_status["overview"] = "failed"

                # Run realize stage if it's available
                realize_cmd = [sys.executable, "maestro.py", "convert", "run", "--stage", "realize"]
                log(f"Running: {' '.join(realize_cmd)}")

                exit_code, stdout, stderr = run_maestro_convert_subprocess(realize_cmd, interrupt_after=args.interrupt_after)
                cmd_exit_codes["realize"] = exit_code
                log(f"Realize stage exit code: {exit_code}")

                if exit_code == 0:
                    stages_status["realize"] = "success"
                else:
                    stages_status["realize"] = "failed"

                # The overall "run" success depends on all required stages
                all_stages_successful = all(status == "success" for status in stages_status.values())
                if all_stages_successful:
                    stages_status["run"] = "success"
                else:
                    stages_status["run"] = "failed"
            else:
                # For other intents, run the full pipeline as before
                run_cmd = [sys.executable, "maestro.py", "convert", "run"]
                log(f"Running: {' '.join(run_cmd)}")

                exit_code, stdout, stderr = run_maestro_convert_subprocess(run_cmd, interrupt_after=args.interrupt_after)
                cmd_exit_codes["run"] = exit_code
                log(f"Run command exit code: {exit_code}")

                if exit_code == 0:
                    stages_status["run"] = "success"
                else:
                    stages_status["run"] = "failed"
        else:
            stages_status["create"] = "failed"
        
        # Capture artifacts
        log("Capturing artifacts")
        copy_artifacts(scenario_path, run_path)
    
    # Check for writes to source
    log("Checking for writes to source repo")
    writes_to_source = check_source_write_protection(source_snapshot_before, source_path)
    log(f"Writes to source detected: {not writes_to_source[0]}")
    
    if not writes_to_source[0]:
        log(f"FAILED: Files were modified in source repo: {writes_to_source[1]}")
        # Still continue to capture summary but mark failure
    else:
        log("Source write protection check passed")
    
    # Capture target diff
    log("Capturing target repo diff")
    capture_target_diff(target_path, run_path)
    
    # Generate summary
    log("Generating summary")
    capture_summary_json(
        args.scenario, intent, source_path, target_path,
        stages_status, cmd_exit_codes, writes_to_source, run_path
    )

    # Load summary data for golden comparison
    summary_path = run_path / "reports" / "summary.json"
    if summary_path.exists():
        with open(summary_path, 'r') as f:
            summary_data = json.load(f)
    
    # Determine success status before golden validation
    success = all(status == "success" for status in stages_status.values()) if stages_status else True  # If dry run, no stages were executed but we consider it successful
    source_unchanged = writes_to_source[0]
    overall_success = success and source_unchanged

    # Golden report matching (if applicable)
    expected_path = scenario_path / "expected"
    if expected_path.exists():
        if args.update_golden:
            log("Updating golden files")
            # Copy current artifacts to expected directory for reference
            expected_artifacts_path = expected_path / "artifacts"
            if expected_artifacts_path.exists():
                shutil.rmtree(expected_artifacts_path)
            if (run_path / "artifacts").exists():
                shutil.copytree(run_path / "artifacts", expected_artifacts_path)

            # Save current summary as expected
            with open(expected_path / "summary.json", "w") as f:
                json.dump(summary_data, f, indent=2)
        else:
            log("Checking against golden files")
            # Basic validation against expected files
            expected_summary_path = expected_path / "summary.json"
            if expected_summary_path.exists():
                try:
                    with open(expected_summary_path, 'r') as f:
                        expected_summary = json.load(f)

                    # Basic validation: check expected stages are present
                    expected_stages = expected_summary.get("expected_stages", [])
                    for stage in expected_stages:
                        if stage not in stages_status:
                            log(f"FAILED: Expected stage '{stage}' not found in actual stages")
                            overall_success = False

                    # Check success expectation
                    expected_success = expected_summary.get("expected_success", True)
                    actual_success = success
                    if expected_success != actual_success:
                        log(f"FAILED: Expected success={expected_success}, got success={actual_success}")
                        overall_success = False
                except Exception as e:
                    log(f"Error validating against golden summary: {e}")
            else:
                log("Warning: No expected summary.json found for this scenario")

    # Update overall success after golden validation
    # Make sure source repo wasn't modified (essential requirement)
    if not source_unchanged:
        overall_success = False
        log("FAILED: Source repo was modified")
    # The golden validation already updated overall_success appropriately

    log(f"Scenario {args.scenario} {'PASSED' if overall_success else 'FAILED'}")

    return 0 if overall_success else 1


if __name__ == "__main__":
    sys.exit(main())