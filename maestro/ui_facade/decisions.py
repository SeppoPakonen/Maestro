"""
UI Facade for Decision Operations

This module provides structured data access to conversion decision management
without CLI dependencies.
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import json
import os
from datetime import datetime
import uuid
import hashlib
import threading


@dataclass
class Decision:
    """Represents a conversion decision."""
    id: str
    status: str  # active, superseded, rejected, pending
    description: str
    created_at: str
    last_modified: str
    reason: Optional[str] = None
    original_decision: Optional[str] = None
    override_reason: Optional[str] = None
    affected_plans: List[str] = None
    evidence: Optional[str] = None
    related_evidence: Optional[str] = None

    def __post_init__(self):
        if self.affected_plans is None:
            self.affected_plans = []


@dataclass
class DecisionSummary:
    """Summary of conversion decisions."""
    total_decisions: int
    active: int
    superseded: int
    pending: int
    rejected: int


@dataclass
class OverrideResult:
    """Result of a decision override operation."""
    old_decision_id: str
    new_decision_id: str
    old_fingerprint: str
    new_fingerprint: str
    plan_is_stale: bool
    message: str = ""


class DecisionManager:
    """Manage conversion decisions with override capabilities."""

    def __init__(self):
        self._lock = threading.Lock()
        self.decisions_dir = "./.maestro/convert/decisions"
        os.makedirs(self.decisions_dir, exist_ok=True)

    def _get_decisions_file_path(self) -> str:
        """Get path to the decisions data file."""
        os.makedirs(self.decisions_dir, exist_ok=True)
        return os.path.join(self.decisions_dir, "decisions.json")

    def _load_decisions(self) -> List[Dict[str, Any]]:
        """Load decisions from file, with fallback to initial decisions."""
        decisions_file = self._get_decisions_file_path()

        if os.path.exists(decisions_file):
            try:
                with open(decisions_file, 'r', encoding='utf-8') as f:
                    decisions_data = json.load(f)
                    # Convert dictionaries to Decision objects
                    decisions = []
                    for data in decisions_data:
                        decision = Decision(
                            id=data['id'],
                            status=data['status'],
                            description=data.get('description', data.get('title', '')),
                            created_at=data.get('timestamp', data.get('created_at', datetime.now().isoformat())),
                            last_modified=data.get('last_modified', data.get('timestamp', datetime.now().isoformat())),
                            reason=data.get('reason'),
                            original_decision=data.get('original_decision'),
                            override_reason=data.get('override_reason'),
                            affected_plans=data.get('affected_plans', []),
                            evidence=data.get('evidence'),
                            related_evidence=data.get('related_evidence')
                        )
                        decisions.append(decision)
                    return decisions
            except (json.JSONDecodeError, IOError):
                # If file is corrupted or can't be read, return empty list
                return self._get_initial_decisions_as_objects()
        else:
            # Create with initial decisions if file doesn't exist
            initial_decisions = self._get_initial_decisions_as_objects()
            self._save_decisions_from_objects(initial_decisions)
            return initial_decisions

    def _save_decisions_from_objects(self, decisions: List[Decision]) -> None:
        """Save decisions objects to file."""
        decisions_file = self._get_decisions_file_path()

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(decisions_file), exist_ok=True)

        # Convert Decision objects to dictionaries
        decisions_data = []
        for decision in decisions:
            decisions_data.append({
                'id': decision.id,
                'status': decision.status,
                'description': decision.description,
                'created_at': decision.created_at,
                'last_modified': decision.last_modified,
                'reason': decision.reason,
                'original_decision': decision.original_decision,
                'override_reason': decision.override_reason,
                'affected_plans': decision.affected_plans,
                'evidence': decision.evidence,
                'related_evidence': decision.related_evidence
            })

        with open(decisions_file, 'w', encoding='utf-8') as f:
            json.dump(decisions_data, f, indent=2)

    def _get_initial_decisions_as_objects(self) -> List[Decision]:
        """Get initial decisions as Decision objects."""
        now = datetime.now().isoformat()
        return [
            Decision(
                id="D-001",
                status="active",
                description="Use snake_case for function names in Python conversion",
                created_at=now,
                last_modified=now,
                reason="Python convention is to use snake_case for function names",
                evidence="Python PEP 8 style guide recommends snake_case for function names",
                affected_plans=["plan_function_naming"]
            ),
            Decision(
                id="D-002",
                status="active",
                description="Convert U++ Vector to Python lists with type hints",
                created_at=now,
                last_modified=now,
                reason="Python lists provide similar functionality with better integration",
                evidence="Python lists are the standard data structure for ordered collections",
                affected_plans=["plan_data_structure_conversion"]
            )
        ]

    def list_decisions(self) -> List[Decision]:
        """List all conversion decisions in the memory."""
        with self._lock:
            return self._load_decisions()

    def get_decision(self, decision_id: str) -> Optional[Decision]:
        """Get a specific decision by ID."""
        with self._lock:
            decisions = self._load_decisions()
            for decision in decisions:
                if decision.id == decision_id:
                    return decision
            return None

    def get_decision_summary(self) -> DecisionSummary:
        """Get a summary of decisions."""
        with self._lock:
            decisions = self._load_decisions()
            total = len(decisions)
            active = len([d for d in decisions if d.status == "active"])
            superseded = len([d for d in decisions if d.status == "superseded"])
            pending = len([d for d in decisions if d.status == "pending"])
            rejected = len([d for d in decisions if d.status == "rejected"])

            return DecisionSummary(
                total_decisions=total,
                active=active,
                superseded=superseded,
                pending=pending,
                rejected=rejected
            )

    def override_decision(self, decision_id: str, reason: str, auto_replan: bool = True) -> OverrideResult:
        """
        Override a decision by creating a new version that supersedes the old one.

        Args:
            decision_id: ID of the decision to override
            reason: Reason for the override
            auto_replan: Whether to automatically trigger replan after override

        Returns:
            OverrideResult with details of the operation
        """
        with self._lock:
            decisions = self._load_decisions()

            # Find the original decision
            old_decision_idx = None
            old_decision = None
            for i, decision in enumerate(decisions):
                if decision.id == decision_id:
                    old_decision_idx = i
                    old_decision = decision
                    break

            if not old_decision:
                raise ValueError(f"Decision with ID {decision_id} not found")

            # Generate new decision ID
            new_decision_id = f"D-{uuid.uuid4().hex[:8].upper()}"

            # Calculate fingerprints for before/after comparison
            old_fingerprint = hashlib.md5(json.dumps({
                'id': old_decision.id,
                'status': old_decision.status,
                'description': old_decision.description,
                'created_at': old_decision.created_at,
                'reason': old_decision.reason
            }, sort_keys=True).encode()).hexdigest()

            # Create new decision based on the old one but with override status
            new_decision = Decision(
                id=new_decision_id,
                status="active",  # New decision is active
                description=old_decision.description,  # Keep same description
                created_at=datetime.now().isoformat(),
                last_modified=datetime.now().isoformat(),
                reason=f"Overridden: {reason}",
                original_decision=old_decision.id,
                override_reason=reason,
                affected_plans=old_decision.affected_plans,
                evidence=old_decision.evidence,
                related_evidence=old_decision.related_evidence
            )

            new_fingerprint = hashlib.md5(json.dumps({
                'id': new_decision.id,
                'status': new_decision.status,
                'description': new_decision.description,
                'created_at': new_decision.created_at,
                'reason': new_decision.reason
            }, sort_keys=True).encode()).hexdigest()

            # Update original decision to mark it as superseded
            old_decision.status = "superseded"
            old_decision.last_modified = datetime.now().isoformat()

            # Add the new decision to the list
            decisions.append(new_decision)

            # Update the old decision in place
            decisions[old_decision_idx] = old_decision

            # Save the updated decisions
            self._save_decisions_from_objects(decisions)

            # Determine if plan is now stale (simplified logic)
            plan_is_stale = auto_replan  # If auto-replan is on, plan likely needs updating

            return OverrideResult(
                old_decision_id=decision_id,
                new_decision_id=new_decision_id,
                old_fingerprint=old_fingerprint,
                new_fingerprint=new_fingerprint,
                plan_is_stale=plan_is_stale,
                message=f"Decision {decision_id} overridden with new decision {new_decision_id}"
            )


# Global instance to ensure consistent decision tracking
_decision_manager = DecisionManager()


def list_decisions() -> List[Decision]:
    """List all conversion decisions in the memory."""
    return _decision_manager.list_decisions()


def get_decision(decision_id: str) -> Optional[Decision]:
    """Get a specific decision by ID."""
    return _decision_manager.get_decision(decision_id)


def get_decision_summary() -> DecisionSummary:
    """Get a summary of conversion decisions."""
    return _decision_manager.get_decision_summary()


def override_decision(decision_id: str, reason: str, auto_replan: bool = True) -> OverrideResult:
    """Override a decision by creating a new version that supersedes the old one."""
    return _decision_manager.override_decision(decision_id, reason, auto_replan)