#!/usr/bin/env python3
"""
Tests for batch functionality in Maestro.

This test module verifies the multi-repo batch conversion feature.
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

# Add the maestro package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from maestro.main import (
    BatchJobSpec, BatchDefaults, BatchSpec, 
    load_batch_spec, validate_batch_spec_schema,
    get_playbook_path, resolve_playbook_for_job
)


def test_batch_spec_validation():
    """Test batch specification validation."""
    print("Testing batch spec validation...")
    
    # Valid spec
    valid_spec = {
        "batch_id": "test_batch_001",
        "defaults": {
            "rehearse": True,
            "auto_replan": False,
            "arbitrate": True,
            "max_candidates": 2,
            "judge_engine": "codex",
            "checkpoint_mode": "manual",
            "semantic_strict": True
        },
        "jobs": [
            {
                "name": "test_job_1",
                "source": "/path/to/source1",
                "target": "/path/to/target1", 
                "intent": "high_to_low_level",
                "playbook": "cpp_to_c"
            }
        ]
    }
    
    is_valid, error_msg = validate_batch_spec_schema(valid_spec)
    assert is_valid, f"Valid spec should pass validation: {error_msg}"
    
    # Invalid spec without required fields
    invalid_spec = {
        "batch_id": "test_batch_001",
        # Missing defaults and jobs
    }
    
    is_valid, error_msg = validate_batch_spec_schema(invalid_spec)
    assert not is_valid, "Invalid spec should fail validation"
    assert "Missing required field" in error_msg
    
    print("✓ Batch spec validation tests passed")


def test_batch_spec_loading():
    """Test loading batch specifications from file."""
    print("Testing batch spec loading...")
    
    # Create a temporary batch spec file
    spec_data = {
        "batch_id": "test_batch_load",
        "defaults": {
            "rehearse": True,
            "auto_replan": False,
            "arbitrate": True,
            "max_candidates": 2,
            "judge_engine": "codex",
            "checkpoint_mode": "manual",
            "semantic_strict": True
        },
        "jobs": [
            {
                "name": "job1",
                "source": "/path/to/source1",
                "target": "/path/to/target1",
                "intent": "convert_cpp_to_c",
                "playbook": "cpp_to_c_playbook",
                "tags": ["core", "low_level"]
            },
            {
                "name": "job2", 
                "source": "/path/to/source2",
                "target": "/path/to/target2",
                "intent": "add_typing",
                "rehearse": False
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(spec_data, f)
        spec_path = f.name
    
    try:
        batch_spec = load_batch_spec(spec_path)
        assert batch_spec.batch_id == "test_batch_load"
        assert len(batch_spec.jobs) == 2
        assert batch_spec.jobs[0].name == "job1"
        assert batch_spec.jobs[1].name == "job2"
        assert batch_spec.jobs[0].tags == ["core", "low_level"]
        assert batch_spec.defaults.rehearse == True
        
        print("✓ Batch spec loading tests passed")
    finally:
        os.unlink(spec_path)


def test_playbook_resolution():
    """Test playbook resolution functionality."""
    print("Testing playbook resolution...")
    
    # Create temporary directories for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a source directory with .maestro/playbooks
        source_dir = os.path.join(temp_dir, "source_repo")
        maestro_dir = os.path.join(source_dir, ".maestro")
        playbooks_dir = os.path.join(maestro_dir, "playbooks")
        os.makedirs(playbooks_dir)
        
        # Create a test playbook in the repo-local directory
        test_playbook_path = os.path.join(playbooks_dir, "test_playbook.json")
        with open(test_playbook_path, 'w') as f:
            json.dump({"test": "playbook"}, f)
        
        # Test resolution with repo-local playbook
        job_spec = BatchJobSpec(
            name="test_job",
            source=source_dir,
            target="/tmp/target",
            intent="test",
            playbook="test_playbook.json"
        )
        
        resolved_path = resolve_playbook_for_job(job_spec)
        assert resolved_path == test_playbook_path, f"Expected {test_playbook_path}, got {resolved_path}"
        
        # Test with non-existent playbook
        job_spec2 = BatchJobSpec(
            name="test_job2",
            source=source_dir,
            target="/tmp/target2",
            intent="test",
            playbook="nonexistent.json"
        )
        
        resolved_path2 = resolve_playbook_for_job(job_spec2)
        assert resolved_path2 is None, f"Expected None for non-existent playbook, got {resolved_path2}"
        
        print("✓ Playbook resolution tests passed")


def test_filter_batch_jobs():
    """Test batch job filtering functionality."""
    print("Testing batch job filtering...")
    
    from maestro.main import filter_batch_jobs, BatchJobSpec
    
    jobs = [
        BatchJobSpec(name="job1", source="/src1", target="/tgt1", intent="convert", tags=["core"]),
        BatchJobSpec(name="job2", source="/src2", target="/tgt2", intent="convert", tags=["utils"]),
        BatchJobSpec(name="job3", source="/src3", target="/tgt3", intent="convert", tags=["core", "web"])
    ]
    
    # Test filtering by job name
    filtered = filter_batch_jobs(jobs, "job1")
    assert len(filtered) == 1
    assert filtered[0].name == "job1"
    
    # Test filtering by job: prefix
    filtered = filter_batch_jobs(jobs, "job:job2")
    assert len(filtered) == 1
    assert filtered[0].name == "job2"
    
    # Test filtering by tag:
    filtered = filter_batch_jobs(jobs, "tag:core")
    assert len(filtered) == 2  # job1 and job3 have "core" tag
    job_names = {j.name for j in filtered}
    assert job_names == {"job1", "job3"}
    
    # Test with no filter (should return all)
    filtered = filter_batch_jobs(jobs, None)
    assert len(filtered) == 3
    
    print("✓ Batch job filtering tests passed")


def run_all_tests():
    """Run all batch functionality tests."""
    print("Running batch functionality tests...\n")
    
    test_batch_spec_validation()
    test_batch_spec_loading() 
    test_playbook_resolution()
    test_filter_batch_jobs()
    
    print("\n✓ All batch functionality tests passed!")


if __name__ == "__main__":
    run_all_tests()