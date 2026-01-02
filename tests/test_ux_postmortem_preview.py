"""
Tests for UX postmortem preview mode (safe, no writes).

All tests verify that preview mode does not write files.
"""

import pytest
import json
import tempfile
from pathlib import Path
from maestro.ux.postmortem import UXPostmortem


def create_fake_eval_dir(tmpdir: Path, eval_id: str):
    """Create a fake UX eval directory with artifacts."""
    eval_dir = tmpdir / eval_id
    eval_dir.mkdir(parents=True)

    # Create telemetry.json
    telemetry = {
        'eval_id': eval_id,
        'goal': 'Test goal for preview',
        'total_attempts': 2,
        'successful_attempts': 1,
        'failed_attempts': 1,
        'help_call_count': 5,
        'timeout_count': 0,
        'unknown_command_count': 1
    }
    with open(eval_dir / 'telemetry.json', 'w') as f:
        json.dump(telemetry, f)

    # Create attempts.jsonl
    attempts = [
        {
            'attempt_index': 0,
            'command_argv': ['maestro', 'plan', 'list'],
            'exit_code': 0,
            'duration_ms': 150,
            'stdout_excerpt': 'Plan 1\nPlan 2',
            'stderr_excerpt': '',
            'timestamp': '2025-01-01T00:00:00',
            'timed_out': False
        },
        {
            'attempt_index': 1,
            'command_argv': ['maestro', 'unknown'],
            'exit_code': 127,
            'duration_ms': 10,
            'stdout_excerpt': '',
            'stderr_excerpt': 'Command not found',
            'timestamp': '2025-01-01T00:00:01',
            'timed_out': False
        }
    ]
    with open(eval_dir / 'attempts.jsonl', 'w') as f:
        for attempt in attempts:
            f.write(json.dumps(attempt) + '\n')

    # Create surface.json
    surface = {
        'surface': {
            ('maestro',): {
                'command_path': ['maestro'],
                'help_text': 'Maestro CLI',
                'help_hash': 'hash1',
                'discovered_subcommands': ['plan', 'repo']
            }
        },
        'help_call_count': 5
    }
    with open(eval_dir / 'surface.json', 'w') as f:
        # Convert tuples to lists for JSON
        surface_json = {'surface': {}, 'help_call_count': 5}
        json.dump(surface_json, f)

    # Create report.md
    with open(eval_dir / f'{eval_id}.md', 'w') as f:
        f.write("# UX Evaluation Report\n\nTest report content")

    return eval_dir


def test_preview_mode_no_files_written(tmp_path):
    """Test that preview mode does not write any files."""
    eval_id = 'ux_eval_test_001'
    eval_dir = create_fake_eval_dir(tmp_path, eval_id)

    # Create postmortem (preview mode, execute=False)
    postmortem = UXPostmortem(
        eval_id=eval_id,
        eval_dir=eval_dir,
        verbose=False,
        very_verbose=False
    )

    # Run in preview mode
    result = postmortem.run(
        execute=False,
        create_issues=True,
        decompose=True,
        profile='investor'
    )

    # Verify no postmortem directory was created
    postmortem_dir = eval_dir / 'ux_postmortem'
    assert not postmortem_dir.exists(), "Preview mode should not create postmortem directory"

    # Verify result indicates preview mode
    assert result['mode'] == 'preview'
    assert result['log_file'] is None
    assert result['scan_id'] is None
    assert result['issues_created'] == []
    assert result['workgraph_id'] is None


def test_preview_mode_prints_commands(tmp_path, capsys):
    """Test that preview mode prints what would be done."""
    eval_id = 'ux_eval_test_002'
    eval_dir = create_fake_eval_dir(tmp_path, eval_id)

    postmortem = UXPostmortem(
        eval_id=eval_id,
        eval_dir=eval_dir,
        verbose=False,
        very_verbose=False
    )

    # Run in preview mode
    result = postmortem.run(
        execute=False,
        create_issues=True,
        decompose=True,
        profile='purpose'
    )

    # Capture output
    captured = capsys.readouterr()

    # Should print preview header
    assert "PREVIEW (DRY RUN)" in captured.out

    # Should print commands that would be executed
    assert "maestro log scan" in captured.out
    assert "maestro issues add" in captured.out
    assert "maestro plan decompose" in captured.out

    # Should mention execute flag
    assert "--execute" in captured.out


def test_preview_mode_with_verbose(tmp_path, capsys):
    """Test preview mode with verbose flag."""
    eval_id = 'ux_eval_test_003'
    eval_dir = create_fake_eval_dir(tmp_path, eval_id)

    postmortem = UXPostmortem(
        eval_id=eval_id,
        eval_dir=eval_dir,
        verbose=True,
        very_verbose=False
    )

    result = postmortem.run(
        execute=False,
        create_issues=False,
        decompose=False,
        profile='default'
    )

    captured = capsys.readouterr()

    # Verbose should show steps
    assert "Step 1:" in captured.out or "Loading" in captured.out
    assert "Step 2:" in captured.out or "Building" in captured.out


def test_preview_mode_respects_flags(tmp_path, capsys):
    """Test that preview mode respects --issues and --decompose flags."""
    eval_id = 'ux_eval_test_004'
    eval_dir = create_fake_eval_dir(tmp_path, eval_id)

    # Case 1: No issues, no decompose
    postmortem1 = UXPostmortem(eval_id=eval_id, eval_dir=eval_dir, verbose=False)
    result1 = postmortem1.run(execute=False, create_issues=False, decompose=False)

    captured1 = capsys.readouterr()
    assert "maestro issues add" not in captured1.out
    assert "maestro plan decompose" not in captured1.out

    # Case 2: Issues only
    postmortem2 = UXPostmortem(eval_id=eval_id, eval_dir=eval_dir, verbose=False)
    result2 = postmortem2.run(execute=False, create_issues=True, decompose=False)

    captured2 = capsys.readouterr()
    assert "maestro issues add" in captured2.out
    assert "maestro plan decompose" not in captured2.out

    # Case 3: Issues + decompose
    postmortem3 = UXPostmortem(eval_id=eval_id, eval_dir=eval_dir, verbose=False)
    result3 = postmortem3.run(execute=False, create_issues=True, decompose=True)

    captured3 = capsys.readouterr()
    assert "maestro issues add" in captured3.out
    assert "maestro plan decompose" in captured3.out


def test_preview_mode_shows_profile(tmp_path, capsys):
    """Test that preview mode shows selected profile."""
    eval_id = 'ux_eval_test_005'
    eval_dir = create_fake_eval_dir(tmp_path, eval_id)

    postmortem = UXPostmortem(eval_id=eval_id, eval_dir=eval_dir, verbose=False)
    result = postmortem.run(
        execute=False,
        create_issues=True,
        decompose=True,
        profile='investor'
    )

    captured = capsys.readouterr()

    # Should show profile in decompose command
    assert "--profile investor" in captured.out


def test_preview_mode_safe_even_with_bad_artifacts(tmp_path):
    """Test that preview mode is safe even if artifacts are incomplete."""
    eval_id = 'ux_eval_test_006'
    eval_dir = tmp_path / eval_id
    eval_dir.mkdir(parents=True)

    # Create minimal telemetry (missing other artifacts)
    telemetry = {
        'eval_id': eval_id,
        'goal': 'Test',
        'total_attempts': 0,
        'successful_attempts': 0,
        'failed_attempts': 0,
        'help_call_count': 0
    }
    with open(eval_dir / 'telemetry.json', 'w') as f:
        json.dump(telemetry, f)

    # Create empty attempts.jsonl
    with open(eval_dir / 'attempts.jsonl', 'w') as f:
        pass

    # Create minimal surface.json
    with open(eval_dir / 'surface.json', 'w') as f:
        json.dump({'surface': {}, 'help_call_count': 0}, f)

    # Preview mode should still work without crashing
    postmortem = UXPostmortem(eval_id=eval_id, eval_dir=eval_dir, verbose=False)

    try:
        result = postmortem.run(execute=False, create_issues=False, decompose=False)
        # Should complete without error
        assert result['mode'] == 'preview'
    except Exception as e:
        pytest.fail(f"Preview mode should not crash with minimal artifacts: {e}")


def test_preview_mode_returns_correct_result_structure(tmp_path):
    """Test that preview mode returns correct result structure."""
    eval_id = 'ux_eval_test_007'
    eval_dir = create_fake_eval_dir(tmp_path, eval_id)

    postmortem = UXPostmortem(eval_id=eval_id, eval_dir=eval_dir, verbose=False)
    result = postmortem.run(
        execute=False,
        create_issues=True,
        decompose=True,
        profile='purpose'
    )

    # Verify result structure
    assert 'eval_id' in result
    assert 'mode' in result
    assert 'create_issues' in result
    assert 'decompose' in result
    assert 'profile' in result
    assert 'log_file' in result
    assert 'scan_id' in result
    assert 'issues_created' in result
    assert 'workgraph_id' in result

    # Preview mode values should be None/empty
    assert result['eval_id'] == eval_id
    assert result['mode'] == 'preview'
    assert result['create_issues'] is True
    assert result['decompose'] is True
    assert result['profile'] == 'purpose'
    assert result['log_file'] is None
    assert result['scan_id'] is None
    assert result['issues_created'] == []
    assert result['workgraph_id'] is None
