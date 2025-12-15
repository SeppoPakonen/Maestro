"""
UI Facade for Convert Pipeline Operations

This module provides structured data access to conversion pipeline information without CLI dependencies.
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import json
import os
from datetime import datetime
import uuid
from maestro.session_model import Session, load_session
from maestro.main import (
    ConversionPipeline,
    ConversionStage,
    load_conversion_pipeline,
    save_conversion_pipeline,
    run_overview_stage,
    run_core_builds_stage,
    run_grow_from_main_stage,
    run_full_tree_check_stage,
    run_refactor_stage,
    get_decisions,
    get_decision_by_id
)


@dataclass
class StageInfo:
    """Information about a conversion stage."""
    name: str
    status: str  # pending, running, blocked, done, failed
    icon: str
    color: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    artifacts: List[str] = None
    description: str = ""
    reason: Optional[str] = None  # For blocked status, explains why

    def __post_init__(self):
        if self.artifacts is None:
            self.artifacts = []


@dataclass
class CheckpointInfo:
    """Information about a checkpoint."""
    id: str
    stage: str
    name: str
    status: str  # pending, approved, rejected, overridden
    created_at: str
    reason: str
    details: str = ""


@dataclass
class PipelineStatus:
    """Status of the entire conversion pipeline."""
    id: str
    name: str
    status: str  # idle, running, blocked, completed
    active_stage: Optional[str] = None
    active_run_id: Optional[str] = None
    stages: List[StageInfo] = None

    def __post_init__(self):
        if self.stages is None:
            self.stages = []


@dataclass
class RunHistory:
    """History of conversion runs."""
    run_id: str
    started_at: str
    completed_at: Optional[str] = None
    status: str = ""  # running, completed, failed, blocked
    stages: List[str] = None
    checkpoints: List[str] = None
    semantic_warnings: int = 0
    arbitration_usage: int = 0

    def __post_init__(self):
        if self.stages is None:
            self.stages = []
        if self.checkpoints is None:
            self.checkpoints = []


@dataclass
class OverrideResult:
    """Result of a decision override operation."""
    old_decision_id: str
    new_decision_id: str
    old_fingerprint: str
    new_fingerprint: str
    plan_is_stale: bool
    message: str = ""


def _get_conversion_dir() -> str:
    """Get the conversion directory path."""
    return "./.maestro/convert/pipelines"


def _find_conversion_pipeline_files(conversion_dir: str = "./.maestro/convert/pipelines") -> List[str]:
    """Find all conversion pipeline JSON files in the specified directory."""
    if not os.path.exists(conversion_dir):
        os.makedirs(conversion_dir, exist_ok=True)
        return []

    pipeline_files = []
    for filename in os.listdir(conversion_dir):
        if filename.endswith('.json'):
            pipeline_files.append(os.path.join(conversion_dir, filename))
    return pipeline_files


def _pipeline_file_path(pipeline_id: str, conversion_dir: str = "./.maestro/convert/pipelines") -> str:
    """Get the file path for a specific pipeline."""
    os.makedirs(conversion_dir, exist_ok=True)
    return os.path.join(conversion_dir, f"{pipeline_id}.json")


def get_pipeline_status(pipeline_id: Optional[str] = None, conversion_dir: str = "./.maestro/convert/pipelines") -> PipelineStatus:
    """
    Get the status of the conversion pipeline.

    Args:
        pipeline_id: ID of the pipeline to retrieve. If None, returns status from all available pipelines.
        conversion_dir: Directory containing pipeline files

    Returns:
        PipelineStatus with current pipeline status information
    """
    if pipeline_id:
        # Load specific pipeline
        pipeline = load_conversion_pipeline(pipeline_id)
        return _convert_pipeline_to_status(pipeline)
    else:
        # Get the most recent pipeline
        pipeline_files = _find_conversion_pipeline_files(conversion_dir)
        if not pipeline_files:
            return PipelineStatus(id="", name="", status="idle")
        
        # Find most recently modified pipeline
        most_recent_file = max(pipeline_files, key=os.path.getmtime)
        pipeline_id = os.path.basename(most_recent_file).replace('.json', '')
        pipeline = load_conversion_pipeline(pipeline_id)
        return _convert_pipeline_to_status(pipeline)


def _convert_pipeline_to_status(pipeline: ConversionPipeline) -> PipelineStatus:
    """Convert ConversionPipeline object to PipelineStatus object."""
    # Determine overall status based on pipeline status and stages
    overall_status = pipeline.status
    if overall_status == "new" and any(stage.status == "running" for stage in pipeline.stages):
        overall_status = "running"
    elif overall_status == "running" and any(stage.status == "failed" for stage in pipeline.stages):
        overall_status = "failed"
    elif overall_status == "running" and any(stage.status == "pending" for stage in pipeline.stages) and not all(stage.status in ["completed", "failed", "skipped"] for stage in pipeline.stages):
        overall_status = "running"
    elif overall_status == "running" and all(stage.status in ["completed", "failed", "skipped"] for stage in pipeline.stages):
        overall_status = "completed"
    elif any(stage.status == "blocked" for stage in pipeline.stages):
        overall_status = "blocked"

    # Convert stages
    stage_infos = []
    for stage in pipeline.stages:
        # Map status to icon and color
        status_icons = {
            "pending": "○",  # Circle
            "running": "↻",  # Running
            "completed": "✓",  # Checkmark
            "failed": "✗",  # Cross
            "blocked": "⚠",  # Warning
            "skipped": "→"  # Skip
        }
        
        status_colors = {
            "pending": "dim",
            "running": "yellow",
            "completed": "green",
            "failed": "red",
            "blocked": "orange",
            "skipped": "blue"
        }
        
        icon = status_icons.get(stage.status, "○")
        color = status_colors.get(stage.status, "dim")
        
        # Get stage description based on name
        descriptions = {
            "overview": "Analyze source for conversion strategy",
            "inventory": "Scan and catalog source files",
            "plan": "Plan conversion approach",
            "core_builds": "Establish core build infrastructure",
            "validate": "Validate conversion artifacts",
            "run": "Execute conversion stages",
            "grow_from_main": "Expand from main entry points",
            "full_tree_check": "Comprehensive tree validation",
            "rehearse": "Dry run without applying changes",
            "promote": "Apply rehearsal results",
            "refactor": "Post-conversion refactoring"
        }
        
        description = descriptions.get(stage.name, f"Process {stage.name}")
        
        stage_info = StageInfo(
            name=stage.name,
            status=stage.status,
            icon=icon,
            color=color,
            start_time=stage.started_at,
            end_time=stage.completed_at,
            artifacts=stage.details.get("artifacts", []) if stage.details else [],
            description=description,
            reason=stage.error  # Use error field to store reason for blocking
        )
        stage_infos.append(stage_info)

    return PipelineStatus(
        id=pipeline.id,
        name=pipeline.name,
        status=overall_status,
        active_stage=pipeline.active_stage,
        stages=stage_infos
    )


def list_stages(pipeline_id: str, conversion_dir: str = "./.maestro/convert/pipelines") -> List[StageInfo]:
    """
    List all stages in the conversion pipeline.

    Args:
        pipeline_id: ID of the pipeline
        conversion_dir: Directory containing pipeline files

    Returns:
        List of stage information
    """
    pipeline = load_conversion_pipeline(pipeline_id)
    stage_infos = []
    for stage in pipeline.stages:
        # Map status to icon and color
        status_icons = {
            "pending": "○",  # Circle
            "running": "↻",  # Running
            "completed": "✓",  # Checkmark
            "failed": "✗",  # Cross
            "blocked": "⚠",  # Warning
            "skipped": "→"  # Skip
        }
        
        status_colors = {
            "pending": "dim",
            "running": "yellow",
            "completed": "green",
            "failed": "red",
            "blocked": "orange",
            "skipped": "blue"
        }
        
        icon = status_icons.get(stage.status, "○")
        color = status_colors.get(stage.status, "dim")
        
        # Get stage description based on name
        descriptions = {
            "overview": "Analyze source for conversion strategy",
            "inventory": "Scan and catalog source files",
            "plan": "Plan conversion approach",
            "core_builds": "Establish core build infrastructure",
            "validate": "Validate conversion artifacts",
            "run": "Execute conversion stages",
            "grow_from_main": "Expand from main entry points",
            "full_tree_check": "Comprehensive tree validation",
            "rehearse": "Dry run without applying changes",
            "promote": "Apply rehearsal results",
            "refactor": "Post-conversion refactoring"
        }
        
        description = descriptions.get(stage.name, f"Process {stage.name}")
        
        stage_info = StageInfo(
            name=stage.name,
            status=stage.status,
            icon=icon,
            color=color,
            start_time=stage.started_at,
            end_time=stage.completed_at,
            artifacts=stage.details.get("artifacts", []) if stage.details else [],
            description=description,
            reason=stage.error  # Use error field to store reason for blocking
        )
        stage_infos.append(stage_info)
    
    return stage_infos


def get_stage_details(pipeline_id: str, stage_name: str, conversion_dir: str = "./.maestro/convert/pipelines") -> Optional[StageInfo]:
    """
    Get detailed information about a specific stage.

    Args:
        pipeline_id: ID of the pipeline
        stage_name: Name of the stage
        conversion_dir: Directory containing pipeline files

    Returns:
        StageInfo with detailed stage information or None if not found
    """
    pipeline = load_conversion_pipeline(pipeline_id)
    for stage in pipeline.stages:
        if stage.name == stage_name:
            # Map status to icon and color
            status_icons = {
                "pending": "○",  # Circle
                "running": "↻",  # Running
                "completed": "✓",  # Checkmark
                "failed": "✗",  # Cross
                "blocked": "⚠",  # Warning
                "skipped": "→"  # Skip
            }
            
            status_colors = {
                "pending": "dim",
                "running": "yellow",
                "completed": "green",
                "failed": "red",
                "blocked": "orange",
                "skipped": "blue"
            }
            
            icon = status_icons.get(stage.status, "○")
            color = status_colors.get(stage.status, "dim")
            
            # Get stage description based on name
            descriptions = {
                "overview": "Analyze source for conversion strategy",
                "inventory": "Scan and catalog source files",
                "plan": "Plan conversion approach",
                "core_builds": "Establish core build infrastructure",
                "validate": "Validate conversion artifacts",
                "run": "Execute conversion stages",
                "grow_from_main": "Expand from main entry points",
                "full_tree_check": "Comprehensive tree validation",
                "rehearse": "Dry run without applying changes",
                "promote": "Apply rehearsal results",
                "refactor": "Post-conversion refactoring"
            }
            
            description = descriptions.get(stage.name, f"Process {stage.name}")
            
            return StageInfo(
                name=stage.name,
                status=stage.status,
                icon=icon,
                color=color,
                start_time=stage.started_at,
                end_time=stage.completed_at,
                artifacts=stage.details.get("artifacts", []) if stage.details else [],
                description=description,
                reason=stage.error  # Use error field to store reason for blocking
            )
    
    return None


def run_stage(pipeline_id: str, stage_name: str, limit: Optional[int] = None, rehearse: bool = False, verbose: bool = False) -> bool:
    """
    Run a specific stage in the conversion pipeline.

    Args:
        pipeline_id: ID of the pipeline
        stage_name: Name of the stage to run
        limit: Optional limit parameter for the stage
        rehearse: Whether to run in rehearse mode (no writes)
        verbose: Whether to show verbose output

    Returns:
        True if successful, False otherwise
    """
    try:
        pipeline = load_conversion_pipeline(pipeline_id)
        
        # Find the stage
        target_stage = None
        for stage in pipeline.stages:
            if stage.name == stage_name:
                target_stage = stage
                break
        
        if not target_stage:
            raise ValueError(f"Stage '{stage_name}' not found in pipeline '{pipeline_id}'")
        
        # Update stage status to running
        target_stage.status = "running"
        target_stage.started_at = datetime.now().isoformat()
        save_conversion_pipeline(pipeline)
        
        # Run the appropriate stage function
        try:
            if stage_name == "overview":
                run_overview_stage(pipeline, target_stage, verbose)
            elif stage_name == "core_builds":
                run_core_builds_stage(pipeline, target_stage, verbose)
            elif stage_name == "grow_from_main":
                run_grow_from_main_stage(pipeline, target_stage, verbose)
            elif stage_name == "full_tree_check":
                run_full_tree_check_stage(pipeline, target_stage, verbose)
            elif stage_name == "refactor":
                run_refactor_stage(pipeline, target_stage, verbose)
            else:
                # For other stages that may not have specific implementations yet
                # We'll simulate execution
                import time
                time.sleep(1)  # Simulate work
                target_stage.status = "completed"
                target_stage.completed_at = datetime.now().isoformat()
        
        except Exception as e:
            target_stage.status = "failed"
            target_stage.error = str(e)
            target_stage.completed_at = datetime.now().isoformat()
            save_conversion_pipeline(pipeline)
            return False
        
        # If we get here, the stage completed successfully
        if target_stage.status != "failed":
            target_stage.status = "completed"
            target_stage.completed_at = datetime.now().isoformat()
        
        save_conversion_pipeline(pipeline)
        return True
        
    except Exception as e:
        # Could not load pipeline or other error
        raise e


def get_checkpoints(pipeline_id: str, conversion_dir: str = "./.maestro/convert/pipelines") -> List[CheckpointInfo]:
    """
    Get all checkpoints in the conversion pipeline.

    Args:
        pipeline_id: ID of the pipeline
        conversion_dir: Directory containing pipeline files

    Returns:
        List of checkpoint information
    """
    checkpoints = []
    try:
        pipeline = load_conversion_pipeline(pipeline_id)

        # This is a simplified implementation - in a real system,
        # checkpoints would be stored in the pipeline data structure
        # For now, we'll simulate them based on pipeline state
        for i, stage in enumerate(pipeline.stages):
            # Create checkpoints for blocked stages
            if stage.status == "blocked":
                checkpoint = CheckpointInfo(
                    id=f"chk_{pipeline.id}_{stage.name}_{i}",
                    stage=stage.name,
                    name=f"Block in {stage.name}",
                    status="pending",
                    created_at=stage.started_at or datetime.now().isoformat(),
                    reason=stage.error or f"Stage {stage.name} is blocked"
                )
                checkpoints.append(checkpoint)

        # Also add any checkpoints that may be explicitly stored in the pipeline's details
        # For this simplified implementation, we'll check if there are any pending decisions in the stages
        for i, stage in enumerate(pipeline.stages):
            if stage.details and stage.details.get("requires_approval"):
                checkpoint = CheckpointInfo(
                    id=f"approval_{pipeline.id}_{stage.name}_{i}",
                    stage=stage.name,
                    name=f"Approval required for {stage.name}",
                    status="pending",
                    created_at=stage.started_at or datetime.now().isoformat(),
                    reason=stage.details.get("approval_reason", f"Manual approval required for {stage.name}")
                )
                checkpoints.append(checkpoint)

    except Exception:
        pass  # If pipeline doesn't exist, return empty list

    return checkpoints


def get_semantic_gates(pipeline_id: str, stage_name: str) -> List[Dict[str, Any]]:
    """
    Get semantic gates that apply to a specific stage.

    Args:
        pipeline_id: ID of the pipeline
        stage_name: Name of the stage

    Returns:
        List of semantic gate information
    """
    # In a real implementation, this would check for semantic differences between stages
    # For now, we'll return empty list as a placeholder
    gates = []
    try:
        pipeline = load_conversion_pipeline(pipeline_id)

        # Check if the stage has associated semantic gates
        for stage in pipeline.stages:
            if stage.name == stage_name and stage.details:
                # Look for semantic gate information in stage details
                semantic_info = stage.details.get("semantic_gates", [])
                for gate in semantic_info:
                    gates.append(gate)

    except Exception:
        pass

    return gates


def reject_checkpoint(pipeline_id: str, checkpoint_id: str) -> bool:
    """
    Reject a checkpoint in the conversion pipeline.

    Args:
        pipeline_id: ID of the pipeline
        checkpoint_id: ID of the checkpoint to reject

    Returns:
        True if successful, False otherwise
    """
    try:
        pipeline = load_conversion_pipeline(pipeline_id)

        # Find the stage that has this checkpoint and mark it as failed
        for stage in pipeline.stages:
            if f"chk_{pipeline.id}_{stage.name}" in checkpoint_id or f"approval_{pipeline.id}_{stage.name}" in checkpoint_id:
                stage.status = "failed"  # Mark stage as failed
                stage.error = "Checkpoint rejected by user"
                break

        save_conversion_pipeline(pipeline)
        return True
    except Exception:
        return False


def override_checkpoint(pipeline_id: str, checkpoint_id: str, reason: str) -> bool:
    """
    Override a checkpoint in the conversion pipeline.

    Args:
        pipeline_id: ID of the pipeline
        checkpoint_id: ID of the checkpoint to override
        reason: Reason for override

    Returns:
        True if successful, False otherwise
    """
    try:
        pipeline = load_conversion_pipeline(pipeline_id)

        # Find the stage that has this checkpoint
        for stage in pipeline.stages:
            if f"chk_{pipeline.id}_{stage.name}" in checkpoint_id or f"approval_{pipeline.id}_{stage.name}" in checkpoint_id:
                # For override, we'll mark the stage as completed but note the override
                stage.status = "completed"  # Mark stage as completed by force
                if stage.details is None:
                    stage.details = {}
                stage.details["override_reason"] = reason
                stage.details["overridden_by_user"] = True
                stage.details["override_timestamp"] = datetime.now().isoformat()
                break

        save_conversion_pipeline(pipeline)
        return True
    except Exception:
        return False


def approve_checkpoint(pipeline_id: str, checkpoint_id: str) -> bool:
    """
    Approve a checkpoint in the conversion pipeline.

    Args:
        pipeline_id: ID of the pipeline
        checkpoint_id: ID of the checkpoint to approve

    Returns:
        True if successful, False otherwise
    """
    try:
        pipeline = load_conversion_pipeline(pipeline_id)
        
        # In a real implementation, this would update the checkpoint status
        # and potentially trigger pipeline continuation
        # For now, we'll update the pipeline to indicate the stage can proceed
        for stage in pipeline.stages:
            if f"chk_{pipeline.id}_{stage.name}" in checkpoint_id:
                stage.status = "pending"  # Unblock the stage
                break
        
        save_conversion_pipeline(pipeline)
        return True
    except Exception:
        return False


def reject_checkpoint(pipeline_id: str, checkpoint_id: str) -> bool:
    """
    Reject a checkpoint in the conversion pipeline.

    Args:
        pipeline_id: ID of the pipeline
        checkpoint_id: ID of the checkpoint to reject

    Returns:
        True if successful, False otherwise
    """
    try:
        # For now, this would mark the associated stage as failed
        # In a real implementation, proper checkpoint rejection logic would be added
        pipeline = load_conversion_pipeline(pipeline_id)
        
        # Find the stage that has this checkpoint
        for stage in pipeline.stages:
            if f"chk_{pipeline.id}_{stage.name}" in checkpoint_id:
                stage.status = "failed"  # Mark stage as failed
                stage.error = "Checkpoint rejected by user"
                break
        
        save_conversion_pipeline(pipeline)
        return True
    except Exception:
        return False


def override_checkpoint(pipeline_id: str, checkpoint_id: str, reason: str) -> bool:
    """
    Override a checkpoint in the conversion pipeline.

    Args:
        pipeline_id: ID of the pipeline
        checkpoint_id: ID of the checkpoint to override
        reason: Reason for override

    Returns:
        True if successful, False otherwise
    """
    try:
        pipeline = load_conversion_pipeline(pipeline_id)
        
        # Find the stage that has this checkpoint
        for stage in pipeline.stages:
            if f"chk_{pipeline.id}_{stage.name}" in checkpoint_id:
                stage.status = "completed"  # Mark stage as completed by force
                stage.details = {"override_reason": reason, "overridden_by_user": True}
                break
        
        save_conversion_pipeline(pipeline)
        return True
    except Exception:
        return False


def list_run_history(pipeline_id: str, conversion_dir: str = "./.maestro/convert/pipelines") -> List[RunHistory]:
    """
    List the history of conversion runs.

    Args:
        pipeline_id: ID of the pipeline
        conversion_dir: Directory containing pipeline files

    Returns:
        List of run history information
    """
    # For now, we'll return a simulated history based on pipeline status
    # In a real implementation, this would load from run history files
    histories = []

    try:
        pipeline = load_conversion_pipeline(pipeline_id)

        # For this implementation, we'll just return the current pipeline's info
        # as a single run history item
        history = RunHistory(
            run_id=pipeline.id,
            started_at=pipeline.created_at,
            completed_at=pipeline.updated_at if pipeline.status in ["completed", "failed"] else None,
            status=pipeline.status,
            stages=[stage.name for stage in pipeline.stages],
            checkpoints=[],
            semantic_warnings=0,  # Placeholder - would come from actual run data
            arbitration_usage=0   # Placeholder - would come from actual run data
        )

        # Add some simulated checkpoint information
        for stage in pipeline.stages:
            if stage.status == "blocked":
                history.checkpoints.append(stage.name)
                history.semantic_warnings += 1  # Count blocked stages as warnings

        histories.append(history)

    except Exception:
        pass  # If pipeline doesn't exist, return empty list

    return histories


def get_run_details(run_id: str, conversion_dir: str = "./.maestro/convert/pipelines") -> Optional[RunHistory]:
    """
    Get details of a specific conversion run.

    Args:
        run_id: ID of the run
        conversion_dir: Directory containing pipeline files

    Returns:
        RunHistory with run details or None if not found
    """
    try:
        # Look for a pipeline with the given run_id
        pipelines_dir = conversion_dir
        pipeline_files = _find_conversion_pipeline_files(pipelines_dir)

        for pipeline_file in pipeline_files:
            pipeline_id = os.path.basename(pipeline_file).replace('.json', '')
            if pipeline_id == run_id:
                pipeline = load_conversion_pipeline(pipeline_id)

                history = RunHistory(
                    run_id=pipeline.id,
                    started_at=pipeline.created_at,
                    completed_at=pipeline.updated_at if pipeline.status in ["completed", "failed"] else None,
                    status=pipeline.status,
                    stages=[stage.name for stage in pipeline.stages],
                    checkpoints=[],
                    semantic_warnings=0,
                    arbitration_usage=0
                )

                # Add checkpoint information
                for stage in pipeline.stages:
                    if stage.status == "blocked":
                        history.checkpoints.append(stage.name)
                        history.semantic_warnings += 1

                return history
    except Exception:
        pass

    return None


def get_active_run_id(pipeline_id: str) -> Optional[str]:
    """
    Get the active run ID for the pipeline.

    Args:
        pipeline_id: ID of the pipeline

    Returns:
        Active run ID if any, otherwise None
    """
    try:
        pipeline = load_conversion_pipeline(pipeline_id)
        # For now, we'll return the pipeline ID as the run ID
        # In a real implementation, this would track separate run IDs
        return pipeline.id
    except Exception:
        return None


# Memory-related functions for the Conversion Memory Browser
def list_decisions() -> List[Dict[str, Any]]:
    """
    List all conversion decisions in the memory.

    Returns:
        List of decision dictionaries with id, title, status, etc.
    """
    from .decisions import list_decisions as decisions_list
    try:
        decisions = decisions_list()
        return decisions if decisions else []
    except Exception as e:
        print(f"Error getting decisions: {e}")
        return []


def get_decision(decision_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific decision by ID.

    Args:
        decision_id: ID of the decision to retrieve

    Returns:
        Decision dictionary or None if not found
    """
    from .decisions import get_decision as get_specific_decision
    try:
        decision = get_specific_decision(decision_id)
        return decision
    except Exception as e:
        print(f"Error getting decision {decision_id}: {e}")
        return None


def override_decision(decision_id: str, new_value: str, reason: str, auto_replan: bool = True) -> OverrideResult:
    """
    Override a decision by creating a new version that supersedes the old one.

    Args:
        decision_id: ID of the decision to override
        new_value: New decision content/value
        reason: Reason for the override
        auto_replan: Whether to automatically trigger replan after override

    Returns:
        OverrideResult with details of the operation
    """
    from .decisions import override_decision as decisions_override
    try:
        result = decisions_override(decision_id, new_value, reason, auto_replan)
        return result
    except Exception as e:
        raise e


def list_conventions() -> List[Dict[str, Any]]:
    """
    List all conversion conventions in the memory.

    Returns:
        List of convention dictionaries
    """
    from maestro.main import get_conventions  # Import the function from main module
    try:
        conventions = get_conventions()
        result = []
        if isinstance(conventions, dict):
            # Convert the top-level conventions dict to individual convention entries
            # This is a simplified approach - in a real implementation, this would handle the structure differently
            for key, value in conventions.items():
                if key == 'naming' or key == 'formatting' or key == 'idiomatic_patterns':
                    if isinstance(value, dict):
                        for subkey, subvalue in value.items():
                            result.append({
                                'id': f'conv_{key}_{subkey}',
                                'title': f'{key.title()} - {subkey.replace("_", " ").title()}',
                                'status': 'active',
                                'timestamp': datetime.now().isoformat(),
                                'origin': 'system',
                                'rule': str(subvalue) if not isinstance(subvalue, (list, dict)) else str(subvalue)[:100],
                                'scope': 'project',
                                'enforcement_status': 'manual'
                            })
                    elif isinstance(value, list):
                        for i, item in enumerate(value):
                            result.append({
                                'id': f'conv_{key}_{i}',
                                'title': f'{key.title()} - Item {i+1}',
                                'status': 'active',
                                'timestamp': datetime.now().isoformat(),
                                'origin': 'system',
                                'rule': str(item)[:100],
                                'scope': 'project',
                                'enforcement_status': 'manual'
                            })
        return result
    except Exception as e:
        print(f"Error getting conventions: {e}")
        return []


def list_glossary() -> List[Dict[str, Any]]:
    """
    List all glossary entries in the memory.

    Returns:
        List of glossary dictionaries
    """
    # In a real implementation, this would load from a glossary file
    # For now, returning a placeholder
    try:
        # This would typically load from the project (e.g., glossary.json)
        # For now, we'll return some example entries
        return [
            {
                'id': 'gloss_001',
                'title': 'U++ Vector to Python List',
                'status': 'active',
                'timestamp': datetime.now().isoformat(),
                'origin': 'converter',
                'source_concept': 'Upp::Vector<T>',
                'target_concept': 'Python list',
                'notes': 'Converted using to_std_vector() method when possible',
                'confidence': 0.95
            },
            {
                'id': 'gloss_002',
                'title': 'U++ Pick to Python Transfer',
                'status': 'active',
                'timestamp': datetime.now().isoformat(),
                'origin': 'converter',
                'source_concept': 'Upp::Pick',
                'target_concept': 'Python object reference transfer',
                'notes': 'Converted using move semantics simulation',
                'confidence': 0.85
            }
        ]
    except Exception as e:
        print(f"Error getting glossary: {e}")
        return []


def list_open_issues() -> List[Dict[str, Any]]:
    """
    List all open issues in the memory.

    Returns:
        List of open issue dictionaries
    """
    from maestro.main import get_open_issues  # Import the function from main module
    try:
        issues = get_open_issues()
        result = []
        for i, issue in enumerate(issues):
            result.append({
                'id': issue.get('id', f'issue_{i:03d}'),
                'title': issue.get('title', ''),
                'status': 'open',
                'timestamp': datetime.now().isoformat(),
                'origin': 'analyzer',
                'severity': issue.get('severity', 'medium'),
                'blocking': issue.get('type', '') == 'blocking',
                'files': issue.get('files', [])
            })
        return result
    except Exception as e:
        print(f"Error getting open issues: {e}")
        return []


def list_task_summaries(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    List task summaries in the memory.

    Args:
        limit: Optional limit on number of summaries to return

    Returns:
        List of task summary dictionaries
    """
    # For now, this returns a placeholder list
    # In a real implementation, this would load from the project's history
    try:
        # This would typically load from task history files
        summaries = [
            {
                'id': 'task_001',
                'title': 'Initial codebase scan and analysis',
                'status': 'completed',
                'timestamp': datetime.now().isoformat(),
                'origin': 'planner',
                'task_id': 'task_001',
                'files_touched': ['src/main.cpp', 'src/utils.cpp'],
                'outcome': 'Identified 23 files for conversion',
                'warnings': ['Found 2 deprecated functions'],
                'errors': [],
                'semantic_notes': ['Detected U++ specific patterns']
            },
            {
                'id': 'task_002',
                'title': 'Convert core data structures',
                'status': 'completed',
                'timestamp': datetime.now().isoformat(),
                'origin': 'converter',
                'task_id': 'task_002',
                'files_touched': ['src/vector.cpp', 'src/map.cpp'],
                'outcome': 'Converted 2 core data structures',
                'warnings': [],
                'errors': [],
                'semantic_notes': ['Maintained API compatibility']
            }
        ]
        if limit:
            summaries = summaries[:limit]
        return summaries
    except Exception as e:
        print(f"Error getting task summaries: {e}")
        return []


def get_summary(task_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific task summary by task ID.

    Args:
        task_id: ID of the task summary to retrieve

    Returns:
        Task summary dictionary or None if not found
    """
    try:
        summaries = list_task_summaries()
        for summary in summaries:
            if summary.get('task_id') == task_id:
                return summary
        return None
    except Exception as e:
        print(f"Error getting summary for task {task_id}: {e}")
        return None