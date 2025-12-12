"""
Session data model for CLI tool.
Defines the core data structure for storing session information with subtasks.
"""
import json
import uuid
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
        summary_file: str
    ):
        self.id = id
        self.title = title
        self.description = description
        self.planner_model = planner_model
        self.worker_model = worker_model
        self.status = status
        self.summary_file = summary_file
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the subtask to a dictionary representation."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "planner_model": self.planner_model,
            "worker_model": self.worker_model,
            "status": self.status,
            "summary_file": self.summary_file
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
            summary_file=data["summary_file"]
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
        status: str
    ):
        self.id = id
        self.created_at = created_at
        self.updated_at = updated_at
        self.root_task = root_task
        self.subtasks = subtasks
        self.rules_path = rules_path
        self.status = status
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the session to a dictionary representation."""
        return {
            "id": self.id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "root_task": self.root_task,
            "subtasks": [subtask.to_dict() for subtask in self.subtasks],
            "rules_path": self.rules_path,
            "status": self.status
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        """Create a Session instance from a dictionary."""
        subtasks = [Subtask.from_dict(subtask_data) for subtask_data in data["subtasks"]]
        return cls(
            id=data["id"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            root_task=data["root_task"],
            subtasks=subtasks,
            rules_path=data.get("rules_path"),
            status=data["status"]
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

