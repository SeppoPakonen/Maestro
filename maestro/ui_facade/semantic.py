"""
UI Facade for Semantic Integrity Operations

This module provides structured data access to semantic risk analysis without CLI dependencies.
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import json
import os
from datetime import datetime
from maestro.session_model import Session, load_session
from maestro.main import (
    ConversionPipeline,
    ConversionStage,
    load_conversion_pipeline,
    save_conversion_pipeline
)
from .convert import SemanticFinding, SemanticSummary


def _get_semantic_dir() -> str:
    """Get the semantic analysis directory path."""
    return "./.maestro/convert/semantic"


def _semantic_file_path(pipeline_id: str) -> str:
    """Get the file path for a specific pipeline's semantic findings."""
    semantic_dir = _get_semantic_dir()
    os.makedirs(semantic_dir, exist_ok=True)
    return os.path.join(semantic_dir, f"{pipeline_id}_semantic_findings.json")


def _save_semantic_findings(pipeline_id: str, findings: List[SemanticFinding]) -> None:
    """Save semantic findings to file."""
    file_path = _semantic_file_path(pipeline_id)
    findings_data = []
    for finding in findings:
        findings_data.append({
            'id': finding.id,
            'task_id': finding.task_id,
            'files': finding.files,
            'equivalence_level': finding.equivalence_level,
            'risk_flags': finding.risk_flags,
            'status': finding.status,
            'description': finding.description,
            'evidence_before': finding.evidence_before,
            'evidence_after': finding.evidence_after,
            'decision_reason': finding.decision_reason,
            'checkpoint_id': finding.checkpoint_id,
            'blocks_pipeline': finding.blocks_pipeline
        })
    
    with open(file_path, 'w') as f:
        json.dump(findings_data, f, indent=2)


def _load_semantic_findings(pipeline_id: str) -> List[SemanticFinding]:
    """Load semantic findings from file."""
    file_path = _semantic_file_path(pipeline_id)
    if not os.path.exists(file_path):
        return []
    
    try:
        with open(file_path, 'r') as f:
            findings_data = json.load(f)
        
        findings = []
        for data in findings_data:
            finding = SemanticFinding(
                id=data['id'],
                task_id=data['task_id'],
                files=data['files'],
                equivalence_level=data['equivalence_level'],
                risk_flags=data['risk_flags'],
                status=data['status'],
                description=data['description'],
                evidence_before=data['evidence_before'],
                evidence_after=data['evidence_after'],
                decision_reason=data.get('decision_reason'),
                checkpoint_id=data.get('checkpoint_id'),
                blocks_pipeline=data.get('blocks_pipeline', False)
            )
            findings.append(finding)
        
        return findings
    except Exception:
        return []


def list_semantic_findings(pipeline_id: Optional[str] = None) -> List[SemanticFinding]:
    """
    List all semantic findings for the given pipeline.

    Args:
        pipeline_id: ID of the pipeline to get findings for. If None, uses active pipeline.

    Returns:
        List of semantic findings
    """
    if not pipeline_id:
        # Get the most recent pipeline ID by looking at pipeline files
        import os
        conversion_dir = "./.maestro/convert/pipelines"
        if os.path.exists(conversion_dir):
            pipeline_files = [f for f in os.listdir(conversion_dir) if f.endswith('.json')]
            if pipeline_files:
                # Get the most recently modified file
                pipeline_files.sort(key=lambda x: os.path.getmtime(os.path.join(conversion_dir, x)), reverse=True)
                pipeline_id = pipeline_files[0].replace('.json', '')
    
    if not pipeline_id:
        # Return empty list if no pipeline found
        return []
    
    return _load_semantic_findings(pipeline_id)


def get_semantic_finding(finding_id: str, pipeline_id: Optional[str] = None) -> Optional[SemanticFinding]:
    """
    Get a specific semantic finding by ID.

    Args:
        finding_id: ID of the finding to retrieve
        pipeline_id: ID of the pipeline. If None, uses active pipeline.

    Returns:
        SemanticFinding or None if not found
    """
    if not pipeline_id:
        # Get the most recent pipeline ID
        import os
        conversion_dir = "./.maestro/convert/pipelines"
        if os.path.exists(conversion_dir):
            pipeline_files = [f for f in os.listdir(conversion_dir) if f.endswith('.json')]
            if pipeline_files:
                pipeline_files.sort(key=lambda x: os.path.getmtime(os.path.join(conversion_dir, x)), reverse=True)
                pipeline_id = pipeline_files[0].replace('.json', '')
    
    if not pipeline_id:
        return None
    
    findings = _load_semantic_findings(pipeline_id)
    for finding in findings:
        if finding.id == finding_id:
            return finding
    
    return None


def accept_semantic_finding(finding_id: str, reason: Optional[str] = None, pipeline_id: Optional[str] = None) -> bool:
    """
    Mark a semantic finding as accepted.

    Args:
        finding_id: ID of the finding to accept
        reason: Optional reason for acceptance
        pipeline_id: ID of the pipeline. If None, uses active pipeline.

    Returns:
        True if successful, False otherwise
    """
    if not pipeline_id:
        # Get the most recent pipeline ID
        import os
        conversion_dir = "./.maestro/convert/pipelines"
        if os.path.exists(conversion_dir):
            pipeline_files = [f for f in os.listdir(conversion_dir) if f.endswith('.json')]
            if pipeline_files:
                pipeline_files.sort(key=lambda x: os.path.getmtime(os.path.join(conversion_dir, x)), reverse=True)
                pipeline_id = pipeline_files[0].replace('.json', '')
    
    if not pipeline_id:
        return False

    try:
        findings = _load_semantic_findings(pipeline_id)
        
        # Find the finding and update its status
        updated = False
        for finding in findings:
            if finding.id == finding_id:
                finding.status = "accepted"
                finding.decision_reason = reason or f"Accepted by user at {datetime.now().isoformat()}"
                updated = True
                break
        
        if not updated:
            return False
        
        # Save the updated findings
        _save_semantic_findings(pipeline_id, findings)
        
        # If the finding was blocking a pipeline stage, we may need to unblock it
        # This would require updating the pipeline status as well
        try:
            pipeline = load_conversion_pipeline(pipeline_id)
            
            # Check if this finding was associated with a blocking stage
            for stage in pipeline.stages:
                if (stage.details and 
                    'blocking_semantic_findings' in stage.details and 
                    finding_id in stage.details['blocking_semantic_findings']):
                    
                    # If this was the last blocking finding, unblock the stage
                    stage.details['blocking_semantic_findings'].remove(finding_id)
                    if not stage.details.get('blocking_semantic_findings'):
                        # No more semantic findings blocking this stage
                        if stage.status == "blocked":
                            stage.status = "pending"
                    
                    # Update the pipeline
                    save_conversion_pipeline(pipeline)
                    break
        except Exception:
            # If pipeline update fails, that's OK - just return success for the semantic finding update
            pass
        
        return True
    except Exception:
        return False


def reject_semantic_finding(finding_id: str, reason: str, pipeline_id: Optional[str] = None) -> bool:
    """
    Mark a semantic finding as rejected.

    Args:
        finding_id: ID of the finding to reject
        reason: Reason for rejection
        pipeline_id: ID of the pipeline. If None, uses active pipeline.

    Returns:
        True if successful, False otherwise
    """
    if not reason:
        raise ValueError("Reason is required for rejecting a semantic finding")
    
    if not pipeline_id:
        # Get the most recent pipeline ID
        import os
        conversion_dir = "./.maestro/convert/pipelines"
        if os.path.exists(conversion_dir):
            pipeline_files = [f for f in os.listdir(conversion_dir) if f.endswith('.json')]
            if pipeline_files:
                pipeline_files.sort(key=lambda x: os.path.getmtime(os.path.join(conversion_dir, x)), reverse=True)
                pipeline_id = pipeline_files[0].replace('.json', '')
    
    if not pipeline_id:
        return False

    try:
        findings = _load_semantic_findings(pipeline_id)
        
        # Find the finding and update its status
        updated = False
        for finding in findings:
            if finding.id == finding_id:
                finding.status = "rejected"
                finding.decision_reason = reason
                updated = True
                break
        
        if not updated:
            return False
        
        # Save the updated findings
        _save_semantic_findings(pipeline_id, findings)
        
        # If the finding was blocking a pipeline stage, rejecting it should keep the stage blocked
        # or potentially move it to failed status
        try:
            pipeline = load_conversion_pipeline(pipeline_id)
            
            # Check if this finding was associated with a blocking stage
            for stage in pipeline.stages:
                if (stage.details and 
                    'blocking_semantic_findings' in stage.details and 
                    finding_id in stage.details['blocking_semantic_findings']):
                    
                    # Rejected semantic findings should block the pipeline
                    # Update stage to failed status if this is a critical issue
                    stage.status = "failed"
                    stage.error = f"Semantic risk rejected: {reason}"
                    
                    # Update the pipeline
                    save_conversion_pipeline(pipeline)
                    break
        except Exception:
            # If pipeline update fails, that's OK - just return success for the semantic finding update
            pass
        
        return True
    except Exception:
        return False


def defer_semantic_finding(finding_id: str, pipeline_id: Optional[str] = None) -> bool:
    """
    Mark a semantic finding as deferred (pending further review).

    Args:
        finding_id: ID of the finding to defer
        pipeline_id: ID of the pipeline. If None, uses active pipeline.

    Returns:
        True if successful, False otherwise
    """
    if not pipeline_id:
        # Get the most recent pipeline ID
        import os
        conversion_dir = "./.maestro/convert/pipelines"
        if os.path.exists(conversion_dir):
            pipeline_files = [f for f in os.listdir(conversion_dir) if f.endswith('.json')]
            if pipeline_files:
                pipeline_files.sort(key=lambda x: os.path.getmtime(os.path.join(conversion_dir, x)), reverse=True)
                pipeline_id = pipeline_files[0].replace('.json', '')
    
    if not pipeline_id:
        return False

    try:
        findings = _load_semantic_findings(pipeline_id)
        
        # Find the finding and update its status (deferred findings remain as pending for now)
        updated = False
        for finding in findings:
            if finding.id == finding_id:
                finding.status = "pending"  # Deferred findings remain pending but are noted as deferred
                finding.decision_reason = f"Deferred for later review at {datetime.now().isoformat()}"
                updated = True
                break
        
        if not updated:
            return False
        
        # Save the updated findings
        _save_semantic_findings(pipeline_id, findings)
        
        return True
    except Exception:
        return False


def get_semantic_summary(pipeline_id: Optional[str] = None) -> SemanticSummary:
    """
    Get a summary of semantic risks for the given pipeline.

    Args:
        pipeline_id: ID of the pipeline. If None, uses active pipeline.

    Returns:
        SemanticSummary with risk summary
    """
    if not pipeline_id:
        # Get the most recent pipeline ID
        import os
        conversion_dir = "./.maestro/convert/pipelines"
        if os.path.exists(conversion_dir):
            pipeline_files = [f for f in os.listdir(conversion_dir) if f.endswith('.json')]
            if pipeline_files:
                pipeline_files.sort(key=lambda x: os.path.getmtime(os.path.join(conversion_dir, x)), reverse=True)
                pipeline_id = pipeline_files[0].replace('.json', '')
    
    if not pipeline_id:
        return SemanticSummary(
            total_findings=0,
            high_risk=0,
            medium_risk=0,
            low_risk=0,
            accepted=0,
            rejected=0,
            blocking=0,
            overall_health_score=1.0
        )

    findings = _load_semantic_findings(pipeline_id)
    
    if not findings:
        return SemanticSummary(
            total_findings=0,
            high_risk=0,
            medium_risk=0,
            low_risk=0,
            accepted=0,
            rejected=0,
            blocking=0,
            overall_health_score=1.0
        )
    
    total_findings = len(findings)
    high_risk = len([f for f in findings if f.equivalence_level == "high"])
    medium_risk = len([f for f in findings if f.equivalence_level == "medium"])
    low_risk = len([f for f in findings if f.equivalence_level == "low"])
    accepted = len([f for f in findings if f.status == "accepted"])
    rejected = len([f for f in findings if f.status == "rejected"])
    blocking = len([f for f in findings if f.status == "blocking" or f.blocks_pipeline])
    
    # Calculate health score based on the ratio of acceptable findings
    if total_findings > 0:
        # More accepted findings and fewer critical risks improve health
        # Start with 1.0 and subtract based on risk levels and rejections
        health_score = 1.0
        health_score -= (rejected * 0.1)  # Rejected findings decrease health
        health_score -= (high_risk * 0.15)  # High risk findings decrease health
        health_score -= (medium_risk * 0.05)  # Medium risk findings decrease health
        health_score = max(0.0, health_score)  # Ensure it doesn't go below 0
    else:
        health_score = 1.0
    
    return SemanticSummary(
        total_findings=total_findings,
        high_risk=high_risk,
        medium_risk=medium_risk,
        low_risk=low_risk,
        accepted=accepted,
        rejected=rejected,
        blocking=blocking,
        overall_health_score=health_score
    )


def add_semantic_finding(finding: SemanticFinding, pipeline_id: Optional[str] = None) -> bool:
    """
    Add a new semantic finding to the pipeline.

    Args:
        finding: SemanticFinding to add
        pipeline_id: ID of the pipeline. If None, uses active pipeline.

    Returns:
        True if successful, False otherwise
    """
    if not pipeline_id:
        # Get the most recent pipeline ID
        import os
        conversion_dir = "./.maestro/convert/pipelines"
        if os.path.exists(conversion_dir):
            pipeline_files = [f for f in os.listdir(conversion_dir) if f.endswith('.json')]
            if pipeline_files:
                pipeline_files.sort(key=lambda x: os.path.getmtime(os.path.join(conversion_dir, x)), reverse=True)
                pipeline_id = pipeline_files[0].replace('.json', '')
    
    if not pipeline_id:
        return False

    try:
        # Load existing findings
        findings = _load_semantic_findings(pipeline_id)
        
        # Check if finding already exists
        for existing_finding in findings:
            if existing_finding.id == finding.id:
                # Update existing finding
                idx = findings.index(existing_finding)
                findings[idx] = finding
                break
        else:
            # Add new finding
            findings.append(finding)
        
        # Save the updated findings
        _save_semantic_findings(pipeline_id, findings)
        
        return True
    except Exception:
        return False


def get_blocking_semantic_findings(pipeline_id: Optional[str] = None) -> List[SemanticFinding]:
    """
    Get all semantic findings that are blocking pipeline progression.

    Args:
        pipeline_id: ID of the pipeline. If None, uses active pipeline.

    Returns:
        List of semantic findings that are blocking
    """
    all_findings = list_semantic_findings(pipeline_id)
    blocking_findings = [
        finding for finding in all_findings 
        if finding.status == "blocking" or finding.blocks_pipeline
    ]
    return blocking_findings