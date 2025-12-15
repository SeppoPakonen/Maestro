"""
Arbitration UI Facade - Backend interface for arbitration arena
"""
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class ArbitrationStatus(Enum):
    PENDING = "pending"
    DECIDED = "decided"
    BLOCKED = "blocked"


class SemanticEquivalence(Enum):
    EQUIVALENT = "equivalent"
    SIMILAR = "similar"
    DIFFERENT = "different"
    CONFLICTING = "conflicting"


@dataclass
class ArbitrationTask:
    """Represents an arbitrated task."""
    id: str
    phase: str  # convert, refactor, sweep
    status: ArbitrationStatus
    winner: Optional[str] = None  # engine name that won, if decided


@dataclass
class Candidate:
    """Represents a candidate output from an engine."""
    engine: str  # qwen, claude, gemini, codex, etc
    score: Optional[float] = None
    semantic_equivalence: Optional[SemanticEquivalence] = None
    validation_passed: bool = True
    flags: List[str] = None
    files_written: List[str] = None
    policy_used: Optional[str] = None
    validation_output: Optional[str] = None

    def __post_init__(self):
        if self.flags is None:
            self.flags = []
        if self.files_written is None:
            self.files_written = []


@dataclass
class ArbitrationData:
    """Complete arbitration information for a task."""
    task_id: str
    phase: str
    status: ArbitrationStatus
    current_winner: Optional[str] = None
    judge_output: Optional[str] = None
    decision_rationale: Optional[str] = None
    confidence: List[str] = None
    candidates: List[Candidate] = None

    def __post_init__(self):
        if self.confidence is None:
            self.confidence = []
        if self.candidates is None:
            self.candidates = []


def list_arbitrated_tasks(session_id: str) -> List[ArbitrationTask]:
    """
    List all tasks that were run with arbitration.

    Args:
        session_id: ID of the session to query

    Returns:
        List of arbitrated tasks
    """
    # This would connect to the actual backend/database in a real implementation
    # For now, return placeholder data
    try:
        from maestro.main import get_session_arbitrated_tasks

        # Get real data from the core system
        tasks_data = get_session_arbitrated_tasks(session_id)
        tasks = []
        for task_data in tasks_data:
            status_enum = ArbitrationStatus(task_data.get('status', 'pending'))
            tasks.append(ArbitrationTask(
                id=task_data['id'],
                phase=task_data.get('phase', 'unknown'),
                status=status_enum,
                winner=task_data.get('winner')
            ))
        return tasks
    except ImportError:
        # If the main module isn't available, return mock data for testing
        return [
            ArbitrationTask(
                id="task_arb_001",
                phase="convert",
                status=ArbitrationStatus.PENDING,
                winner=None
            ),
            ArbitrationTask(
                id="task_arb_002",
                phase="refactor",
                status=ArbitrationStatus.DECIDED,
                winner="claude"
            ),
            ArbitrationTask(
                id="task_arb_003",
                phase="sweep",
                status=ArbitrationStatus.BLOCKED,
                winner=None
            )
        ]


def get_arbitration(task_id: str) -> ArbitrationData:
    """
    Get detailed arbitration information for a specific task.

    Args:
        task_id: ID of the arbitrated task

    Returns:
        Arbitration data for the task
    """
    # This would connect to the actual backend/database in a real implementation
    try:
        from maestro.main import get_arbitration_task_details

        # Get real data from the core system
        data = get_arbitration_task_details(task_id)
        if data:
            status_enum = ArbitrationStatus(data.get('status', 'pending'))
            return ArbitrationData(
                task_id=task_id,
                phase=data.get('phase', 'unknown'),
                status=status_enum,
                current_winner=data.get('winner'),
                judge_output=data.get('judge_output'),
                decision_rationale=data.get('decision_rationale'),
                confidence=data.get('confidence', []),
                candidates=_convert_candidates(data.get('candidates', []))
            )
        else:
            # Return empty data if task not found
            return ArbitrationData(task_id=task_id, phase='unknown', status=ArbitrationStatus.PENDING)
    except ImportError:
        # If the main module isn't available, return mock data for testing
        return ArbitrationData(
            task_id=task_id,
            phase="convert",
            status=ArbitrationStatus.PENDING,
            current_winner=None,
            judge_output="Judge engine output would appear here...",
            decision_rationale="Decision rationale would appear here...",
            confidence=["high semantic similarity", "low risk changes"],
            candidates=[
                Candidate(
                    engine="qwen",
                    score=0.85,
                    semantic_equivalence=SemanticEquivalence.SIMILAR,
                    validation_passed=True,
                    flags=["large_diff"],
                    files_written=["src/file1.py", "src/file2.py"],
                    policy_used="strict_validation"
                ),
                Candidate(
                    engine="claude",
                    score=0.92,
                    semantic_equivalence=SemanticEquivalence.EQUIVALENT,
                    validation_passed=True,
                    flags=[],
                    files_written=["src/file1.py", "src/file2.py", "tests/test_file1.py"],
                    policy_used="strict_validation"
                ),
                Candidate(
                    engine="gemini",
                    score=0.78,
                    semantic_equivalence=SemanticEquivalence.SIMILAR,
                    validation_passed=False,
                    flags=["validation_failed", "risk_warning"],
                    files_written=["src/file1.py"],
                    policy_used="strict_validation",
                    validation_output="Validation errors occurred..."
                )
            ]
        )


def _convert_candidates(candidate_data_list) -> List[Candidate]:
    """Helper to convert raw data to Candidate objects."""
    candidates = []
    for data in candidate_data_list:
        equiv_value = data.get('semantic_equivalence')
        if equiv_value:
            try:
                equiv_enum = SemanticEquivalence(equiv_value)
            except ValueError:
                equiv_enum = None
        else:
            equiv_enum = None
            
        candidates.append(Candidate(
            engine=data['engine'],
            score=data.get('score'),
            semantic_equivalence=equiv_enum,
            validation_passed=data.get('validation_passed', True),
            flags=data.get('flags', []),
            files_written=data.get('files_written', []),
            policy_used=data.get('policy_used'),
            validation_output=data.get('validation_output')
        ))
    return candidates


def list_candidates(task_id: str) -> List[Candidate]:
    """
    List all candidates for a given arbitrated task.
    
    Args:
        task_id: ID of the arbitrated task
        
    Returns:
        List of candidates
    """
    # Get the full arbitration data and extract candidates
    arbitration_data = get_arbitration(task_id)
    return arbitration_data.candidates


def get_candidate(task_id: str, engine: str) -> Candidate:
    """
    Get specific candidate information for a task.
    
    Args:
        task_id: ID of the arbitrated task
        engine: Name of the engine
        
    Returns:
        Candidate information
    """
    candidates = list_candidates(task_id)
    for candidate in candidates:
        if candidate.engine.lower() == engine.lower():
            return candidate
    
    # If not found, raise an exception
    raise ValueError(f"No candidate found for engine '{engine}' in task '{task_id}'")


def choose_winner(task_id: str, engine: str, reason: str) -> bool:
    """
    Manually select a winner for an arbitrated task.

    Args:
        task_id: ID of the arbitrated task
        engine: Name of the engine to select as winner
        reason: Human-readable reason for the selection

    Returns:
        True if successful, False otherwise
    """
    # This would connect to the actual backend/database in a real implementation
    try:
        from maestro.main import set_arbitration_winner

        # Call the core system to make the selection
        success = set_arbitration_winner(task_id, engine, reason)
        return success
    except ImportError:
        # If the main module isn't available, simulate success for testing
        print(f"[SIMULATION] Selected {engine} as winner for task {task_id} with reason: {reason}")
        return True


def reject_candidate(task_id: str, engine: str, reason: str) -> bool:
    """
    Mark a candidate as rejected with a reason.

    Args:
        task_id: ID of the arbitrated task
        engine: Name of the engine to reject
        reason: Human-readable reason for rejection

    Returns:
        True if successful, False otherwise
    """
    # This would connect to the actual backend/database in a real implementation
    try:
        from maestro.main import reject_arbitration_candidate

        # Call the core system to reject the candidate
        success = reject_arbitration_candidate(task_id, engine, reason)
        return success
    except ImportError:
        # If the main module isn't available, simulate success for testing
        print(f"[SIMULATION] Rejected {engine} for task {task_id} with reason: {reason}")
        return True