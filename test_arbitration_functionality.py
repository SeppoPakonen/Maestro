"""
Tests for Arbitration Arena functionality
"""
import pytest
from unittest.mock import patch, MagicMock
from maestro.ui_facade.arbitration import (
    ArbitrationTask,
    ArbitrationStatus,
    Candidate,
    SemanticEquivalence,
    list_arbitrated_tasks,
    get_arbitration,
    list_candidates,
    get_candidate,
    choose_winner,
    reject_candidate
)


def test_arbitration_status_enum():
    """Test that ArbitrationStatus enum works correctly."""
    assert ArbitrationStatus.PENDING.value == "pending"
    assert ArbitrationStatus.DECIDED.value == "decided"
    assert ArbitrationStatus.BLOCKED.value == "blocked"


def test_semantic_equivalence_enum():
    """Test that SemanticEquivalence enum works correctly."""
    assert SemanticEquivalence.EQUIVALENT.value == "equivalent"
    assert SemanticEquivalence.SIMILAR.value == "similar"
    assert SemanticEquivalence.DIFFERENT.value == "different"
    assert SemanticEquivalence.CONFLICTING.value == "conflicting"


def test_arbitration_task_creation():
    """Test ArbitrationTask dataclass."""
    task = ArbitrationTask(
        id="test_task_001",
        phase="convert",
        status=ArbitrationStatus.PENDING,
        winner="qwen"
    )
    
    assert task.id == "test_task_001"
    assert task.phase == "convert"
    assert task.status == ArbitrationStatus.PENDING
    assert task.winner == "qwen"


def test_candidate_creation():
    """Test Candidate dataclass."""
    candidate = Candidate(
        engine="qwen",
        score=0.85,
        semantic_equivalence=SemanticEquivalence.SIMILAR,
        validation_passed=True,
        flags=["large_diff"],
        files_written=["src/file.py"],
        policy_used="strict",
        validation_output="All tests passed"
    )
    
    assert candidate.engine == "qwen"
    assert candidate.score == 0.85
    assert candidate.semantic_equivalence == SemanticEquivalence.SIMILAR
    assert candidate.validation_passed is True
    assert candidate.flags == ["large_diff"]
    assert candidate.files_written == ["src/file.py"]
    assert candidate.policy_used == "strict"
    assert candidate.validation_output == "All tests passed"


def test_candidate_defaults():
    """Test Candidate dataclass with default values."""
    candidate = Candidate(engine="claude")
    
    assert candidate.engine == "claude"
    assert candidate.score is None
    assert candidate.flags == []  # Default value from __post_init__
    assert candidate.files_written == []  # Default value from __post_init__
    assert candidate.validation_passed is True


def test_list_arbitrated_tasks_basic():
    """Test list_arbitrated_tasks basic functionality."""
    # With ImportError fallback, should return mock data
    tasks = list_arbitrated_tasks("session_123")

    # Should return mock data when ImportError occurs
    assert len(tasks) >= 1  # At least one mock task should be returned
    assert all(isinstance(task, ArbitrationTask) for task in tasks)
    assert any(task.id == "task_arb_001" for task in tasks)


def test_get_arbitration_basic():
    """Test get_arbitration basic functionality."""
    # With ImportError fallback, should return mock data
    arbitration_data = get_arbitration("task_001")

    # Should return mock data when ImportError occurs
    assert arbitration_data.task_id == 'task_001'
    assert len(arbitration_data.candidates) >= 1  # At least one mock candidate should be returned
    assert any(c.engine == "qwen" for c in arbitration_data.candidates)


def test_list_candidates():
    """Test list_candidates function."""
    # This function relies on get_arbitration, so we'll test the flow
    with patch('maestro.ui_facade.arbitration.get_arbitration') as mock_get_arbitration:
        mock_arbitration_data = MagicMock()
        mock_arbitration_data.candidates = [
            Candidate(engine="qwen"),
            Candidate(engine="claude")
        ]
        mock_get_arbitration.return_value = mock_arbitration_data
        
        candidates = list_candidates("task_001")
        
        assert len(candidates) == 2
        assert candidates[0].engine == "qwen"
        assert candidates[1].engine == "claude"


def test_get_candidate_success():
    """Test get_candidate function with successful lookup."""
    with patch('maestro.ui_facade.arbitration.list_candidates') as mock_list_candidates:
        mock_candidates = [
            Candidate(engine="qwen", score=0.85),
            Candidate(engine="claude", score=0.92)
        ]
        mock_list_candidates.return_value = mock_candidates
        
        candidate = get_candidate("task_001", "qwen")
        
        assert candidate.engine == "qwen"
        assert candidate.score == 0.85


def test_get_candidate_case_insensitive():
    """Test get_candidate function with case-insensitive lookup."""
    with patch('maestro.ui_facade.arbitration.list_candidates') as mock_list_candidates:
        mock_candidates = [
            Candidate(engine="Qwen", score=0.85)
        ]
        mock_list_candidates.return_value = mock_candidates
        
        candidate = get_candidate("task_001", "qwen")  # lowercase input
        
        assert candidate.engine == "Qwen"  # original case, but matching
        assert candidate.score == 0.85


def test_get_candidate_not_found():
    """Test get_candidate function when candidate is not found."""
    with patch('maestro.ui_facade.arbitration.list_candidates') as mock_list_candidates:
        mock_candidates = [
            Candidate(engine="qwen", score=0.85)
        ]
        mock_list_candidates.return_value = mock_candidates
        
        with pytest.raises(ValueError, match="No candidate found for engine 'nonexistent' in task 'task_001'"):
            get_candidate("task_001", "nonexistent")


def test_choose_winner_basic():
    """Test choose_winner basic functionality."""
    # With ImportError fallback, should simulate success
    result = choose_winner("task_001", "qwen", "Best score and semantics")

    assert result is True  # Should return True in simulation mode


def test_reject_candidate_basic():
    """Test reject_candidate basic functionality."""
    # With ImportError fallback, should simulate success
    result = reject_candidate("task_001", "claude", "Low quality output")

    assert result is True  # Should return True in simulation mode


if __name__ == "__main__":
    pytest.main([__file__])