"""
Tests for Cross-Repo Semantic Diff Explorer functionality
"""
import pytest
from unittest.mock import Mock, patch
from maestro.tui.screens.semantic_diff import SemanticDiffScreen
from maestro.ui_facade.semantic import (
    get_mapping_index,
    diff_semantics,
    get_semantic_coverage,
    get_semantic_hotspots,
    acknowledge_loss,
    override_loss
)


def test_semantic_diff_screen_initialization():
    """Test that SemanticDiffScreen initializes without errors."""
    screen = SemanticDiffScreen()
    assert screen is not None
    assert screen.mappings == []
    assert screen.summary is None
    assert screen.checkpoint is None


def test_get_mapping_index():
    """Test get_mapping_index function."""
    result = get_mapping_index()
    
    assert isinstance(result, list)
    assert len(result) >= 0  # May be empty or have entries
    
    if result:
        mapping = result[0]
        assert 'id' in mapping
        assert 'source_path' in mapping
        assert 'target_path' in mapping
        assert 'status' in mapping
        assert 'concepts' in mapping


def test_diff_semantics_current_baseline():
    """Test diff_semantics function with current_baseline mode."""
    result = diff_semantics("current_baseline", "current_run", "baseline_id")
    
    assert 'mode' in result
    assert result['mode'] == 'current_baseline'
    assert 'lhs' in result
    assert 'rhs' in result
    assert 'mappings' in result
    assert 'summary' in result
    
    summary = result['summary']
    assert 'total_concepts' in summary
    assert 'preserved_concepts' in summary
    assert 'changed_concepts' in summary
    assert 'degraded_concepts' in summary
    assert 'lost_concepts' in summary
    assert 'aggregated_risk_score' in summary


def test_diff_semantics_run_run():
    """Test diff_semantics function with run_run mode."""
    result = diff_semantics("run_run", "run1", "run2")
    
    assert 'mode' in result
    assert result['mode'] == 'run_run'
    assert 'lhs' in result
    assert 'rhs' in result
    assert 'mappings' in result
    assert 'summary' in result
    
    summary = result['summary']
    assert 'total_concepts' in summary
    assert 'preserved_concepts' in summary
    assert 'changed_concepts' in summary
    assert 'degraded_concepts' in summary
    assert 'lost_concepts' in summary
    assert 'aggregated_risk_score' in summary


def test_diff_semantics_source_target():
    """Test diff_semantics function with source_target mode."""
    result = diff_semantics("source_target", "source_repo", "target_repo")
    
    assert 'mode' in result
    assert result['mode'] == 'source_target'
    assert 'lhs' in result
    assert 'rhs' in result
    assert 'mappings' in result
    assert 'summary' in result
    
    summary = result['summary']
    assert 'total_concepts' in summary
    assert 'preserved_concepts' in summary
    assert 'changed_concepts' in summary
    assert 'degraded_concepts' in summary
    assert 'lost_concepts' in summary
    assert 'aggregated_risk_score' in summary


def test_get_semantic_coverage():
    """Test get_semantic_coverage function."""
    result = get_semantic_coverage()
    
    assert 'total_mappings' in result
    assert 'preserved_mappings' in result
    assert 'changed_mappings' in result
    assert 'degraded_mappings' in result
    assert 'lost_mappings' in result
    assert 'coverage_percentage' in result
    assert 'risk_distribution' in result
    
    risk_dist = result['risk_distribution']
    assert 'low_risk' in risk_dist
    assert 'medium_risk' in risk_dist
    assert 'high_risk' in risk_dist


def test_get_semantic_hotspots():
    """Test get_semantic_hotspots function."""
    result = get_semantic_hotspots()
    
    # Result should be a list (may be empty)
    assert isinstance(result, list)
    
    if result:
        hotspot = result[0]
        assert 'file_path' in hotspot
        assert 'risk_score' in hotspot
        assert 'description' in hotspot


def test_acknowledge_loss():
    """Test acknowledge_loss function."""
    result = acknowledge_loss("loss_id_123", "Test reason for acknowledgment")
    
    assert result is True


def test_override_loss():
    """Test override_loss function."""
    result = override_loss("loss_id_123", "Test reason for override")
    
    assert result is True


def test_semantic_diff_data_loading():
    """Test that semantic diff data loading works properly."""
    from maestro.ui_facade.semantic import (
        get_mapping_index,
        diff_semantics
    )
    from maestro.tui.screens.semantic_diff import (
        SemanticDiffConcept,
        SemanticDiffMapping,
        SemanticDiffSummary,
        CheckpointInfo
    )
    from datetime import datetime

    # Get real data functions to test
    mappings_data = get_mapping_index()

    # Test the data transformation logic directly without Textual UI components
    mappings = []
    for mapping_data in mappings_data:
        concepts = []
        for concept_data in mapping_data.get('concepts', []):
            concept = SemanticDiffConcept(
                id=concept_data['id'],
                name=concept_data['name'],
                source_file=concept_data['source_file'],
                target_file=concept_data['target_file'],
                status=concept_data['status'],
                equivalence_level=concept_data['equivalence_level'],
                risk_score=concept_data['risk_score'],
                confidence=concept_data['confidence'],
                description=concept_data['description'],
                evidence_links=concept_data['evidence_links']
            )
            concepts.append(concept)

        mapping = SemanticDiffMapping(
            id=mapping_data['id'],
            source_path=mapping_data['source_path'],
            target_path=mapping_data['target_path'],
            status=mapping_data['status'],
            concepts=concepts,
            risk_score=mapping_data['risk_score'],
            confidence=mapping_data['confidence'],
            equivalence_level=mapping_data['equivalence_level'],
            heuristics_used=mapping_data['heuristics_used']
        )
        mappings.append(mapping)

    # Verify the mappings were created properly
    assert len(mappings) >= 0  # May be empty but should be a valid list
    for mapping in mappings:
        assert hasattr(mapping, 'id')
        assert hasattr(mapping, 'source_path')
        assert hasattr(mapping, 'target_path')
        assert hasattr(mapping, 'concepts')
        for concept in mapping.concepts:
            assert hasattr(concept, 'id')
            assert hasattr(concept, 'name')
            assert hasattr(concept, 'status')

    # Test diff semantics
    diff_result = diff_semantics("source_target", "source_repo", "target_repo")
    assert 'summary' in diff_result
    summary_data = diff_result['summary']

    # Create summary object
    summary = SemanticDiffSummary(
        total_concepts=summary_data.get('total_concepts', 0),
        preserved_concepts=summary_data.get('preserved_concepts', 0),
        changed_concepts=summary_data.get('changed_concepts', 0),
        degraded_concepts=summary_data.get('degraded_concepts', 0),
        lost_concepts=summary_data.get('lost_concepts', 0),
        total_files=summary_data.get('total_files', 0),
        preserved_files=summary_data.get('preserved_files', 0),
        changed_files=summary_data.get('changed_files', 0),
        lost_files=summary_data.get('lost_files', 0),
        aggregated_risk_score=summary_data.get('aggregated_risk_score', 0.0),
        confidence_score=summary_data.get('confidence_score', 0.0),
        heuristics_used=summary_data.get('heuristics_used', []),
        drift_threshold_exceeded=summary_data.get('drift_threshold_exceeded', False),
        checkpoint_required=summary_data.get('checkpoint_required', False)
    )

    # Verify summary was created properly
    assert summary.total_concepts >= 0
    assert 0.0 <= summary.aggregated_risk_score <= 1.0
    assert 0.0 <= summary.confidence_score <= 1.0


if __name__ == "__main__":
    pytest.main([__file__])