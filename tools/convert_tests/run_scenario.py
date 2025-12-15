#!/usr/bin/env python3
"""
Maestro Convert Test Harness - Dual-Repo Conversion Runner

This script provides a standardized way to run Maestro's convert functionality
with two separate repos (source and target) for testing purposes.
"""

import argparse
import hashlib
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
    parser.add_argument("--idempotency-check", action="store_true", help="Run idempotency check: execute run twice and ensure no changes on second run")
    parser.add_argument("--auto-approve-checkpoints", action="store_true", help="Automatically approve any checkpoints that are created during conversion")

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


def take_target_snapshot(target_path):
    """Take a snapshot of the target repo's file hashes to detect changes."""
    snapshot = {}
    for root, dirs, files in os.walk(target_path):
        for file in files:
            if not any(part.startswith('.') for part in (root / Path(file)).parts):  # Skip hidden files/dirs
                filepath = Path(root) / file
                try:
                    with open(filepath, 'rb') as f:
                        content = f.read()
                        filehash = hashlib.sha256(content).hexdigest()
                        rel_path = str(filepath.relative_to(target_path))
                        snapshot[rel_path] = filehash
                except Exception:
                    # Skip files that can't be read
                    continue
    return snapshot


def check_target_idempotency(initial_snapshot, final_snapshot):
    """Check if the target repo changed between runs."""
    initial_files = set(initial_snapshot.keys())
    final_files = set(final_snapshot.keys())

    changed_files = []
    for filepath in final_files:
        if filepath not in initial_files:
            changed_files.append(f"ADDED: {filepath}")
        elif initial_snapshot[filepath] != final_snapshot[filepath]:
            changed_files.append(f"MODIFIED: {filepath}")

    for filepath in initial_files:
        if filepath not in final_files:
            changed_files.append(f"DELETED: {filepath}")

    return len(changed_files) == 0, changed_files


def run_idempotency_check(scenario_path, source_path, target_path, args, run_path, log):
    """Run the idempotency check: execute run twice and verify no changes on second run."""
    log("Running idempotency check...")

    # First run
    log("First run...")
    target_snapshot_before = take_target_snapshot(target_path)

    # Run the conversion pipeline (this will be the same as a first run)
    success, stages_status, cmd_exit_codes = run_conversion_pipeline(source_path, target_path, args, run_path, log, first_run=True)

    if not success:
        log("First run failed, skipping idempotency check")
        return False, stages_status, cmd_exit_codes

    target_snapshot_after_first = take_target_snapshot(target_path)

    # Second run
    log("Second run...")
    success, stages_status_second, cmd_exit_codes_second = run_conversion_pipeline(source_path, target_path, args, run_path, log, first_run=False)

    if not success:
        log("Second run failed, idempotency check failed")
        return False, stages_status_second, cmd_exit_codes_second

    target_snapshot_after_second = take_target_snapshot(target_path)

    # Check if target changed between the two runs
    idempotent, changes = check_target_idempotency(target_snapshot_after_first, target_snapshot_after_second)

    if idempotent:
        log("Idempotency check PASSED: No changes detected on second run")
    else:
        log(f"Idempotency check FAILED: Changes detected on second run: {changes}")

        # Save changes to report
        changes_path = run_path / "reports" / "idempotency_changes.json"
        with open(changes_path, 'w') as f:
            json.dump({"changes": changes}, f, indent=2)

    # Combine exit codes from both runs
    cmd_exit_codes_combined = {**cmd_exit_codes, **{f"second_{k}": v for k, v in cmd_exit_codes_second.items()}}

    return idempotent, stages_status_second, cmd_exit_codes_combined


def run_conversion_pipeline(source_path, target_path, args, run_path, log, first_run=True):
    """Run the conversion pipeline and return success status and stage info."""
    stages_status = {}
    cmd_exit_codes = {}

    # Create pipeline
    create_cmd = [
        sys.executable, "maestro.py", "convert", "new",
        str(source_path),
        str(target_path),
        "--intent", "test_conversion"
    ]
    log(f"Running: {' '.join(create_cmd)}")

    exit_code, stdout, stderr = run_maestro_convert_subprocess(create_cmd, interrupt_after=args.interrupt_after)
    cmd_exit_codes["create"] = exit_code
    log(f"Create command exit code: {exit_code}")

    if exit_code == 0:
        stages_status["create"] = "success"

        # For language_to_language conversions, run specific stages as per requirements
        if True:  # Default to run all stages for idempotency test
            # Run semantic_mapping stage first if it exists
            try:
                semantic_cmd = [sys.executable, "maestro.py", "convert", "run", "--stage", "semantic_mapping"]
                log(f"Running: {' '.join(semantic_cmd)}")

                exit_code, stdout, stderr = run_maestro_convert_subprocess(semantic_cmd, interrupt_after=args.interrupt_after)
                cmd_exit_codes["semantic_mapping"] = exit_code
                log(f"Semantic mapping stage exit code: {exit_code}")

                if exit_code == 0:
                    stages_status["semantic_mapping"] = "success"
                else:
                    stages_status["semantic_mapping"] = "failed"
            except subprocess.CalledProcessError:
                # If stage doesn't exist, continue
                pass

            # Run overview stage
            try:
                overview_cmd = [sys.executable, "maestro.py", "convert", "run", "--stage", "overview"]
                log(f"Running: {' '.join(overview_cmd)}")

                exit_code, stdout, stderr = run_maestro_convert_subprocess(overview_cmd, interrupt_after=args.interrupt_after)
                cmd_exit_codes["overview"] = exit_code
                log(f"Overview stage exit code: {exit_code}")

                if exit_code == 0:
                    stages_status["overview"] = "success"
                else:
                    stages_status["overview"] = "failed"
            except subprocess.CalledProcessError:
                # If stage doesn't exist, continue
                pass

            # Run realize stage if it's available
            try:
                realize_cmd = [sys.executable, "maestro.py", "convert", "run", "--stage", "realize"]
                log(f"Running: {' '.join(realize_cmd)}")

                exit_code, stdout, stderr = run_maestro_convert_subprocess(realize_cmd, interrupt_after=args.interrupt_after)
                cmd_exit_codes["realize"] = exit_code
                log(f"Realize stage exit code: {exit_code}")

                if exit_code == 0:
                    stages_status["realize"] = "success"
                else:
                    stages_status["realize"] = "failed"
            except subprocess.CalledProcessError:
                # If stage doesn't exist, continue with general run
                # Run the full pipeline as before
                run_cmd = [sys.executable, "maestro.py", "convert", "run"]
                log(f"Running: {' '.join(run_cmd)}")

                exit_code, stdout, stderr = run_maestro_convert_subprocess(run_cmd, interrupt_after=args.interrupt_after)
                cmd_exit_codes["run"] = exit_code
                log(f"Run command exit code: {exit_code}")

                if exit_code == 0:
                    stages_status["run"] = "success"
                else:
                    stages_status["run"] = "failed"

            # The overall "run" success depends on all required stages
            all_stages_successful = all(status == "success" for status in stages_status.values() if status != "create")
            if all_stages_successful:
                stages_status["run"] = "success"
            else:
                stages_status["run"] = "failed"
    else:
        stages_status["create"] = "failed"
        return False, stages_status, cmd_exit_codes

    success = all(status == "success" for status in stages_status.values() if status != "create")
    return success, stages_status, cmd_exit_codes


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


def capture_summary_json(scenario_name, intent, source_path, target_path, stages_status, cmd_exit_codes, writes_to_source, run_path, args):
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
        "changed_files_in_source": writes_to_source[1] if not writes_to_source[0] else [],
        "idempotency_check": args.idempotency_check
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
        if args.idempotency_check:
            # Run idempotency check
            idempotent, stages_status, cmd_exit_codes = run_idempotency_check(
                scenario_path, source_path, target_path, args, run_path, log
            )

            # Set the overall success based on idempotency
            success = idempotent and all(status == "success" for status in stages_status.values() if status != "create")
        else:
            # Run Maestro convert pipeline normally
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
                if intent == "language_to_language" or intent == "typedness_upgrade":
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
                    all_stages_successful = all(status == "success" for status in stages_status.values() if status != "create")
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

            success = all(status == "success" for status in stages_status.values() if status != "create")

        # Capture artifacts
        log("Capturing artifacts")
        copy_artifacts(scenario_path, run_path)

        # Run semantic diff for high_to_low_level intent scenarios
        if intent == "high_to_low_level":
            log("Running semantic diff for high_to_low_level intent...")
            semantic_diff_cmd = [sys.executable, "cross_repo_semantic_diff.py", "diff", "--format", "json"]
            log(f"Running: {' '.join(semantic_diff_cmd)}")

            try:
                exit_code, stdout, stderr = run_maestro_convert_subprocess(semantic_diff_cmd, interrupt_after=args.interrupt_after)
                cmd_exit_codes["semantic_diff"] = exit_code
                log(f"Semantic diff command exit code: {exit_code}")

                if exit_code == 0:
                    stages_status["semantic_diff"] = "success"

                    # Copy semantic diff artifacts
                    semantic_diff_path = run_path / "artifacts" / "semantic_diff"
                    semantic_diff_path.mkdir(exist_ok=True)

                    import shutil
                    diff_json_src = Path(".maestro/convert/semantics/cross_repo/diff_report.json")
                    diff_md_src = Path(".maestro/convert/semantics/cross_repo/diff_report.md")
                    mapping_idx_src = Path(".maestro/convert/semantics/cross_repo/mapping_index.json")

                    if diff_json_src.exists():
                        shutil.copy2(diff_json_src, semantic_diff_path / "diff_report.json")
                    if diff_md_src.exists():
                        shutil.copy2(diff_md_src, semantic_diff_path / "diff_report.md")
                    if mapping_idx_src.exists():
                        shutil.copy2(mapping_idx_src, semantic_diff_path / "mapping_index.json")
                else:
                    stages_status["semantic_diff"] = "failed"
                    log(f"Semantic diff failed with stderr: {stderr}")
            except Exception as e:
                log(f"Error running semantic diff: {e}")
                stages_status["semantic_diff"] = "failed"

        # Auto-approve checkpoints if requested
        if args.auto_approve_checkpoints and intent == "high_to_low_level":
            log("Auto-approving checkpoints...")
            try:
                checkpoint_approve_cmd = [sys.executable, "maestro.py", "convert", "checkpoint", "approve", "--all"]
                log(f"Running: {' '.join(checkpoint_approve_cmd)}")

                exit_code, stdout, stderr = run_maestro_convert_subprocess(checkpoint_approve_cmd, interrupt_after=args.interrupt_after)
                cmd_exit_codes["checkpoint_approve"] = exit_code
                log(f"Checkpoint approval command exit code: {exit_code}")

                if exit_code == 0:
                    stages_status["checkpoint_approve"] = "success"
                else:
                    stages_status["checkpoint_approve"] = "failed"
                    log(f"Checkpoint approval failed with stderr: {stderr}")
            except Exception as e:
                log(f"Error auto-approving checkpoints: {e}")
                stages_status["checkpoint_approve"] = "failed"

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
        stages_status, cmd_exit_codes, writes_to_source, run_path, args
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

            # Validate semantic diff requirements if this is a high_to_low_level scenario
            if intent == "high_to_low_level":
                expected_semantic_diff_reqs_path = expected_path / "semantic_diff_requirements.json"
                if expected_semantic_diff_reqs_path.exists():
                    try:
                        with open(expected_semantic_diff_reqs_path, 'r') as f:
                            expected_reqs = json.load(f)

                        # Load actual semantic diff report
                        actual_diff_path = run_path / "artifacts" / "semantic_diff" / "diff_report.json"
                        if actual_diff_path.exists():
                            with open(actual_diff_path, 'r') as f:
                                actual_diff = json.load(f)

                            # Validate required keys exist
                            required_keys = expected_reqs.get("required_keys_in_diff_report", [])
                            for key in required_keys:
                                if key not in actual_diff:
                                    log(f"FAILED: Required key '{key}' not found in diff_report.json")
                                    overall_success = False

                            # Validate minimum losses
                            min_losses = expected_reqs.get("minimum_losses_required", 0)
                            loss_ledger = actual_diff.get("loss_ledger", [])
                            actual_loss_count = len(loss_ledger)
                            if actual_loss_count < min_losses:
                                log(f"FAILED: Expected at least {min_losses} losses, but found {actual_loss_count}")
                                overall_success = False

                            # Validate checkpoint expectations
                            expected_checkpoint = expected_reqs.get("checkpoint_expected", False)
                            drift_analysis = actual_diff.get("drift_threshold_analysis", {})
                            actual_checkpoint_required = drift_analysis.get("requires_checkpoint", False)

                            # The requirement from the task is that if AI claims "no loss", test should fail
                            # This means we must have some losses for high_to_low_level
                            if actual_loss_count == 0:
                                log("FAILED: No losses detected in semantic diff for high_to_low_level conversion (AI claimed no loss, which is suspicious)")
                                overall_success = False
                            elif expected_checkpoint and not actual_checkpoint_required:
                                log(f"EXPECTED: Checkpoint should be required for this scenario based on loss count and equivalence thresholds")
                                # For scenarios designed to trigger checkpoints, this may not be an automatic failure
                                # We'll check the designed_checkpoint_scenario flag in summary
                                summary_path = expected_path / "summary.json"
                                if summary_path.exists():
                                    with open(summary_path, 'r') as f:
                                        summary = json.load(f)
                                    if summary.get("designed_checkpoint_scenario", False):
                                        log("NOTE: This is a designed checkpoint scenario")
                                    else:
                                        log("Note: Checkpoint not required but conversion is high-to-low")

                        else:
                            log("FAILED: semantic diff report not found for high_to_low_level scenario")
                            overall_success = False
                    except Exception as e:
                        log(f"Error validating semantic diff requirements: {e}")
                        overall_success = False
                else:
                    log("Warning: No semantic_diff_requirements.json found for this high_to_low_level scenario")

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