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
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                # If file is corrupted or can't be read, return empty list
                return self._get_initial_decisions()
        else:
            # Create with initial decisions if file doesn't exist
            initial_decisions = self._get_initial_decisions()
            self._save_decisions(initial_decisions)
            return initial_decisions
    
    def _save_decisions(self, decisions: List[Dict[str, Any]]) -> None:
        """Save decisions to file."""
        decisions_file = self._get_decisions_file_path()
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(decisions_file), exist_ok=True)
        
        with open(decisions_file, 'w', encoding='utf-8') as f:
            json.dump(decisions, f, indent=2)
    
    def _get_initial_decisions(self) -> List[Dict[str, Any]]:
        """Get initial decisions for a new project."""
        return [
            {
                "id": "D-001",
                "title": "Use snake_case for function names in Python conversion",
                "status": "active",
                "timestamp": "2023-10-15T10:30:00Z",
                "origin": "planner",
                "reason": "Python convention is to use snake_case for function names",
                "evidence_refs": ["refactor_log_001", "style_guide_001"],
                "impacted_files": ["**/*.py"],
                "superseded_by": None,
                "supersedes": []
            },
            {
                "id": "D-002",
                "title": "Convert U++ Vector to Python lists with type hints",
                "status": "active",
                "timestamp": "2023-10-16T14:22:00Z",
                "origin": "converter",
                "reason": "Python lists provide similar functionality with better integration",
                "evidence_refs": ["conversion_log_002", "performance_test_001"],
                "impacted_files": ["src/**/*.py"],
                "superseded_by": None,
                "supersedes": []
            }
        ]
    
    def list_decisions(self) -> List[Dict[str, Any]]:
        """List all conversion decisions in the memory."""
        with self._lock:
            return self._load_decisions()
    
    def get_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific decision by ID."""
        with self._lock:
            decisions = self._load_decisions()
            for decision in decisions:
                if decision.get("id") == decision_id:
                    return decision
            return None
    
    def override_decision(self, decision_id: str, new_value: str, reason: str, auto_replan: bool = True) -> OverrideResult:
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
        with self._lock:
            decisions = self._load_decisions()
            
            # Find the original decision
            old_decision_idx = None
            old_decision = None
            for i, decision in enumerate(decisions):
                if decision.get("id") == decision_id:
                    old_decision_idx = i
                    old_decision = decision
                    break
            
            if not old_decision:
                raise ValueError(f"Decision with ID {decision_id} not found")
            
            # Generate new decision ID
            new_decision_id = f"D-{uuid.uuid4().hex[:8].upper()}"
            
            # Calculate fingerprints for before/after comparison
            old_fingerprint = hashlib.md5(json.dumps(old_decision, sort_keys=True).encode()).hexdigest()
            
            # Create new decision with the new value
            new_decision = {
                "id": new_decision_id,
                "title": old_decision.get("title", f"Updated: {decision_id}"),
                "status": "active",
                "timestamp": datetime.now().isoformat(),
                "origin": "human_override",
                "reason": reason,
                "value": new_value,  # This is the new value provided by user
                "evidence_refs": old_decision.get("evidence_refs", []),
                "impacted_files": old_decision.get("impacted_files", []),
                "superseded_by": None,
                "supersedes": [decision_id],  # This new decision supersedes the old one
                "override_reason": reason,
                "original_decision_id": decision_id
            }
            
            new_fingerprint = hashlib.md5(json.dumps(new_decision, sort_keys=True).encode()).hexdigest()
            
            # Update original decision to mark it as superseded
            old_decision["superseded_by"] = new_decision_id
            old_decision["status"] = "superseded"
            
            # Add the new decision to the list
            decisions.append(new_decision)
            
            # Update the old decision in place
            decisions[old_decision_idx] = old_decision
            
            # Save the updated decisions
            self._save_decisions(decisions)
            
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


def list_decisions() -> List[Dict[str, Any]]:
    """List all conversion decisions in the memory."""
    return _decision_manager.list_decisions()


def get_decision(decision_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific decision by ID."""
    return _decision_manager.get_decision(decision_id)


def override_decision(decision_id: str, new_value: str, reason: str, auto_replan: bool = True) -> OverrideResult:
    """Override a decision by creating a new version that supersedes the old one."""
    return _decision_manager.override_decision(decision_id, new_value, reason, auto_replan)