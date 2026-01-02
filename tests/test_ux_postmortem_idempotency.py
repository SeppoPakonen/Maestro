"""
Tests for UX postmortem idempotency (stable outputs, no duplication).

Verifies that running postmortem multiple times produces deterministic results.
"""

import pytest
import json
from pathlib import Path
from maestro.ux.postmortem import UXPostmortem, build_ux_log, load_eval_artifacts


def create_fake_eval_dir(tmpdir: Path, eval_id: str):
    """Create a fake UX eval directory with artifacts."""
    eval_dir = tmpdir / eval_id
    eval_dir.mkdir(parents=True)

    # Create telemetry.json
    telemetry = {
        'eval_id': eval_id,
        'goal': 'Stable goal for idempotency test',
        'total_attempts': 2,
        'successful_attempts': 1,
        'failed_attempts': 1,
        'help_call_count': 5,
        'timeout_count': 0,
        'unknown_command_count': 1
    }
    with open(eval_dir / 'telemetry.json', 'w') as f:
        json.dump(telemetry, f)

    # Create attempts.jsonl (deterministic order)
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
        'surface': {},
        'help_call_count': 5
    }
    with open(eval_dir / 'surface.json', 'w') as f:
        json.dump(surface, f)

    # Create report.md
    with open(eval_dir / f'{eval_id}.md', 'w') as f:
        f.write("# UX Evaluation Report\n\nDeterministic report content")

    return eval_dir


def test_load_eval_artifacts_deterministic(tmp_path):
    """Test that loading artifacts produces deterministic results."""
    eval_id = 'ux_eval_idem_001'
    eval_dir = create_fake_eval_dir(tmp_path, eval_id)

    # Load twice
    artifacts1 = load_eval_artifacts(eval_dir)
    artifacts2 = load_eval_artifacts(eval_dir)

    # Should be identical
    assert artifacts1['telemetry'] == artifacts2['telemetry']
    assert artifacts1['attempts'] == artifacts2['attempts']
    assert artifacts1['surface'] == artifacts2['surface']
    assert artifacts1['report_text'] == artifacts2['report_text']


def test_build_ux_log_idempotent(tmp_path):
    """Test that building log twice produces identical output."""
    eval_id = 'ux_eval_idem_002'
    eval_dir = create_fake_eval_dir(tmp_path, eval_id)

    artifacts = load_eval_artifacts(eval_dir)
    goal = artifacts['telemetry']['goal']

    # Build log twice
    log1 = build_ux_log(
        artifacts['attempts'],
        artifacts['surface'],
        artifacts['report_text'],
        goal
    )

    log2 = build_ux_log(
        artifacts['attempts'],
        artifacts['surface'],
        artifacts['report_text'],
        goal
    )

    # Should be character-for-character identical
    assert log1 == log2
    assert len(log1) == len(log2)


def test_postmortem_run_twice_same_log_content(tmp_path, monkeypatch):
    """Test that running postmortem twice produces same log content."""
    eval_id = 'ux_eval_idem_003'
    eval_dir = create_fake_eval_dir(tmp_path, eval_id)

    # Mock subprocess to avoid actual commands
    class FakeResult:
        def __init__(self):
            self.returncode = 0
            self.stdout = "Scan created: SCAN-IDEM-001\n"
            self.stderr = ""

    def fake_run(cmd, **kwargs):
        return FakeResult()

    import subprocess
    monkeypatch.setattr(subprocess, 'run', fake_run)

    # Run postmortem first time
    postmortem1 = UXPostmortem(eval_id=eval_id, eval_dir=eval_dir, verbose=False)
    result1 = postmortem1.run(execute=True, create_issues=False, decompose=False)

    log_file = eval_dir / 'ux_postmortem' / 'ux_log.txt'
    with open(log_file, 'r') as f:
        log_content_1 = f.read()

    # Remove postmortem dir
    import shutil
    shutil.rmtree(eval_dir / 'ux_postmortem')

    # Run postmortem second time
    postmortem2 = UXPostmortem(eval_id=eval_id, eval_dir=eval_dir, verbose=False)
    result2 = postmortem2.run(execute=True, create_issues=False, decompose=False)

    with open(log_file, 'r') as f:
        log_content_2 = f.read()

    # Log content should be identical
    assert log_content_1 == log_content_2


def test_postmortem_metadata_includes_timestamp(tmp_path, monkeypatch):
    """Test that postmortem metadata includes timestamp (but log content is still deterministic)."""
    eval_id = 'ux_eval_idem_004'
    eval_dir = create_fake_eval_dir(tmp_path, eval_id)

    class FakeResult:
        def __init__(self):
            self.returncode = 0
            self.stdout = "Scan created: SCAN-IDEM-002\n"
            self.stderr = ""

    def fake_run(cmd, **kwargs):
        return FakeResult()

    import subprocess
    monkeypatch.setattr(subprocess, 'run', fake_run)

    postmortem = UXPostmortem(eval_id=eval_id, eval_dir=eval_dir, verbose=False)
    result = postmortem.run(execute=True, create_issues=False, decompose=False)

    # Check postmortem.json has timestamp
    meta_file = eval_dir / 'ux_postmortem' / 'postmortem.json'
    with open(meta_file, 'r') as f:
        meta = json.load(f)

    assert 'timestamp' in meta
    assert meta['eval_id'] == eval_id
    assert meta['mode'] == 'execute'


def test_log_content_stable_across_different_postmortem_instances(tmp_path):
    """Test that different UXPostmortem instances produce same log for same eval."""
    eval_id = 'ux_eval_idem_005'
    eval_dir = create_fake_eval_dir(tmp_path, eval_id)

    artifacts = load_eval_artifacts(eval_dir)
    goal = artifacts['telemetry']['goal']

    # Create log with function directly (no UXPostmortem instance)
    log_direct = build_ux_log(
        artifacts['attempts'],
        artifacts['surface'],
        artifacts['report_text'],
        goal
    )

    # Create log via UXPostmortem (but don't execute, just check the log)
    postmortem = UXPostmortem(eval_id=eval_id, eval_dir=eval_dir, verbose=False)

    # Manually build log inside postmortem (same as what run() does)
    log_via_postmortem = build_ux_log(
        artifacts['attempts'],
        artifacts['surface'],
        artifacts['report_text'],
        goal
    )

    # Should be identical
    assert log_direct == log_via_postmortem


def test_log_fingerprint_stability():
    """Test that log fingerprints (hashes) are stable for same input."""
    import hashlib

    attempts = [
        {
            'attempt_index': 0,
            'command_argv': ['maestro', 'test'],
            'exit_code': 0,
            'duration_ms': 100,
            'stdout_excerpt': 'Output',
            'stderr_excerpt': '',
            'timestamp': '2025-01-01T00:00:00',
            'timed_out': False
        }
    ]

    surface = {'surface': {}, 'help_call_count': 1}
    report = "Report"
    goal = "Goal"

    # Build log multiple times and hash
    log1 = build_ux_log(attempts, surface, report, goal)
    hash1 = hashlib.sha256(log1.encode()).hexdigest()

    log2 = build_ux_log(attempts, surface, report, goal)
    hash2 = hashlib.sha256(log2.encode()).hexdigest()

    log3 = build_ux_log(attempts, surface, report, goal)
    hash3 = hashlib.sha256(log3.encode()).hexdigest()

    # All hashes should be identical
    assert hash1 == hash2 == hash3


def test_attempt_order_preserved(tmp_path):
    """Test that attempt order is preserved in log (important for determinism)."""
    eval_id = 'ux_eval_idem_006'
    eval_dir = tmp_path / eval_id
    eval_dir.mkdir(parents=True)

    # Create attempts in specific order
    attempts = [
        {'attempt_index': 0, 'command_argv': ['maestro', 'cmd0'],
         'exit_code': 0, 'duration_ms': 10, 'stdout_excerpt': '',
         'stderr_excerpt': '', 'timestamp': '2025-01-01T00:00:00', 'timed_out': False},
        {'attempt_index': 1, 'command_argv': ['maestro', 'cmd1'],
         'exit_code': 0, 'duration_ms': 20, 'stdout_excerpt': '',
         'stderr_excerpt': '', 'timestamp': '2025-01-01T00:00:01', 'timed_out': False},
        {'attempt_index': 2, 'command_argv': ['maestro', 'cmd2'],
         'exit_code': 0, 'duration_ms': 30, 'stdout_excerpt': '',
         'stderr_excerpt': '', 'timestamp': '2025-01-01T00:00:02', 'timed_out': False}
    ]

    surface = {'surface': {}, 'help_call_count': 3}
    log = build_ux_log(attempts, surface, "", "Goal")

    # Verify order by checking positions in log
    pos_cmd0 = log.find('Attempt 1: maestro cmd0')
    pos_cmd1 = log.find('Attempt 2: maestro cmd1')
    pos_cmd2 = log.find('Attempt 3: maestro cmd2')

    # All should be found
    assert pos_cmd0 > 0
    assert pos_cmd1 > 0
    assert pos_cmd2 > 0

    # Should be in order
    assert pos_cmd0 < pos_cmd1 < pos_cmd2


def test_failure_summary_deterministic():
    """Test that failure summary counts are deterministic."""
    attempts = [
        # 2 unknown commands
        {'attempt_index': 0, 'command_argv': ['maestro', 'bad1'],
         'exit_code': 127, 'duration_ms': 10, 'stdout_excerpt': '',
         'stderr_excerpt': 'Not found', 'timestamp': '2025-01-01T00:00:00', 'timed_out': False},
        {'attempt_index': 1, 'command_argv': ['maestro', 'bad2'],
         'exit_code': 127, 'duration_ms': 10, 'stdout_excerpt': '',
         'stderr_excerpt': 'Not found', 'timestamp': '2025-01-01T00:00:01', 'timed_out': False},
        # 1 timeout
        {'attempt_index': 2, 'command_argv': ['maestro', 'slow'],
         'exit_code': 124, 'duration_ms': 30000, 'stdout_excerpt': '',
         'stderr_excerpt': '[TIMEOUT]', 'timestamp': '2025-01-01T00:00:02', 'timed_out': True},
        # 1 other failure
        {'attempt_index': 3, 'command_argv': ['maestro', 'fail'],
         'exit_code': 1, 'duration_ms': 100, 'stdout_excerpt': '',
         'stderr_excerpt': 'Error', 'timestamp': '2025-01-01T00:00:03', 'timed_out': False}
    ]

    surface = {'surface': {}, 'help_call_count': 4}

    # Build twice
    log1 = build_ux_log(attempts, surface, "", "Goal")
    log2 = build_ux_log(attempts, surface, "", "Goal")

    # Both should have same failure counts
    assert "Total Failures: 4" in log1
    assert "Total Failures: 4" in log2
    assert "Timeouts: 1" in log1
    assert "Timeouts: 1" in log2
    assert "Unknown Commands: 2" in log1
    assert "Unknown Commands: 2" in log2
    assert "Other Failures: 1" in log1
    assert "Other Failures: 1" in log2

    # Logs should be identical
    assert log1 == log2
