"""
Session data model for CLI tool.
Defines the core data structure for storing session information with subtasks.
"""
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any

# Define possible session and subtask statuses
SESSION_STATUSES = {"new", "planned", "in_progress", "interrupted", "failed", "done"}
SUBTASK_STATUSES = {"pending", "in_progress", "done", "error", "interrupted"}


class Subtask:
    """
    Represents a subtask within a session.
    """
    def __init__(
        self,
        id: str,
        title: str,
        description: str,
        planner_model: str,
        worker_model: str,
        status: str,
        summary_file: str,
        categories: Optional[List[str]] = None,
        root_excerpt: Optional[str] = None,
        plan_id: Optional[str] = None
    ):
        self.id = id
        self.title = title
        self.description = description
        self.planner_model = planner_model
        self.worker_model = worker_model
        self.status = status
        self.summary_file = summary_file
        self.categories = categories or []
        self.root_excerpt = root_excerpt
        self.plan_id = plan_id

    def to_dict(self) -> Dict[str, Any]:
        """Convert the subtask to a dictionary representation."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "planner_model": self.planner_model,
            "worker_model": self.worker_model,
            "status": self.status,
            "summary_file": self.summary_file,
            "categories": self.categories,
            "root_excerpt": self.root_excerpt,
            "plan_id": self.plan_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Subtask':
        """Create a Subtask instance from a dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            planner_model=data["planner_model"],
            worker_model=data["worker_model"],
            status=data["status"],
            summary_file=data["summary_file"],
            categories=data.get("categories", []),
            root_excerpt=data.get("root_excerpt"),
            plan_id=data.get("plan_id")
        )


@dataclass
class PlanNode:
    """
    Represents a node in the plan tree for branch support.
    """
    plan_id: str
    parent_plan_id: Optional[str]
    created_at: str
    label: str
    status: str  # "active", "inactive", "dead"
    notes: Optional[str]
    root_snapshot: str  # Combined root task snapshot
    categories_snapshot: List[str]
    subtask_ids: List[str]  # IDs of subtasks belonging to this plan

    def to_dict(self) -> Dict[str, Any]:
        """Convert the PlanNode to a dictionary representation."""
        return {
            "plan_id": self.plan_id,
            "parent_plan_id": self.parent_plan_id,
            "created_at": self.created_at,
            "label": self.label,
            "status": self.status,
            "notes": self.notes,
            "root_snapshot": self.root_snapshot,
            "categories_snapshot": self.categories_snapshot,
            "subtask_ids": self.subtask_ids
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlanNode':
        """Create a PlanNode instance from a dictionary."""
        # Handle backward compatibility for old sessions with separate root fields
        root_snapshot = data.get("root_snapshot", "")
        if not root_snapshot:
            # Try to get from old field names
            root_snapshot = data.get("root_task_snapshot", data.get("root_clean_snapshot", ""))

        return cls(
            plan_id=data["plan_id"],
            parent_plan_id=data.get("parent_plan_id"),
            created_at=data["created_at"],
            label=data["label"],
            status=data["status"],
            notes=data.get("notes"),
            root_snapshot=root_snapshot,
            categories_snapshot=data.get("categories_snapshot", []),
            subtask_ids=data.get("subtask_ids", [])
        )


class Session:
    """
    Represents a session with subtasks.
    """
    def __init__(
        self,
        id: str,
        created_at: str,
        updated_at: str,
        root_task: str,
        subtasks: List[Subtask],
        rules_path: Optional[str],
        status: str,
        root_task_raw: Optional[str] = None,
        root_task_clean: Optional[str] = None,
        root_task_summary: Optional[str] = None,
        root_task_categories: Optional[List[str]] = None,
        root_history: Optional[List[Dict[str, Any]]] = None,
        plans: Optional[List[PlanNode]] = None,
        active_plan_id: Optional[str] = None
    ):
        self.id = id
        self.created_at = created_at
        self.updated_at = updated_at
        self.root_task = root_task
        self.subtasks = subtasks
        self.rules_path = rules_path
        self.status = status
        self.root_task_raw = root_task_raw or root_task
        self.root_task_clean = root_task_clean
        self.root_task_summary = root_task_summary
        self.root_task_categories = root_task_categories or []
        self.root_history = root_history or []
        self.plans = plans or []
        self.active_plan_id = active_plan_id

    def to_dict(self) -> Dict[str, Any]:
        """Convert the session to a dictionary representation."""
        return {
            "id": self.id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "root_task": self.root_task,
            "subtasks": [subtask.to_dict() for subtask in self.subtasks],
            "rules_path": self.rules_path,
            "status": self.status,
            "root_task_raw": self.root_task_raw,
            "root_task_clean": self.root_task_clean,
            "root_task_summary": self.root_task_summary,
            "root_task_categories": self.root_task_categories,
            "root_history": self.root_history,
            "plans": [plan.to_dict() for plan in self.plans] if self.plans else [],
            "active_plan_id": self.active_plan_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        """Create a Session instance from a dictionary."""
        subtasks = [Subtask.from_dict(subtask_data) for subtask_data in data["subtasks"]]

        # Handle backward compatibility for old sessions without new fields
        root_task_raw = data.get("root_task_raw")
        if root_task_raw is None:
            root_task_raw = data.get("root_task", "")

        root_task_clean = data.get("root_task_clean")
        if root_task_clean is None:
            root_task_clean = data.get("root_task", "")

        root_task_summary = data.get("root_task_summary")
        if root_task_summary is None:
            root_task_summary = data.get("root_task_summary", "")

        root_task_categories = data.get("root_task_categories")
        if root_task_categories is None:
            root_task_categories = []

        root_history = data.get("root_history", [])

        plans = data.get("plans", [])
        active_plan_id = data.get("active_plan_id")

        return cls(
            id=data["id"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            root_task=data["root_task"],
            subtasks=subtasks,
            rules_path=data.get("rules_path"),
            status=data["status"],
            root_task_raw=root_task_raw,
            root_task_clean=root_task_clean,
            root_task_summary=root_task_summary,
            root_task_categories=root_task_categories,
            root_history=root_history,
            plans=[PlanNode.from_dict(plan_data) for plan_data in plans] if plans else [],
            active_plan_id=active_plan_id
        )
def load_session(path: str) -> Session:
    '''
    Load a session from the specified JSON file path.
    
    Args:
        path: Path to the session JSON file
        
    Returns:
        Session instance loaded from the file
        
    Raises:
        FileNotFoundError: If the file does not exist
        json.JSONDecodeError: If the file contains invalid JSON
    '''
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return Session.from_dict(data)


def save_session(session: Session, path: str) -> None:
    '''
    Save a session to the specified JSON file path.
    
    Args:
        session: Session instance to save
        path: Path where the session JSON file will be saved
    '''
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(session.to_dict(), f, indent=2)


if __name__ == '__main__':
    import sys
    import os

    if len(sys.argv) != 2:
        print('Usage: python -m session_model <path_to_session_file>')
        sys.exit(1)

    session_path = sys.argv[1]

    # Create a dummy session for testing
    test_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()

    # Create sample subtasks
    sample_subtasks = [
        Subtask(
            id=str(uuid.uuid4()),
            title="Research topic",
            description="Perform initial research on the given topic",
            planner_model="gpt-4",
            worker_model="gpt-3.5-turbo",
            status="done",
            summary_file="/tmp/research_summary.txt"
        ),
        Subtask(
            id=str(uuid.uuid4()),
            title="Write draft",
            description="Write a comprehensive draft based on research",
            planner_model="gpt-4",
            worker_model="gpt-3.5-turbo",
            status="pending",
            summary_file="/tmp/draft_summary.txt"
        )
    ]

    # Create and save session
    session = Session(
        id=test_id,
        created_at=timestamp,
        updated_at=timestamp,
        root_task="Generate a comprehensive report on AI advancements",
        subtasks=sample_subtasks,
        rules_path=None,
        status="in_progress"
    )

    save_session(session, session_path)
    print(f'Session saved to {session_path}')

    # Load and verify session
    loaded_session = load_session(session_path)
    print(f'Session loaded successfully. ID: {loaded_session.id}')
    print(f'Root task: {loaded_session.root_task}')
    print(f'Number of subtasks: {len(loaded_session.subtasks)}')
    print('Confirmation: Session created, saved, and loaded successfully.')

