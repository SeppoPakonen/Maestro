"""
Tests for Replay & Baselines Lab functionality
"""
import pytest
from datetime import datetime
from maestro.ui_facade.runs import (
    list_runs, 
    get_run, 
    get_run_manifest, 
    replay_run, 
    diff_runs, 
    set_baseline,
    RunSummary,
    DriftInfo
)


def test_list_runs():
    """Test that list_runs returns expected data structure"""
    runs = list_runs()
    
    # Should return a list
    assert isinstance(runs, list)
    
    # Should have at least one run
    assert len(runs) > 0
    
    # Each run should be a RunSummary
    for run in runs:
        assert isinstance(run, RunSummary)
        assert hasattr(run, 'run_id')
        assert hasattr(run, 'timestamp')
        assert hasattr(run, 'mode')
        assert hasattr(run, 'status')
        assert hasattr(run, 'baseline_tag')


def test_get_run():
    """Test getting a specific run"""
    runs = list_runs()
    if runs:
        run_id = runs[0].run_id
        run = get_run(run_id)
        
        assert run is not None
        assert run.run_id == run_id
        assert isinstance(run.timestamp, datetime) or run.timestamp is None
        assert run.mode in ["normal", "rehearse", "replay"]
        assert run.status in ["ok", "drift", "blocked"]


def test_get_run_not_found():
    """Test getting a run that doesn't exist"""
    run = get_run("nonexistent_run_id")
    assert run is None


def test_get_run_manifest():
    """Test getting run manifest"""
    runs = list_runs()
    if runs:
        run_id = runs[0].run_id
        manifest = get_run_manifest(run_id)
        
        assert manifest is not None
        assert manifest.run_id == run_id


def test_replay_run_dry():
    """Test dry replay functionality"""
    runs = list_runs()
    if runs:
        run_id = runs[0].run_id
        result = replay_run(run_id, apply=False)
        
        assert result["success"] is True
        assert result["run_id"] == run_id
        assert result["apply"] is False
        assert "message" in result


def test_replay_run_apply():
    """Test apply replay functionality"""
    runs = list_runs()
    if runs:
        run_id = runs[0].run_id
        result = replay_run(run_id, apply=True)
        
        assert result["success"] is True
        assert result["run_id"] == run_id
        assert result["apply"] is True
        assert "message" in result


def test_replay_run_with_override():
    """Test replay functionality with drift threshold override"""
    runs = list_runs()
    if runs:
        run_id = runs[0].run_id
        # Test with override parameter (though in mock implementation it doesn't change behavior)
        result = replay_run(run_id, apply=True, override_drift_threshold=True)
        
        assert result["success"] is True
        assert result["run_id"] == run_id
        assert result["apply"] is True
        assert "message" in result


def test_replay_run_invalid_id():
    """Test replay with invalid run ID"""
    with pytest.raises(ValueError):
        replay_run("invalid_run_id", apply=False)


def test_diff_runs():
    """Test diff functionality between two runs"""
    runs = list_runs()
    if len(runs) >= 2:
        run1_id = runs[0].run_id
        run2_id = runs[1].run_id
        diff_info = diff_runs(run1_id, run2_id)
        
        assert diff_info is not None
        assert hasattr(diff_info, 'structural_drift')
        assert hasattr(diff_info, 'decision_drift')
        assert hasattr(diff_info, 'semantic_drift')
        
        # Check that drift info has the expected structure
        assert isinstance(diff_info.structural_drift, dict)
        assert isinstance(diff_info.decision_drift, dict)
        assert isinstance(diff_info.semantic_drift, dict)


def test_diff_runs_invalid_ids():
    """Test diff with invalid run IDs"""
    diff_info = diff_runs("invalid_run_id", "another_invalid_id")
    assert diff_info is None


def test_set_baseline():
    """Test setting a run as baseline"""
    runs = list_runs()
    if runs:
        run_id = runs[0].run_id
        result = set_baseline(run_id)
        
        assert result["success"] is True
        assert result["run_id"] == run_id
        assert "message" in result


def test_set_baseline_invalid_id():
    """Test setting baseline with invalid run ID"""
    with pytest.raises(ValueError):
        set_baseline("invalid_run_id")


def test_run_summary_attributes():
    """Test that RunSummary has all expected attributes"""
    runs = list_runs()
    if runs:
        run = runs[0]
        
        # Check all expected attributes exist
        assert hasattr(run, 'run_id')
        assert hasattr(run, 'timestamp')
        assert hasattr(run, 'mode')
        assert hasattr(run, 'status')
        assert hasattr(run, 'baseline_tag')
        assert hasattr(run, 'plan_revision')
        assert hasattr(run, 'decision_fingerprint')
        assert hasattr(run, 'playbook_hash')
        assert hasattr(run, 'engines_used')
        assert hasattr(run, 'checkpoints_hit')
        assert hasattr(run, 'semantic_warnings_count')
        assert hasattr(run, 'arbitration_usage_count')


def test_drift_info_structure():
    """Test that DriftInfo has all expected attributes"""
    runs = list_runs()
    if len(runs) >= 2:
        run1_id = runs[0].run_id
        run2_id = runs[1].run_id
        diff_info = diff_runs(run1_id, run2_id)
        
        if diff_info:  # Only test if diff was successful
            assert hasattr(diff_info, 'structural_drift')
            assert hasattr(diff_info, 'decision_drift')
            assert hasattr(diff_info, 'semantic_drift')
            
            # Check that each drift type has expected content
            assert 'files_changed' in diff_info.structural_drift
            assert 'files_added' in diff_info.structural_drift
            assert 'files_removed' in diff_info.structural_drift
            
            assert 'fingerprint_delta' in diff_info.decision_drift
            assert 'decisions_different' in diff_info.decision_drift
            
            assert 'summary' in diff_info.semantic_drift
            assert 'flags' in diff_info.semantic_drift