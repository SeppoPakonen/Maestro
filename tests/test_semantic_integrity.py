"""
Tests for Semantic Integrity Panel functionality
"""
import os
import tempfile
from unittest.mock import patch, MagicMock
from maestro.ui_facade.semantic import (
    list_semantic_findings,
    get_semantic_finding,
    accept_semantic_finding,
    reject_semantic_finding,
    defer_semantic_finding,
    get_semantic_summary,
    add_semantic_finding,
    get_blocking_semantic_findings
)
from maestro.ui_facade.convert import SemanticFinding, SemanticSummary


def test_semantic_finding_dataclass():
    """Test that SemanticFinding dataclass works correctly."""
    finding = SemanticFinding(
        id="test_001",
        task_id="task_001",
        files=["src/test.cpp"],
        equivalence_level="high",
        risk_flags=["logic-change"],
        status="pending",
        description="Test semantic finding",
        evidence_before="int x = 0;",
        evidence_after="x = 0",
        decision_reason="Test reason",
        checkpoint_id="chk_001",
        blocks_pipeline=True
    )
    
    assert finding.id == "test_001"
    assert finding.task_id == "task_001"
    assert finding.files == ["src/test.cpp"]
    assert finding.equivalence_level == "high"
    assert finding.risk_flags == ["logic-change"]
    assert finding.status == "pending"
    assert finding.description == "Test semantic finding"
    assert finding.evidence_before == "int x = 0;"
    assert finding.evidence_after == "x = 0"
    assert finding.decision_reason == "Test reason"
    assert finding.checkpoint_id == "chk_001"
    assert finding.blocks_pipeline is True


def test_semantic_summary_dataclass():
    """Test that SemanticSummary dataclass works correctly."""
    summary = SemanticSummary(
        total_findings=10,
        high_risk=2,
        medium_risk=3,
        low_risk=5,
        accepted=4,
        rejected=1,
        blocking=2,
        overall_health_score=0.7
    )
    
    assert summary.total_findings == 10
    assert summary.high_risk == 2
    assert summary.medium_risk == 3
    assert summary.low_risk == 5
    assert summary.accepted == 4
    assert summary.rejected == 1
    assert summary.blocking == 2
    assert summary.overall_health_score == 0.7


@patch('maestro.ui_facade.semantic._load_semantic_findings')
def test_list_semantic_findings(mock_load):
    """Test listing semantic findings."""
    mock_findings = [
        SemanticFinding(
            id="test_001",
            task_id="task_001",
            files=["src/test.cpp"],
            equivalence_level="high",
            risk_flags=["logic-change"],
            status="pending",
            description="Test finding",
            evidence_before="old code",
            evidence_after="new code"
        )
    ]
    mock_load.return_value = mock_findings
    
    findings = list_semantic_findings(pipeline_id="test_pipeline")
    
    assert len(findings) == 1
    assert findings[0].id == "test_001"
    assert findings[0].status == "pending"
    mock_load.assert_called_once_with("test_pipeline")


@patch('maestro.ui_facade.semantic._load_semantic_findings')
def test_get_semantic_finding(mock_load):
    """Test getting a specific semantic finding."""
    mock_findings = [
        SemanticFinding(
            id="test_001",
            task_id="task_001",
            files=["src/test.cpp"],
            equivalence_level="high",
            risk_flags=["logic-change"],
            status="pending",
            description="Test finding",
            evidence_before="old code",
            evidence_after="new code"
        )
    ]
    mock_load.return_value = mock_findings
    
    finding = get_semantic_finding("test_001", pipeline_id="test_pipeline")
    
    assert finding is not None
    assert finding.id == "test_001"
    mock_load.assert_called_once_with("test_pipeline")


@patch('maestro.ui_facade.semantic._load_semantic_findings')
@patch('maestro.ui_facade.semantic._save_semantic_findings')
@patch('maestro.ui_facade.semantic.load_conversion_pipeline')
@patch('maestro.ui_facade.semantic.save_conversion_pipeline')
def test_accept_semantic_finding(mock_save_pipeline, mock_load_pipeline, mock_save, mock_load):
    """Test accepting a semantic finding."""
    # Setup mock pipeline
    mock_pipeline = MagicMock()
    mock_pipeline.stages = []
    mock_load_pipeline.return_value = mock_pipeline
    
    # Setup mock findings
    finding = SemanticFinding(
        id="test_001",
        task_id="task_001",
        files=["src/test.cpp"],
        equivalence_level="high",
        risk_flags=["logic-change"],
        status="pending",
        description="Test finding",
        evidence_before="old code",
        evidence_after="new code",
        blocks_pipeline=True
    )
    mock_load.return_value = [finding]
    
    # Test accepting the finding
    result = accept_semantic_finding("test_001", reason="Reviewed and accepted", pipeline_id="test_pipeline")
    
    assert result is True
    mock_load.assert_called_once_with("test_pipeline")
    mock_save.assert_called_once_with("test_pipeline", [finding])
    
    # Verify the finding was updated
    assert finding.status == "accepted"
    assert finding.decision_reason == "Reviewed and accepted"


@patch('maestro.ui_facade.semantic._load_semantic_findings')
@patch('maestro.ui_facade.semantic._save_semantic_findings')
def test_reject_semantic_finding(mock_save, mock_load):
    """Test rejecting a semantic finding."""
    finding = SemanticFinding(
        id="test_001",
        task_id="task_001",
        files=["src/test.cpp"],
        equivalence_level="high",
        risk_flags=["logic-change"],
        status="pending",
        description="Test finding",
        evidence_before="old code",
        evidence_after="new code"
    )
    mock_load.return_value = [finding]
    
    # Test rejecting the finding
    result = reject_semantic_finding("test_001", reason="Risk too high", pipeline_id="test_pipeline")
    
    assert result is True
    mock_load.assert_called_once_with("test_pipeline")
    mock_save.assert_called_once_with("test_pipeline", [finding])
    
    # Verify the finding was updated
    assert finding.status == "rejected"
    assert finding.decision_reason == "Risk too high"


def test_reject_semantic_finding_no_reason():
    """Test rejecting a semantic finding without providing a reason."""
    with patch('maestro.ui_facade.semantic._load_semantic_findings'):
        with patch('maestro.ui_facade.semantic._save_semantic_findings'):
            with patch('maestro.ui_facade.semantic.load_conversion_pipeline'):
                with patch('maestro.ui_facade.semantic.save_conversion_pipeline'):
                    try:
                        result = reject_semantic_finding("test_001", reason="", pipeline_id="test_pipeline")
                        # If we reach here without an exception, the test failed
                        assert False, "Expected ValueError was not raised"
                    except ValueError as e:
                        assert "Reason is required" in str(e)


@patch('maestro.ui_facade.semantic._load_semantic_findings')
@patch('maestro.ui_facade.semantic._save_semantic_findings')
def test_defer_semantic_finding(mock_save, mock_load):
    """Test deferring a semantic finding."""
    finding = SemanticFinding(
        id="test_001",
        task_id="task_001",
        files=["src/test.cpp"],
        equivalence_level="medium",
        risk_flags=["performance"],
        status="pending",
        description="Test finding",
        evidence_before="old code",
        evidence_after="new code"
    )
    mock_load.return_value = [finding]
    
    # Test deferring the finding
    result = defer_semantic_finding("test_001", pipeline_id="test_pipeline")
    
    assert result is True
    mock_load.assert_called_once_with("test_pipeline")
    mock_save.assert_called_once_with("test_pipeline", [finding])
    
    # Verify the finding was updated
    assert finding.status == "pending"  # Deferred findings remain pending
    assert finding.decision_reason is not None  # Should have a reason for deferral


@patch('maestro.ui_facade.semantic._load_semantic_findings')
def test_get_semantic_summary(mock_load):
    """Test getting semantic summary."""
    findings = [
        SemanticFinding(
            id="test_001",
            task_id="task_001",
            files=["src/test1.cpp"],
            equivalence_level="high",
            risk_flags=["logic-change"],
            status="pending",
            description="High risk finding",
            evidence_before="old code",
            evidence_after="new code",
            blocks_pipeline=True
        ),
        SemanticFinding(
            id="test_002",
            task_id="task_002",
            files=["src/test2.cpp"],
            equivalence_level="medium",
            risk_flags=["performance"],
            status="accepted",
            description="Medium risk finding",
            evidence_before="old code",
            evidence_after="new code"
        ),
        SemanticFinding(
            id="test_003",
            task_id="task_003",
            files=["src/test3.cpp"],
            equivalence_level="low",
            risk_flags=["formatting"],
            status="rejected",
            description="Low risk finding",
            evidence_before="old code",
            evidence_after="new code"
        )
    ]
    mock_load.return_value = findings
    
    summary = get_semantic_summary(pipeline_id="test_pipeline")
    
    assert summary.total_findings == 3
    assert summary.high_risk == 1
    assert summary.medium_risk == 1
    assert summary.low_risk == 1
    assert summary.accepted == 1
    assert summary.rejected == 1
    assert summary.blocking == 1
    assert 0.0 <= summary.overall_health_score <= 1.0


@patch('maestro.ui_facade.semantic._load_semantic_findings')
@patch('maestro.ui_facade.semantic._save_semantic_findings')
def test_add_semantic_finding_new(mock_save, mock_load):
    """Test adding a new semantic finding."""
    existing_findings = [
        SemanticFinding(
            id="existing_001",
            task_id="task_001",
            files=["src/test1.cpp"],
            equivalence_level="high",
            risk_flags=["logic-change"],
            status="pending",
            description="Existing finding",
            evidence_before="old code",
            evidence_after="new code"
        )
    ]
    mock_load.return_value = existing_findings
    
    new_finding = SemanticFinding(
        id="new_001",
        task_id="task_002",
        files=["src/test2.cpp"],
        equivalence_level="medium",
        risk_flags=["performance"],
        status="pending",
        description="New finding",
        evidence_before="old code2",
        evidence_after="new code2"
    )
    
    result = add_semantic_finding(new_finding, pipeline_id="test_pipeline")
    
    assert result is True
    mock_load.assert_called_once_with("test_pipeline")
    assert len(mock_save.call_args[0][1]) == 2  # Should have 2 findings now
    assert mock_save.call_args[0][1][0].id == "existing_001"
    assert mock_save.call_args[0][1][1].id == "new_001"


@patch('maestro.ui_facade.semantic._load_semantic_findings')
@patch('maestro.ui_facade.semantic._save_semantic_findings')
def test_add_semantic_finding_update(mock_save, mock_load):
    """Test updating an existing semantic finding."""
    existing_findings = [
        SemanticFinding(
            id="existing_001",
            task_id="task_001",
            files=["src/test1.cpp"],
            equivalence_level="high",
            risk_flags=["logic-change"],
            status="pending",
            description="Original finding",
            evidence_before="old code",
            evidence_after="new code"
        )
    ]
    mock_load.return_value = existing_findings
    
    updated_finding = SemanticFinding(
        id="existing_001",  # Same ID - should update
        task_id="task_001",
        files=["src/test1_updated.cpp"],  # Different file
        equivalence_level="medium",  # Different level
        risk_flags=["performance"],
        status="accepted",
        description="Updated finding",
        evidence_before="old code updated",
        evidence_after="new code updated"
    )
    
    result = add_semantic_finding(updated_finding, pipeline_id="test_pipeline")
    
    assert result is True
    mock_load.assert_called_once_with("test_pipeline")
    assert len(mock_save.call_args[0][1]) == 1  # Should still have 1 finding
    saved_finding = mock_save.call_args[0][1][0]
    assert saved_finding.id == "existing_001"
    assert saved_finding.description == "Updated finding"


@patch('maestro.ui_facade.semantic._load_semantic_findings')
def test_get_blocking_semantic_findings(mock_load):
    """Test getting blocking semantic findings."""
    findings = [
        SemanticFinding(
            id="blocking_001",
            task_id="task_001",
            files=["src/test1.cpp"],
            equivalence_level="high",
            risk_flags=["logic-change"],
            status="blocking",
            description="Blocking finding",
            evidence_before="old code",
            evidence_after="new code",
            blocks_pipeline=True
        ),
        SemanticFinding(
            id="non_blocking_001",
            task_id="task_002",
            files=["src/test2.cpp"],
            equivalence_level="low",
            risk_flags=["formatting"],
            status="accepted",
            description="Non-blocking finding",
            evidence_before="old code",
            evidence_after="new code",
            blocks_pipeline=False
        ),
        SemanticFinding(
            id="pending_blocking_001",
            task_id="task_003",
            files=["src/test3.cpp"],
            equivalence_level="high",
            risk_flags=["logic-change"],
            status="pending",
            description="Pending blocking finding",
            evidence_before="old code",
            evidence_after="new code",
            blocks_pipeline=True
        )
    ]
    mock_load.return_value = findings
    
    blocking_findings = get_blocking_semantic_findings(pipeline_id="test_pipeline")
    
    assert len(blocking_findings) == 2
    ids = [f.id for f in blocking_findings]
    assert "blocking_001" in ids
    assert "pending_blocking_001" in ids
    assert "non_blocking_001" not in ids


if __name__ == "__main__":
    pytest.main([__file__])