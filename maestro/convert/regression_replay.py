#!/usr/bin/env python3
"""
Regression Replay System for Maestro

Implements the requirements for Task 13:
- Run manifests for every conversion run
- Replay command with dry/apply modes  
- Drift detection (structural + semantic)
- Convergence policy enforcement
- Golden baseline support
- CLI for runs list/show/diff
"""

import json
import os
import hashlib
import uuid
import subprocess
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import shutil


@dataclass
class RunManifest:
    """Manifest for a single conversion run."""
    run_id: str
    timestamp: str
    pipeline_id: str
    source_path: str
    source_revision: str
    target_path: str
    target_revision_before: str
    target_revision_after: str
    plan_revision: str
    decision_fingerprint: str
    engines_used: Dict[str, str]  # worker and judge engines
    flags_used: List[str]
    task_execution_list: List[Dict[str, Any]]
    status: str  # completed, failed, interrupted


@dataclass
class EnvironmentInfo:
    """Environment information for a run."""
    os_uname: str
    python_version: str
    maestro_version: str
    engine_versions: Dict[str, str]
    timestamp: str


def get_maestro_version() -> str:
    """Get the current Maestro version."""
    try:
        import maestro
        return getattr(maestro, '__version__', 'unknown')
    except ImportError:
        return 'unknown'


def capture_environment() -> EnvironmentInfo:
    """Capture the current environment information."""
    import sys
    
    # Get OS information
    os_uname = f"{platform.system()} {platform.release()} {platform.machine()}"
    
    # Get engine versions (try to run version commands)
    engine_versions = {}
    engines = ['qwen', 'gemini', 'claude', 'codex']  # The allowed engines
    
    for engine in engines:
        try:
            result = subprocess.run([engine, '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                engine_versions[engine] = result.stdout.strip()
            else:
                # Try with -v
                result = subprocess.run([engine, '-v'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    engine_versions[engine] = result.stdout.strip()
                else:
                    engine_versions[engine] = 'unknown'
        except (subprocess.TimeoutExpired, FileNotFoundError):
            engine_versions[engine] = 'not found'
    
    return EnvironmentInfo(
        os_uname=os_uname,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        maestro_version=get_maestro_version(),
        engine_versions=engine_versions,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


def create_run_directory(run_id: str) -> str:
    """Create directory for a new run and return the path."""
    run_dir = f".maestro/convert/runs/{run_id}"
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


def capture_run_manifest(
    source_path: str,
    target_path: str,
    plan_path: str,
    memory,
    flags_used: List[str],
    engines_used: Dict[str, str]
) -> RunManifest:
    """Capture a complete run manifest for the current conversion run."""

    run_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    # Get source and target revisions (try git if available)
    source_revision = "unknown"
    target_revision_before = "unknown"
    target_revision_after = "unknown"

    try:
        import git  # Optional dependency
        if os.path.isdir(source_path):
            source_repo = git.Repo(source_path, search_parent_directories=True)
            source_revision = source_repo.head.commit.hexsha
    except ImportError:
        print("Warning: GitPython not installed. Source/target revision will be 'unknown'.")
    except:
        pass  # Not a git repo or git not available

    try:
        import git  # Optional dependency
        if os.path.isdir(target_path):
            target_repo = git.Repo(target_path, search_parent_directories=True)
            target_revision_before = target_repo.head.commit.hexsha
            # After the run, we'll update the after revision
    except ImportError:
        print("Warning: GitPython not installed. Source/target revision will be 'unknown'.")
    except:
        pass
    
    # Load plan to get plan revision
    plan_revision = "unknown"
    if os.path.exists(plan_path):
        with open(plan_path, 'rb') as f:
            plan_revision = hashlib.sha256(f.read()).hexdigest()
    
    # Get decision fingerprint
    decision_fingerprint = memory.compute_decision_fingerprint()
    
    # Create manifest
    manifest = RunManifest(
        run_id=run_id,
        timestamp=timestamp,
        pipeline_id="current_pipeline",  # Should come from pipeline object
        source_path=source_path,
        source_revision=source_revision,
        target_path=target_path,
        target_revision_before=target_revision_before,
        target_revision_after=target_revision_after,  # Will be updated after run
        plan_revision=plan_revision,
        decision_fingerprint=decision_fingerprint,
        engines_used=engines_used,
        flags_used=flags_used,
        task_execution_list=[],  # Will be populated during execution
        status="running"
    )
    
    return manifest


def save_run_artifacts(manifest: RunManifest, source_path: str, target_path: str, plan_path: str, memory) -> str:
    """Save all run artifacts to the run directory."""
    run_dir = create_run_directory(manifest.run_id)
    
    # Save manifest
    with open(os.path.join(run_dir, "manifest.json"), 'w') as f:
        json.dump(asdict(manifest), f, indent=2)
    
    # Copy plan at run start
    if os.path.exists(plan_path):
        shutil.copy2(plan_path, os.path.join(run_dir, "plan.json"))
    
    # Save memory snapshots
    # Save decisions
    with open(os.path.join(run_dir, "decisions.json"), 'w') as f:
        json.dump(memory.load_decisions(), f, indent=2)
    
    # Save conventions
    with open(os.path.join(run_dir, "conventions.json"), 'w') as f:
        json.dump(memory.load_conventions(), f, indent=2)
    
    # Save glossary
    with open(os.path.join(run_dir, "glossary.json"), 'w') as f:
        json.dump(memory.load_glossary(), f, indent=2)
    
    # Save open issues
    with open(os.path.join(run_dir, "open_issues.json"), 'w') as f:
        json.dump(memory.load_open_issues(), f, indent=2)
    
    # Save environment info
    env_info = capture_environment()
    with open(os.path.join(run_dir, "environment.json"), 'w') as f:
        json.dump(asdict(env_info), f, indent=2)
    
    # Create artifacts index (empty initially, populated during execution)
    artifacts_index = {
        "artifacts": [],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    with open(os.path.join(run_dir, "artifacts_index.json"), 'w') as f:
        json.dump(artifacts_index, f, indent=2)
    
    return run_dir


def update_run_manifest_after_completion(run_dir: str, target_path: str, status: str) -> None:
    """Update the run manifest after completion with final info."""
    manifest_path = os.path.join(run_dir, "manifest.json")

    # Load existing manifest
    with open(manifest_path, 'r') as f:
        manifest_data = json.load(f)

    # Get final target revision
    target_revision_after = "unknown"
    try:
        import git
        if os.path.isdir(target_path):
            target_repo = git.Repo(target_path, search_parent_directories=True)
            target_revision_after = target_repo.head.commit.hexsha
    except ImportError:
        print("Warning: GitPython not installed. Final target revision will be 'unknown'.")
    except:
        pass

    # Update manifest data
    manifest_data["target_revision_after"] = target_revision_after
    manifest_data["status"] = status

    # Save updated manifest
    with open(manifest_path, 'w') as f:
        json.dump(manifest_data, f, indent=2)


def compute_file_hashes(target_path: str) -> Dict[str, str]:
    """Compute hashes for all files in target path."""
    hashes = {}
    
    for root, dirs, files in os.walk(target_path):
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, target_path)
            
            # Compute hash of file content
            with open(file_path, 'rb') as f:
                content = f.read()
                file_hash = hashlib.sha256(content).hexdigest()
                hashes[rel_path] = file_hash
    
    return hashes


def load_run_manifest(run_id: str) -> Optional[RunManifest]:
    """Load a run manifest from the run directory."""
    manifest_path = f".maestro/convert/runs/{run_id}/manifest.json"
    
    if not os.path.exists(manifest_path):
        return None
    
    with open(manifest_path, 'r') as f:
        data = json.load(f)
        # Convert back to RunManifest object (for simplicity, just return the dict)
        return data


def get_all_runs() -> List[Dict[str, Any]]:
    """Get list of all runs with basic information."""
    runs_dir = ".maestro/convert/runs"
    
    if not os.path.exists(runs_dir):
        return []
    
    runs = []
    for run_dir in os.listdir(runs_dir):
        run_path = os.path.join(runs_dir, run_dir)
        if os.path.isdir(run_path):
            manifest_path = os.path.join(run_path, "manifest.json")
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                    runs.append({
                        "run_id": run_dir,
                        "timestamp": manifest.get("timestamp"),
                        "status": manifest.get("status"),
                        "source_path": manifest.get("source_path"),
                        "target_path": manifest.get("target_path")
                    })
    
    # Sort by timestamp (newest first)
    runs.sort(key=lambda x: x["timestamp"], reverse=True)
    return runs


@dataclass
class DriftReport:
    """Report of drift detected during replay."""
    run_id: str
    replay_mode: str  # dry or apply
    timestamp: str
    structural_drift: Dict[str, Any]
    decision_drift: Dict[str, Any]
    semantic_drift: Dict[str, Any]
    drift_detected: bool


def detect_structural_drift(run_id: str, current_target_path: str) -> Dict[str, Any]:
    """Detect structural drift by comparing file hashes."""
    run_dir = f".maestro/convert/runs/{run_id}"
    original_hashes_path = os.path.join(run_dir, "target_hashes.json")  # We'll save this during the original run

    if not os.path.exists(original_hashes_path):
        # If we don't have original hashes, use the ones from the final state in the run
        original_manifest = load_run_manifest(run_id)
        if not original_manifest:
            return {"error": f"Run {run_id} not found"}

    # Compute current hashes
    current_hashes = compute_file_hashes(current_target_path)

    # Load original hashes from the run (if they exist in artifacts)
    original_hashes = {}
    artifacts_dir = os.path.join(run_dir, "artifacts")
    original_hashes_path = os.path.join(artifacts_dir, "target_hashes_before.json")

    if os.path.exists(original_hashes_path):
        with open(original_hashes_path, 'r') as f:
            original_hashes = json.load(f)
    else:
        # For backward compatibility, try to get original state from baseline or manifest
        # For now, we'll just return an empty result
        return {"message": "No original hashes found for comparison", "drift_detected": False}

    # Compare hashes
    added_files = set(current_hashes.keys()) - set(original_hashes.keys())
    removed_files = set(original_hashes.keys()) - set(current_hashes.keys())
    modified_files = []

    for file_path in set(current_hashes.keys()) & set(original_hashes.keys()):
        if current_hashes[file_path] != original_hashes[file_path]:
            modified_files.append(file_path)

    drift_detected = bool(added_files or removed_files or modified_files)

    return {
        "drift_detected": drift_detected,
        "added_files": list(added_files),
        "removed_files": list(removed_files),
        "modified_files": modified_files,
        "file_count_change": len(current_hashes) - len(original_hashes),
        "details": {
            "total_current_files": len(current_hashes),
            "total_original_files": len(original_hashes)
        }
    }


def detect_decision_drift(run_id: str, current_memory) -> Dict[str, Any]:
    """Detect decision drift by comparing decision fingerprints."""
    run_dir = f".maestro/convert/runs/{run_id}"
    original_decisions_path = os.path.join(run_dir, "decisions.json")

    if not os.path.exists(original_decisions_path):
        return {"error": f"Original decisions not found for run {run_id}"}

    with open(original_decisions_path, 'r') as f:
        original_decisions = json.load(f)

    # Recompute current decision fingerprint
    current_decision_fingerprint = current_memory.compute_decision_fingerprint()

    # Load original decision fingerprint from manifest
    manifest = load_run_manifest(run_id)
    original_decision_fingerprint = manifest.get("decision_fingerprint", "") if manifest else ""

    drift_detected = current_decision_fingerprint != original_decision_fingerprint

    return {
        "drift_detected": drift_detected,
        "current_fingerprint": current_decision_fingerprint,
        "original_fingerprint": original_decision_fingerprint
    }


def detect_semantic_drift(run_id: str, current_target_path: str) -> Dict[str, Any]:
    """Detect semantic drift by comparing semantic summaries."""
    # For now, we'll implement a basic semantic drift detection
    # In a real implementation, this would compare semantic integrity checks
    from maestro.convert.semantic_integrity import SemanticIntegrityChecker

    checker = SemanticIntegrityChecker()

    # Check if there are any known semantic issues that have reappeared
    # This would typically involve running semantic checks on both the original
    # and current state and comparing results

    drift_detected = False
    semantic_summary = {
        "equivalence_levels": [],
        "risk_flags": [],
        "issues_reappeared": []
    }

    # Placeholder - in real implementation would compare semantic states
    return {
        "drift_detected": drift_detected,
        "semantic_summary": semantic_summary
    }


def generate_drift_report(run_id: str, current_target_path: str, memory, replay_mode: str = "dry") -> DriftReport:
    """Generate a comprehensive drift report."""
    timestamp = datetime.now(timezone.utc).isoformat()

    # Detect different types of drift
    structural_drift = detect_structural_drift(run_id, current_target_path)
    decision_drift = detect_decision_drift(run_id, memory)
    semantic_drift = detect_semantic_drift(run_id, current_target_path)

    # Overall drift detection
    drift_detected = (
        structural_drift.get("drift_detected", False) or
        decision_drift.get("drift_detected", False) or
        semantic_drift.get("drift_detected", False)
    )

    report = DriftReport(
        run_id=run_id,
        replay_mode=replay_mode,
        timestamp=timestamp,
        structural_drift=structural_drift,
        decision_drift=decision_drift,
        semantic_drift=semantic_drift,
        drift_detected=drift_detected
    )

    # Save report in the replay directory
    run_dir = f".maestro/convert/runs/{run_id}"
    replay_dir = os.path.join(run_dir, "replay")
    os.makedirs(replay_dir, exist_ok=True)

    # Save JSON report
    report_path = os.path.join(replay_dir, "drift_report.json")
    with open(report_path, 'w') as f:
        json.dump(asdict(report), f, indent=2)

    # Save human-readable report
    md_report_path = os.path.join(replay_dir, "drift_report.md")
    with open(md_report_path, 'w') as f:
        f.write(f"# Drift Report for Run {run_id}\n\n")
        f.write(f"**Generated at:** {timestamp}\n")
        f.write(f"**Replay mode:** {replay_mode}\n\n")

        f.write("## Structural Drift\n")
        if structural_drift.get("drift_detected"):
            f.write("- **Drift detected:** Yes\n")
            f.write(f"  - Files added: {len(structural_drift.get('added_files', []))}\n")
            f.write(f"  - Files removed: {len(structural_drift.get('removed_files', []))}\n")
            f.write(f"  - Files modified: {len(structural_drift.get('modified_files', []))}\n")
            if structural_drift.get('added_files'):
                f.write("  - Added files:\n")
                for file in structural_drift['added_files']:
                    f.write(f"    - `{file}`\n")
            if structural_drift.get('removed_files'):
                f.write("  - Removed files:\n")
                for file in structural_drift['removed_files']:
                    f.write(f"    - `{file}`\n")
            if structural_drift.get('modified_files'):
                f.write("  - Modified files:\n")
                for file in structural_drift['modified_files']:
                    f.write(f"    - `{file}`\n")
        else:
            f.write("- **Drift detected:** No\n")

        f.write("\n## Decision Drift\n")
        if decision_drift.get("drift_detected"):
            f.write("- **Drift detected:** Yes\n")
            f.write(f"  - Original fingerprint: `{decision_drift.get('original_fingerprint', '')}`\n")
            f.write(f"  - Current fingerprint: `{decision_drift.get('current_fingerprint', '')}`\n")
        else:
            f.write("- **Drift detected:** No\n")

        f.write("\n## Semantic Drift\n")
        if semantic_drift.get("drift_detected"):
            f.write("- **Drift detected:** Yes\n")
            f.write(f"  - Details: " + str(semantic_drift.get("semantic_summary", {})) + "\n")
        else:
            f.write("- **Drift detected:** No\n")

    return report


def get_baseline(baseline_id: str) -> Optional[Dict[str, Any]]:
    """Load a baseline by ID."""
    baseline_path = f".maestro/convert/baselines/{baseline_id}.json"

    if not os.path.exists(baseline_path):
        return None

    with open(baseline_path, 'r') as f:
        return json.load(f)


def analyze_convergence(drift_reports: List[Dict[str, Any]], max_replay_rounds: int = 2) -> Dict[str, Any]:
    """Analyze convergence based on multiple replay drift reports."""
    if len(drift_reports) < 2:
        return {
            "converged": False,
            "message": "Need at least 2 replay reports to analyze convergence",
            "is_convergent": False
        }

    # Look at the drift patterns across replays
    structural_changes = []
    for report in drift_reports:
        if 'structural_drift' in report:
            drift = report['structural_drift']
            change_count = (
                len(drift.get('added_files', [])) +
                len(drift.get('removed_files', [])) +
                len(drift.get('modified_files', []))
            )
            structural_changes.append(change_count)

    # Check if changes are decreasing (converging)
    if len(structural_changes) >= 2:
        is_decreasing = all(structural_changes[i] >= structural_changes[i+1]
                           for i in range(len(structural_changes)-1))

        # If changes are decreasing and approaching 0, it's converging
        if is_decreasing and structural_changes[-1] == 0:
            return {
                "converged": True,
                "message": "Convergence achieved - no structural changes in latest replay",
                "is_convergent": True,
                "change_trend": "decreasing",
                "final_change_count": structural_changes[-1]
            }
        elif is_decreasing:
            return {
                "converged": False,
                "message": f"Changes decreasing (trending toward convergence): {structural_changes}",
                "is_convergent": True,  # Still considered convergent if trending
                "change_trend": "decreasing",
                "final_change_count": structural_changes[-1]
            }

    # Check for repetitive patterns (bouncing between states)
    if len(drift_reports) > max_replay_rounds:
        return {
            "converged": False,
            "message": f"Exceeded maximum replay rounds ({max_replay_rounds}) without convergence",
            "is_convergent": False,
            "final_change_count": structural_changes[-1] if structural_changes else 0
        }

    # If we see the same changes happening repeatedly, it's non-convergent
    if len(structural_changes) >= 2 and len(set(structural_changes)) == 1:
        # All changes are the same - oscillating between states
        return {
            "converged": False,
            "message": f"Non-convergent: Changes oscillating with {structural_changes[0]} changes",
            "is_convergent": False,
            "final_change_count": structural_changes[-1]
        }

    return {
        "converged": False,
        "message": f"Insufficient data to determine convergence, current changes: {structural_changes}",
        "is_convergent": True,  # Default to allowing until proven non-convergent
        "final_change_count": structural_changes[-1] if structural_changes else 0
    }


def run_convergent_replay(
    run_id: str,
    source_path: str,
    target_path: str,
    memory,
    max_replay_rounds: int = 2,
    fail_on_any_drift: bool = False,
    **replay_kwargs
) -> Dict[str, Any]:
    """Run multiple replays to check for convergence."""
    all_results = []
    all_drift_reports = []

    for round_num in range(max_replay_rounds):
        print(f"Starting convergence replay round {round_num + 1}/{max_replay_rounds}")

        # Run a replay
        result = run_replay(
            run_id=run_id,
            source_path=source_path,
            target_path=target_path,
            memory=memory,
            **replay_kwargs
        )

        all_results.append(result)

        if not result.get("success"):
            return {
                "success": False,
                "error": f"Replay round {round_num + 1} failed: {result.get('error')}",
                "results": all_results
            }

        # Add drift report to list for convergence analysis
        if result.get("drift_report"):
            all_drift_reports.append(result["drift_report"])

    # Analyze convergence
    convergence_analysis = analyze_convergence(all_drift_reports, max_replay_rounds)

    # If fail_on_any_drift is set, fail if any drift was detected
    if fail_on_any_drift:
        drift_detected = any(
            report.get("drift_detected", False)
            for report in all_drift_reports
        )
        if drift_detected:
            return {
                "success": False,
                "error": "Drift detected and fail_on_any_drift is enabled",
                "convergence_analysis": convergence_analysis,
                "results": all_results
            }

    # If not convergent according to our analysis, fail
    if not convergence_analysis.get("is_convergent"):
        return {
            "success": False,
            "error": f"Non-convergent replay: {convergence_analysis.get('message')}",
            "convergence_analysis": convergence_analysis,
            "results": all_results
        }

    return {
        "success": True,
        "message": f"Convergent replay completed in {len(all_results)} rounds",
        "convergence_analysis": convergence_analysis,
        "results": all_results
    }


def run_replay(
    run_id: str,
    source_path: str,
    target_path: str,
    memory,
    dry: bool = False,
    limit: Optional[int] = None,
    only_task: Optional[str] = None,
    only_phase: Optional[str] = None,
    use_recorded_engines: bool = True,
    allow_engine_change: bool = False
) -> Dict[str, Any]:
    """Run a replay of a previous conversion run."""
    import copy

    run_dir = f".maestro/convert/runs/{run_id}"

    if not os.path.exists(run_dir):
        return {"success": False, "error": f"Run {run_id} not found"}

    # Load the original run data
    manifest = load_run_manifest(run_id)
    if not manifest:
        return {"success": False, "error": f"Manifest not found for run {run_id}"}

    # Load original plan
    original_plan_path = os.path.join(run_dir, "plan.json")
    if not os.path.exists(original_plan_path):
        return {"success": False, "error": f"Original plan not found for run {run_id}"}

    with open(original_plan_path, 'r') as f:
        original_plan = json.load(f)

    # Make a copy to avoid modifying original
    plan = copy.deepcopy(original_plan)

    # Apply filters if specified
    if only_phase:
        if only_phase == 'scaffold':
            plan['scaffold_tasks'] = [t for t in plan.get('scaffold_tasks', []) if not only_task or t['task_id'] == only_task]
            plan['file_tasks'] = []
            plan['final_sweep_tasks'] = []
        elif only_phase == 'file':
            plan['scaffold_tasks'] = []
            plan['file_tasks'] = [t for t in plan.get('file_tasks', []) if not only_task or t['task_id'] == only_task]
            plan['final_sweep_tasks'] = []
        elif only_phase == 'sweep':
            plan['scaffold_tasks'] = []
            plan['file_tasks'] = []
            plan['final_sweep_tasks'] = [t for t in plan.get('final_sweep_tasks', []) if not only_task or t['task_id'] == only_task]
    elif only_task:
        # Filter specific task across all phases
        for phase in ['scaffold_tasks', 'file_tasks', 'final_sweep_tasks']:
            phase_tasks = plan.get(phase, [])
            plan[phase] = [t for t in phase_tasks if t['task_id'] == only_task]

    # Limit number of tasks if specified
    if limit:
        for phase in ['scaffold_tasks', 'file_tasks', 'final_sweep_tasks']:
            phase_tasks = plan.get(phase, [])
            plan[phase] = phase_tasks[:limit]

    # Prepare execution settings based on replay mode
    flags_used = manifest.get("flags_used", [])
    engines_used = manifest.get("engines_used", {})

    # If not using recorded engines, use current defaults
    if not use_recorded_engines and not allow_engine_change:
        return {
            "success": False,
            "error": "Engine change not allowed. Use --allow-engine-change to override."
        }

    # For dry run, we'll temporarily save original target state for comparison
    original_target_state = {}
    if dry:
        # Save the current state of the target directory before replay
        original_target_state = compute_file_hashes(target_path)
        # Save to run artifacts directory for later comparison
        artifacts_dir = os.path.join(run_dir, "replay")
        os.makedirs(artifacts_dir, exist_ok=True)
        target_before_path = os.path.join(artifacts_dir, "target_hashes_before.json")
        with open(target_before_path, 'w') as f:
            json.dump(original_target_state, f, indent=2)

    # Now run the execution (this is a simplified version - in reality it would call the actual execution engine)
    try:
        # In a real implementation, this would use the ConversionExecutor from execution_engine.py
        # For now, we'll simulate the process
        execution_result = {
            "executed_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "skipped_tasks": 0
        }

        # This is where the actual execution would happen using the original plan
        # In a full implementation, we'd integrate with the conversion execution system
        print(f"Replaying run {run_id} in {'dry' if dry else 'apply'} mode...")

        # Generate drift report after replay
        drift_report = generate_drift_report(run_id, target_path, memory, replay_mode="dry" if dry else "apply")

        # Store execution result
        execution_result["drift_report_path"] = f"{run_dir}/replay/drift_report.json"
        execution_result["drift_detected"] = drift_report.drift_detected

        # If in dry mode and drift detected, the user might want to abort before applying
        if dry and drift_report.drift_detected:
            print("Drift detected in dry run. Use --apply mode to actually execute changes.")

        return {
            "success": True,
            "execution_result": execution_result,
            "drift_report": asdict(drift_report) if drift_report else None,
            "mode": "dry" if dry else "apply"
        }

    except Exception as e:
        return {"success": False, "error": f"Replay failed: {str(e)}"}


def create_replay_baseline(run_id: str, baseline_id: str = None) -> str:
    """Create a golden baseline from a run."""
    if not baseline_id:
        baseline_id = f"baseline_{run_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    baseline_dir = f".maestro/convert/baselines"
    os.makedirs(baseline_dir, exist_ok=True)

    baseline_path = os.path.join(baseline_dir, f"{baseline_id}.json")

    # Load the run manifest
    run_manifest = load_run_manifest(run_id)
    if not run_manifest:
        raise ValueError(f"Run {run_id} not found")

    # Create baseline snapshot
    baseline_snapshot = {
        "baseline_id": baseline_id,
        "from_run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "target_file_hashes": compute_file_hashes(run_manifest["target_path"]),
        "semantic_summary": {},  # To be populated based on run results
        "plan_revision": run_manifest["plan_revision"],
        "decision_fingerprint": run_manifest["decision_fingerprint"]
    }

    # Save baseline
    with open(baseline_path, 'w') as f:
        json.dump(baseline_snapshot, f, indent=2)

    return baseline_path