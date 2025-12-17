"""
Timeline facade module for Maestro TUI.

Provides backend functionality for timeline operations:
- Listing events
- Getting event details
- Replay functionality
- Branch creation
- Event explanation tracking
- Vault integration for timeline events
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime
import os
import json

from maestro.ui_facade.vault import VaultItem, store_evidence


def list_events(scope: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List timeline events.

    Args:
        scope: Optional scope to filter events ('session', 'plan', 'run', etc.)

    Returns:
        List of event dictionaries with keys: id, timestamp, type, summary, risk_marker, etc.
    """
    # For now, return a mock list of events
    # In a real implementation, this would fetch from the timeline storage
    mock_events = [
        {
            "id": "evt_run_1",
            "timestamp": (datetime.now()).isoformat(),
            "type": "run",
            "summary": "Conversion run started",
            "risk_marker": "low",
            "details": "Initial conversion run initiated by user",
            "user_id": "user1",
            "system_impact": "repo/conversion_plan.json",
            "vault_refs": ["vlt_run_start_1", "vlt_plan_init_1"]  # References to vault items
        },
        {
            "id": "evt_checkpoint_1",
            "timestamp": (datetime.now()).isoformat(),
            "type": "checkpoint",
            "summary": "Manual checkpoint created",
            "risk_marker": "medium",
            "details": "User created checkpoint after stage 2",
            "user_id": "user1",
            "system_impact": "plan/checkpoints.json",
            "vault_refs": ["vlt_checkpoint_1", "vlt_semantic_check_1"]
        },
        {
            "id": "evt_decision_1",
            "timestamp": (datetime.now()).isoformat(),
            "type": "decision",
            "summary": "Semantic decision made",
            "risk_marker": "high",
            "details": "User overrode semantic integrity check",
            "user_id": "user1",
            "system_impact": "semantic/decisions.json",
            "vault_refs": ["vlt_semantic_decision_1", "vlt_override_evidence_1"]
        },
        {
            "id": "evt_batch_1",
            "timestamp": (datetime.now()).isoformat(),
            "type": "batch",
            "summary": "Batch job transitioned",
            "risk_marker": "low",
            "details": "Batch job moved from pending to running",
            "user_id": "system",
            "system_impact": "batch/job_queue.json",
            "vault_refs": ["vlt_batch_status_1", "vlt_job_transition_1"]
        },
        {
            "id": "evt_abort_1",
            "timestamp": (datetime.now()).isoformat(),
            "type": "abort",
            "summary": "Run manually aborted",
            "risk_marker": "medium",
            "details": "User manually stopped conversion run",
            "user_id": "user1",
            "system_impact": "run/status.json",
            "vault_refs": ["vlt_abort_reason_1", "vlt_run_status_1"]
        }
    ]

    return mock_events


def get_event(event_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information for a specific event.

    Args:
        event_id: ID of the event to retrieve

    Returns:
        Event dictionary or None if not found
    """
    events = list_events()
    for event in events:
        if event["id"] == event_id:
            return event
    return None


def link_event_to_vault(event_id: str, vault_item_id: str) -> bool:
    """
    Link a timeline event to a vault item.

    Args:
        event_id: ID of the timeline event
        vault_item_id: ID of the vault item to link

    Returns:
        True if successful, False otherwise
    """
    # In a real implementation, this would update the event to include the vault reference
    # For now, we'll just simulate the operation
    event = get_event(event_id)
    if not event:
        return False

    try:
        # Add the vault reference to the event's vault_refs list
        if 'vault_refs' not in event:
            event['vault_refs'] = []
        if vault_item_id not in event['vault_refs']:
            event['vault_refs'].append(vault_item_id)
        return True
    except Exception:
        return False


def get_event_vault_refs(event_id: str) -> List[str]:
    """
    Get vault references for a specific event.

    Args:
        event_id: ID of the event

    Returns:
        List of vault item IDs associated with this event
    """
    event = get_event(event_id)
    if not event:
        return []

    return event.get('vault_refs', [])


def create_timeline_evidence(event_id: str, content: str, description: str) -> Optional[str]:
    """
    Create evidence in the vault linked to a timeline event.

    Args:
        event_id: ID of the timeline event
        content: Content to store as evidence
        description: Description of the evidence

    Returns:
        ID of the created vault item or None if failed
    """
    try:
        # Create a vault item for the evidence
        vault_item = VaultItem(
            id=f"evidence_{event_id}_{int(datetime.now().timestamp())}",
            source_type="human_judgment",
            subtype="text",
            timestamp=datetime.now().isoformat(),
            origin=event_id,
            description=description,
            path="",  # Path will be set by store_evidence
            size=len(content.encode('utf-8')),
            subsystem="tui",  # Or could be "timeline"
            related_entities=[{"type": "timeline_event", "id": event_id}]
        )

        # Store the evidence content
        success = store_evidence(vault_item, content)

        if success:
            # Link the event to this new vault item
            link_event_to_vault(event_id, vault_item.id)
            return vault_item.id
        else:
            return None
    except Exception:
        return None


def replay_from_event(event_id: str, apply: bool = False) -> Dict[str, Any]:
    """
    Replay from a specific event.

    Args:
        event_id: ID of the event to replay from
        apply: If True, apply changes; if False, dry run only

    Returns:
        Result dictionary with status and details
    """
    # Validate event exists
    event = get_event(event_id)
    if not event:
        return {"status": "error", "message": f"Event {event_id} not found"}

    try:
        # In a real implementation, this would replay from the specific event
        # For now, we'll simulate the operation and create evidence
        action = "Applied" if apply else "Dry-run"

        # Create evidence of the replay operation
        replay_content = f"""
        Replay Operation Log
        ===================
        Event ID: {event_id}
        Operation: {action} replay
        Timestamp: {datetime.now().isoformat()}
        Original Event Type: {event.get('type', 'unknown')}
        Original Summary: {event.get('summary', 'N/A')}

        Status: {'Completed' if apply else 'Dry-run completed'}
        """

        evidence_id = create_timeline_evidence(
            event_id,
            replay_content,
            f"Replay operation evidence for event {event_id} ({'apply' if apply else 'dry-run'})"
        )

        result = {
            "status": "success",
            "message": f"{action} replay from event {event_id}",
            "event_id": event_id,
            "apply": apply,
            "timestamp": datetime.now().isoformat()
        }

        if evidence_id:
            result["evidence_id"] = evidence_id

        return result
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to replay from event {event_id}: {str(e)}"
        }


def branch_from_event(event_id: str, reason: str) -> Dict[str, Any]:
    """
    Create a recovery branch from a specific event.

    Args:
        event_id: ID of the event to branch from
        reason: Reason for creating the branch

    Returns:
        Result dictionary with status and details
    """
    # Validate event exists
    event = get_event(event_id)
    if not event:
        return {"status": "error", "message": f"Event {event_id} not found"}

    try:
        # In a real implementation, this would create a new plan/run lineage
        # For now, we'll simulate the operation and create evidence
        branch_id = f"branch_{event_id}_{int(datetime.now().timestamp())}"

        # Create evidence of the branch operation
        branch_content = f"""
        Recovery Branch Creation Log
        ===========================
        Event ID: {event_id}
        Branch ID: {branch_id}
        Reason: {reason}
        Timestamp: {datetime.now().isoformat()}
        Original Event Type: {event.get('type', 'unknown')}
        Original Summary: {event.get('summary', 'N/A')}

        Status: Branch created successfully
        """

        evidence_id = create_timeline_evidence(
            event_id,
            branch_content,
            f"Recovery branch evidence for event {event_id}, reason: {reason}"
        )

        result = {
            "status": "success",
            "message": f"Created recovery branch from event {event_id}",
            "event_id": event_id,
            "reason": reason,
            "branch_id": branch_id,
            "timestamp": datetime.now().isoformat()
        }

        if evidence_id:
            result["evidence_id"] = evidence_id

        return result
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to create branch from event {event_id}: {str(e)}"
        }


def mark_event_explained(event_id: str, note: str) -> Dict[str, Any]:
    """
    Mark an event as 'explained' with a note.

    Args:
        event_id: ID of the event to mark as explained
        note: Explanation note

    Returns:
        Result dictionary with status and details
    """
    # Validate event exists
    event = get_event(event_id)
    if not event:
        return {"status": "error", "message": f"Event {event_id} not found"}

    try:
        # Create evidence of the explanation
        explanation_content = f"""
        Event Explanation
        ================
        Event ID: {event_id}
        Explained at: {datetime.now().isoformat()}
        Explanation Note: {note}
        Original Event Type: {event.get('type', 'unknown')}
        Original Summary: {event.get('summary', 'N/A')}
        Risk Marker: {event.get('risk_marker', 'N/A')}

        This event has been marked as 'explained' by the user.
        """

        evidence_id = create_timeline_evidence(
            event_id,
            explanation_content,
            f"Explanation for event {event_id}: {note}"
        )

        result = {
            "status": "success",
            "message": f"Event {event_id} marked as explained",
            "event_id": event_id,
            "note": note,
            "timestamp": datetime.now().isoformat()
        }

        if evidence_id:
            result["evidence_id"] = evidence_id

        return result
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to mark event {event_id} as explained: {str(e)}"
        }


def get_event_lineage(event_id: str) -> List[Dict[str, Any]]:
    """
    Get the lineage of events that follow the specified event.
    
    Args:
        event_id: ID of the starting event
        
    Returns:
        List of subsequent events
    """
    all_events = list_events()
    
    # Find the starting event
    start_idx = -1
    for i, event in enumerate(all_events):
        if event["id"] == event_id:
            start_idx = i
            break
    
    if start_idx == -1:
        return []
    
    # Return events that come after the starting event
    return all_events[start_idx + 1:]


def get_event_precedence(event_id: str) -> List[Dict[str, Any]]:
    """
    Get the precedence of events that came before the specified event.
    
    Args:
        event_id: ID of the reference event
        
    Returns:
        List of preceding events
    """
    all_events = list_events()
    
    # Find the reference event
    ref_idx = -1
    for i, event in enumerate(all_events):
        if event["id"] == event_id:
            ref_idx = i
            break
    
    if ref_idx == -1:
        return []
    
    # Return events that came before the reference event
    return all_events[:ref_idx]


def get_related_vault_items(event_id: str) -> List[Dict[str, Any]]:
    """
    Get vault items related to a specific timeline event.

    Args:
        event_id: ID of the timeline event

    Returns:
        List of vault items related to this event
    """
    from maestro.ui_facade.vault import list_items, VaultFilter

    # Get vault references for this event
    vault_refs = get_event_vault_refs(event_id)

    # Create a filter to find related items
    # In a real implementation, we would search for items related to this event
    # For now, we'll search by origin or related entities
    related_items = []

    # Search by origin (items with the same origin as the event ID)
    filter_obj = VaultFilter(origin_filter=event_id)
    vault_items = list_items(filters=filter_obj)
    related_items.extend([{
        'id': item.id,
        'source_type': item.source_type,
        'description': item.description,
        'timestamp': item.timestamp,
        'path': item.path
    } for item in vault_items])

    # Also look for items that have this event in their related_entities
    all_items = list_items()
    for item in all_items:
        for entity in item.related_entities:
            if entity.get('id') == event_id:
                related_items.append({
                    'id': item.id,
                    'source_type': item.source_type,
                    'description': item.description,
                    'timestamp': item.timestamp,
                    'path': item.path
                })
                break  # Don't add the same item multiple times

    return related_items


# IMPORT-SAFE: no side effects allowed