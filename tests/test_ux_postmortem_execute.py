"""
Tests for UX postmortem execute mode with mocked subprocess calls.

Uses pytest monkeypatch to mock subprocess.run for deterministic tests.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from maestro.ux.postmortem import UXPostmortem


def create_fake_eval_dir(tmpdir: Path, eval_id: str):
    """Create a fake UX eval directory with artifacts."""
    eval_dir = tmpdir / eval_id
    eval_dir.mkdir(parents=True)

    # Create telemetry.json
    telemetry = {
        'eval_id': eval_id,
        'goal': 'Improve CLI UX for repository analysis',
        'total_attempts': 3,
        'successful_attempts': 1,
        'failed_attempts': 2,
        'help_call_count': 10,
        'timeout_count': 1,
        'unknown_command_count': 1
    }
    with open(eval_dir / 'telemetry.json', 'w') as f:
        json.dump(telemetry, f)

    # Create attempts.jsonl
    attempts = [
        {
            'attempt_index': 0,
            'command_argv': ['maestro', 'repo', 'resolve'],
            'exit_code': 0,
            'duration_ms': 150,
            'stdout_excerpt': 'Repository analyzed',
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
        },
        {
            'attempt_index': 2,
            'command_argv': ['maestro', 'slow'],
            'exit_code': 124,
            'duration_ms': 30000,
            'stdout_excerpt': '',
            'stderr_excerpt': '[TIMEOUT]',
            'timestamp': '2025-01-01T00:00:02',
            'timed_out': True
        }
    ]
    with open(eval_dir / 'attempts.jsonl', 'w') as f:
        for attempt in attempts:
            f.write(json.dumps(attempt) + '\n')

    # Create surface.json
    surface = {
        'surface': {},
        'help_call_count': 10
    }
    with open(eval_dir / 'surface.json', 'w') as f:
        json.dump(surface, f)

    # Create report.md
    with open(eval_dir / f'{eval_id}.md', 'w') as f:
        f.write("# UX Evaluation Report\n\nFindings and recommendations")

    return eval_dir


class FakeSubprocessResult:
    """Fake subprocess.run result."""
    def __init__(self, returncode, stdout, stderr):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_execute_mode_creates_files(tmp_path, monkeypatch):
    """Test that execute mode creates expected files."""
    eval_id = 'ux_eval_test_exec_001'
    eval_dir = create_fake_eval_dir(tmp_path, eval_id)

    # Mock subprocess.run
    def fake_subprocess_run(cmd, **kwargs):
        # Return fake scan ID
        return FakeSubprocessResult(
            returncode=0,
            stdout="Scan created: SCAN-TEST-001\n",
            stderr=""
        )

    import subprocess
    monkeypatch.setattr(subprocess, 'run', fake_subprocess_run)

    # Run postmortem in execute mode
    postmortem = UXPostmortem(eval_id=eval_id, eval_dir=eval_dir, verbose=False)
    result = postmortem.run(execute=True, create_issues=False, decompose=False)

    # Verify postmortem directory was created
    postmortem_dir = eval_dir / 'ux_postmortem'
    assert postmortem_dir.exists()

    # Verify ux_log.txt was created
    log_file = postmortem_dir / 'ux_log.txt'
    assert log_file.exists()

    # Verify log content
    with open(log_file, 'r') as f:
        log_content = f.read()
    assert "UX EVALUATION SYNTHETIC LOG" in log_content
    assert "Improve CLI UX for repository analysis" in log_content

    # Verify postmortem.json was created
    meta_file = postmortem_dir / 'postmortem.json'
    assert meta_file.exists()

    with open(meta_file, 'r') as f:
        meta = json.load(f)
    assert meta['eval_id'] == eval_id
    assert meta['mode'] == 'execute'
    assert meta['scan_id'] == 'SCAN-TEST-001'


def test_execute_mode_runs_log_scan(tmp_path, monkeypatch, capsys):
    """Test that execute mode runs log scan command."""
    eval_id = 'ux_eval_test_exec_002'
    eval_dir = create_fake_eval_dir(tmp_path, eval_id)

    commands_run = []

    def fake_subprocess_run(cmd, **kwargs):
        commands_run.append(' '.join(cmd))
        if 'log' in cmd and 'scan' in cmd:
            return FakeSubprocessResult(
                returncode=0,
                stdout="Scan created: SCAN-TEST-002\n",
                stderr=""
            )
        return FakeSubprocessResult(returncode=0, stdout="", stderr="")

    import subprocess
    monkeypatch.setattr(subprocess, 'run', fake_subprocess_run)

    postmortem = UXPostmortem(eval_id=eval_id, eval_dir=eval_dir, verbose=False)
    result = postmortem.run(execute=True, create_issues=False, decompose=False)

    # Verify log scan command was run
    assert any('maestro log scan' in cmd for cmd in commands_run)
    assert any('--kind run' in cmd for cmd in commands_run)

    # Verify scan_id in result
    assert result['scan_id'] == 'SCAN-TEST-002'


def test_execute_mode_creates_issues(tmp_path, monkeypatch, capsys):
    """Test that execute mode creates issues when --issues flag is set."""
    eval_id = 'ux_eval_test_exec_003'
    eval_dir = create_fake_eval_dir(tmp_path, eval_id)

    commands_run = []

    def fake_subprocess_run(cmd, **kwargs):
        commands_run.append(' '.join(cmd))
        if 'log' in cmd and 'scan' in cmd:
            return FakeSubprocessResult(
                returncode=0,
                stdout="Scan created: SCAN-TEST-003\n",
                stderr=""
            )
        elif 'issues' in cmd and 'add' in cmd:
            return FakeSubprocessResult(
                returncode=0,
                stdout="Created ISSUE-001\nCreated ISSUE-002\n",
                stderr=""
            )
        return FakeSubprocessResult(returncode=0, stdout="", stderr="")

    import subprocess
    monkeypatch.setattr(subprocess, 'run', fake_subprocess_run)

    postmortem = UXPostmortem(eval_id=eval_id, eval_dir=eval_dir, verbose=False)
    result = postmortem.run(execute=True, create_issues=True, decompose=False)

    # Verify issues command was run
    assert any('maestro issues add' in cmd for cmd in commands_run)
    assert any('--from-log SCAN-TEST-003' in cmd for cmd in commands_run)

    # Verify issues in result
    assert len(result['issues_created']) == 2
    assert 'ISSUE-001' in result['issues_created']
    assert 'ISSUE-002' in result['issues_created']

    # Verify issues_created.json was created
    issues_file = eval_dir / 'ux_postmortem' / 'issues_created.json'
    assert issues_file.exists()

    with open(issues_file, 'r') as f:
        issues_data = json.load(f)
    assert 'ISSUE-001' in issues_data['issue_ids']


def test_execute_mode_decomposes_workgraph(tmp_path, monkeypatch):
    """Test that execute mode decomposes WorkGraph when --decompose flag is set."""
    eval_id = 'ux_eval_test_exec_004'
    eval_dir = create_fake_eval_dir(tmp_path, eval_id)

    commands_run = []

    def fake_subprocess_run(cmd, **kwargs):
        commands_run.append(' '.join(cmd))
        if 'log' in cmd and 'scan' in cmd:
            return FakeSubprocessResult(
                returncode=0,
                stdout="Scan created: SCAN-TEST-004\n",
                stderr=""
            )
        elif 'issues' in cmd and 'add' in cmd:
            return FakeSubprocessResult(
                returncode=0,
                stdout="Created ISSUE-003\n",
                stderr=""
            )
        elif 'plan' in cmd and 'decompose' in cmd:
            return FakeSubprocessResult(
                returncode=0,
                stdout="Created WorkGraph: wg-test-004\n",
                stderr=""
            )
        return FakeSubprocessResult(returncode=0, stdout="", stderr="")

    import subprocess
    monkeypatch.setattr(subprocess, 'run', fake_subprocess_run)

    postmortem = UXPostmortem(eval_id=eval_id, eval_dir=eval_dir, verbose=False)
    result = postmortem.run(
        execute=True,
        create_issues=True,
        decompose=True,
        profile='investor'
    )

    # Verify decompose command was run
    assert any('maestro plan decompose' in cmd for cmd in commands_run)
    assert any('--domain issues' in cmd for cmd in commands_run)
    assert any('--profile investor' in cmd for cmd in commands_run)

    # Verify workgraph_id in result
    assert result['workgraph_id'] == 'wg-test-004'

    # Verify workgraph_id.txt was created
    wg_file = eval_dir / 'ux_postmortem' / 'workgraph_id.txt'
    assert wg_file.exists()

    with open(wg_file, 'r') as f:
        wg_id = f.read().strip()
    assert wg_id == 'wg-test-004'


def test_execute_mode_emits_markers(tmp_path, monkeypatch, capsys):
    """Test that execute mode emits machine-readable markers."""
    eval_id = 'ux_eval_test_exec_005'
    eval_dir = create_fake_eval_dir(tmp_path, eval_id)

    def fake_subprocess_run(cmd, **kwargs):
        if 'log' in cmd and 'scan' in cmd:
            return FakeSubprocessResult(0, "Scan created: SCAN-MARKER-001\n", "")
        elif 'issues' in cmd and 'add' in cmd:
            return FakeSubprocessResult(0, "Created ISSUE-M1\nCreated ISSUE-M2\n", "")
        elif 'plan' in cmd and 'decompose' in cmd:
            return FakeSubprocessResult(0, "Created WorkGraph: wg-marker-001\n", "")
        return FakeSubprocessResult(0, "", "")

    import subprocess
    monkeypatch.setattr(subprocess, 'run', fake_subprocess_run)

    postmortem = UXPostmortem(eval_id=eval_id, eval_dir=eval_dir, verbose=False)
    result = postmortem.run(
        execute=True,
        create_issues=True,
        decompose=True,
        profile='purpose'
    )

    captured = capsys.readouterr()

    # Verify machine-readable markers were emitted
    assert f"MAESTRO_UX_EVAL_ID={eval_id}" in captured.out
    assert "MAESTRO_UX_POSTMORTEM_SCAN_ID=SCAN-MARKER-001" in captured.out
    assert "MAESTRO_UX_POSTMORTEM_ISSUES=2" in captured.out
    assert "MAESTRO_UX_POSTMORTEM_WORKGRAPH_ID=wg-marker-001" in captured.out


def test_execute_mode_pipeline_order(tmp_path, monkeypatch):
    """Test that execute mode runs pipeline steps in correct order."""
    eval_id = 'ux_eval_test_exec_006'
    eval_dir = create_fake_eval_dir(tmp_path, eval_id)

    call_order = []

    def fake_subprocess_run(cmd, **kwargs):
        if 'log' in cmd and 'scan' in cmd:
            call_order.append('log_scan')
            return FakeSubprocessResult(0, "Scan created: SCAN-006\n", "")
        elif 'issues' in cmd and 'add' in cmd:
            call_order.append('issues_add')
            return FakeSubprocessResult(0, "Created ISSUE-006\n", "")
        elif 'plan' in cmd and 'decompose' in cmd:
            call_order.append('decompose')
            return FakeSubprocessResult(0, "Created WorkGraph: wg-006\n", "")
        return FakeSubprocessResult(0, "", "")

    import subprocess
    monkeypatch.setattr(subprocess, 'run', fake_subprocess_run)

    postmortem = UXPostmortem(eval_id=eval_id, eval_dir=eval_dir, verbose=False)
    result = postmortem.run(
        execute=True,
        create_issues=True,
        decompose=True,
        profile='default'
    )

    # Verify correct order: log_scan → issues_add → decompose
    assert call_order == ['log_scan', 'issues_add', 'decompose']


def test_execute_mode_handles_scan_failure(tmp_path, monkeypatch):
    """Test that execute mode handles log scan failure gracefully."""
    eval_id = 'ux_eval_test_exec_007'
    eval_dir = create_fake_eval_dir(tmp_path, eval_id)

    def fake_subprocess_run(cmd, **kwargs):
        if 'log' in cmd and 'scan' in cmd:
            # Simulate scan failure (no scan ID in output)
            return FakeSubprocessResult(1, "", "Error scanning log")
        return FakeSubprocessResult(0, "", "")

    import subprocess
    monkeypatch.setattr(subprocess, 'run', fake_subprocess_run)

    postmortem = UXPostmortem(eval_id=eval_id, eval_dir=eval_dir, verbose=False)
    result = postmortem.run(execute=True, create_issues=True, decompose=True)

    # Should complete without crashing
    assert result['scan_id'] is None
    assert result['issues_created'] == []
    assert result['workgraph_id'] is None


def test_execute_mode_with_very_verbose(tmp_path, monkeypatch, capsys):
    """Test execute mode with -vv flag shows subprocess commands."""
    eval_id = 'ux_eval_test_exec_008'
    eval_dir = create_fake_eval_dir(tmp_path, eval_id)

    def fake_subprocess_run(cmd, **kwargs):
        if 'log' in cmd and 'scan' in cmd:
            return FakeSubprocessResult(0, "Scan created: SCAN-VV-001\n", "")
        return FakeSubprocessResult(0, "", "")

    import subprocess
    monkeypatch.setattr(subprocess, 'run', fake_subprocess_run)

    postmortem = UXPostmortem(
        eval_id=eval_id,
        eval_dir=eval_dir,
        verbose=True,
        very_verbose=True
    )
    result = postmortem.run(execute=True, create_issues=False, decompose=False)

    captured = capsys.readouterr()

    # Very verbose should show command being run
    assert "Running: maestro log scan" in captured.out or "Running:" in captured.out
