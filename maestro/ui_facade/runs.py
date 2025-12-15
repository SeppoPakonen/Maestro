"""
Runs Facade - Provides backend functionality for run history, replay, and baselines
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class RunSummary:
    """Represents a summary of a single run"""
    run_id: str
    timestamp: datetime
    mode: str  # normal, rehearse, replay
    status: str  # ok, drift, blocked
    baseline_tag: Optional[str]
    plan_revision: Optional[str] = None
    decision_fingerprint: Optional[str] = None
    playbook_hash: Optional[str] = None
    engines_used: Optional[List[str]] = None
    checkpoints_hit: Optional[int] = None
    semantic_warnings_count: Optional[int] = None
    arbitration_usage_count: Optional[int] = None


@dataclass
class DriftInfo:
    """Describes drift between runs"""
    structural_drift: Dict[str, Any]  # files changed, added, removed
    decision_drift: Dict[str, Any]    # decision fingerprint differences
    semantic_drift: Dict[str, Any]    # semantic summary and flags


@dataclass
class RunManifest:
    """Complete manifest of a run including all artifacts"""
    run_id: str
    plan: Any  # The original plan used
    memory: Any  # The memory state at the time of the run
    decisions: Any  # Decisions made during the run
    artifacts: Dict[str, Any]  # Files and outputs
    metadata: Dict[str, Any]  # Additional metadata


def list_runs() -> List[RunSummary]:
    """
    List all past runs (conversion + refactor)
    
    Returns:
        List of run summaries with id, timestamp, mode, status, and baseline tag
    """
    # This would eventually connect to persistent storage
    # For now, returning mock data for testing
    return [
        RunSummary(
            run_id="run_a1b2c3d4",
            timestamp=datetime.now(),
            mode="normal",
            status="ok",
            baseline_tag=None,
            plan_revision="v1.2.3",
            decision_fingerprint="f1e2d3c4b5a6",
            playbook_hash="h1i2j3k4l5m6",
            engines_used=["engine_alpha", "engine_beta"],
            checkpoints_hit=15,
            semantic_warnings_count=2,
            arbitration_usage_count=3
        ),
        RunSummary(
            run_id="run_e5f6g7h8",
            timestamp=datetime.now(),
            mode="rehearse",
            status="drift",
            baseline_tag="baseline_prod",
            plan_revision="v1.2.4",
            decision_fingerprint="f1e2d3c4b5a7",
            playbook_hash="h1i2j3k4l5m6",
            engines_used=["engine_alpha", "engine_beta"],
            checkpoints_hit=18,
            semantic_warnings_count=5,
            arbitration_usage_count=4
        ),
        RunSummary(
            run_id="run_i9j0k1l2",
            timestamp=datetime.now(),
            mode="replay",
            status="ok",
            baseline_tag=None,
            plan_revision="v1.2.3",
            decision_fingerprint="f1e2d3c4b5a6",
            playbook_hash="h1i2j3k4l5m6",
            engines_used=["engine_alpha", "engine_beta"],
            checkpoints_hit=15,
            semantic_warnings_count=2,
            arbitration_usage_count=3
        )
    ]


def get_run(run_id: str) -> Optional[RunSummary]:
    """
    Get details for a specific run
    
    Args:
        run_id: Unique identifier for the run
        
    Returns:
        Run summary or None if not found
    """
    runs = list_runs()
    for run in runs:
        if run.run_id == run_id:
            return run
    return None


def get_run_manifest(run_id: str) -> Optional[RunManifest]:
    """
    Get the complete manifest for a run
    
    Args:
        run_id: Unique identifier for the run
        
    Returns:
        Complete run manifest or None if not found
    """
    # This would fetch the full run data from storage
    run = get_run(run_id)
    if not run:
        return None
        
    return RunManifest(
        run_id=run.run_id,
        plan={"revision": run.plan_revision},
        memory={},
        decisions={},
        artifacts={},
        metadata={
            "timestamp": run.timestamp,
            "mode": run.mode,
            "status": run.status
        }
    )


def replay_run(run_id: str, apply: bool = False, override_drift_threshold: bool = False) -> Dict[str, Any]:
    """
    Replay a run deterministically

    Args:
        run_id: The run to replay
        apply: Whether to apply changes (dry run if False)
        override_drift_threshold: Whether to override drift threshold checks

    Returns:
        Result of the replay operation
    """
    run = get_run(run_id)
    if not run:
        raise ValueError(f"Run {run_id} not found")

    # Load the original run manifest (plan, memory, decisions)
    manifest = get_run_manifest(run_id)
    if not manifest:
        raise ValueError(f"Run manifest for {run_id} not found")

    # Check for drift thresholds if applying changes
    drift_detected = False
    drift_details = {}

    # This would be where we actually compare the replay results with the original
    # For now, we'll simulate it with a mock check
    if apply and not override_drift_threshold:
        # Check if the run has significant drift from any baseline
        # In a real implementation, this would run the actual replay and measure drift
        # For now, using mock logic
        drift_detected = False  # In a real implementation, this would be computed

        if drift_detected and not override_drift_threshold:
            return {
                "success": False,
                "run_id": run_id,
                "mode": "replay",
                "apply": apply,
                "drift_detected": True,
                "drift_details": drift_details,
                "message": f"Replay blocked due to significant drift detected. Use override to proceed.",
                "requires_override": True
            }

    # In a real implementation, this would:
    # 1. Load the original plan, memory, and decisions from the manifest
    # 2. Set up the same execution environment
    # 3. Re-execute using the same inputs
    # 4. Compare results for drift detection
    # 5. Apply changes to filesystem only if apply=True

    return {
        "success": True,
        "run_id": run_id,
        "mode": "replay",
        "apply": apply,
        "drift_detected": drift_detected,
        "drift_details": drift_details,
        "message": f"Replayed run {run_id} successfully{' with apply' if apply else ' dry-run'}"
    }


def diff_runs(run_id: str, baseline_id: str) -> Optional[DriftInfo]:
    """
    Compare two runs to detect drift
    
    Args:
        run_id: The run to compare
        baseline_id: The baseline run to compare against
        
    Returns:
        Drift information or None if comparison fails
    """
    run = get_run(run_id)
    baseline = get_run(baseline_id)
    
    if not run or not baseline:
        return None
    
    # In a real implementation, this would compare artifact outputs
    # For now, returning mock data
    return DriftInfo(
        structural_drift={
            "files_changed": [],
            "files_added": [],
            "files_removed": []
        },
        decision_drift={
            "fingerprint_delta": "identical" if run.decision_fingerprint == baseline.decision_fingerprint else "different",
            "decisions_different": []
        },
        semantic_drift={
            "summary": "No significant semantic differences detected",
            "flags": []
        }
    )


def set_baseline(run_id: str) -> Dict[str, Any]:
    """
    Mark a run as a baseline
    
    Args:
        run_id: The run to mark as baseline
        
    Returns:
        Result of the operation
    """
    run = get_run(run_id)
    if not run:
        raise ValueError(f"Run {run_id} not found")
    
    # In a real implementation, this would update persistent storage
    # For now, just returning a success message
    return {
        "success": True,
        "run_id": run_id,
        "message": f"Run {run_id} marked as baseline"
    }