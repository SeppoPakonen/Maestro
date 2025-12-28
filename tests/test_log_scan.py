"""
Test log scanning functionality.
"""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

from maestro.log import create_scan, load_scan, list_scans
from maestro.log.fingerprint import generate_fingerprint, normalize_message


class TestFingerprinting:
    """Test fingerprint generation."""

    def test_normalize_message_removes_absolute_paths(self):
        """Test that normalization removes absolute paths."""
        message = "/home/user/project/src/foo.cpp:42: error: undefined reference"
        normalized = normalize_message(message)
        assert "/home/user" not in normalized
        assert "<REPO>/" in normalized or "src/foo.cpp" in normalized

    def test_normalize_message_removes_timestamps(self):
        """Test that normalization removes timestamps."""
        message = "2025-01-01T12:00:30 error occurred"
        normalized = normalize_message(message)
        assert "2025-01-01T12:00:30" not in normalized
        assert "<TIMESTAMP>" in normalized

    def test_same_message_same_fingerprint(self):
        """Test that same message produces same fingerprint."""
        msg1 = "error: undefined reference to 'foo()'"
        msg2 = "error: undefined reference to 'foo()'"
        fp1 = generate_fingerprint(msg1, tool="gcc", file="main.cpp")
        fp2 = generate_fingerprint(msg2, tool="gcc", file="main.cpp")
        assert fp1 == fp2

    def test_different_paths_same_fingerprint(self):
        """Test that different absolute paths produce same fingerprint."""
        msg1 = "/home/alice/project/foo.cpp:42: error: undefined reference"
        msg2 = "/home/bob/work/project/foo.cpp:42: error: undefined reference"
        fp1 = generate_fingerprint(msg1, file="foo.cpp")
        fp2 = generate_fingerprint(msg2, file="foo.cpp")
        # Should be same since we use basename
        assert fp1 == fp2


class TestLogScan:
    """Test log scanning."""

    @pytest.fixture
    def temp_repo(self):
        """Create temporary repository."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_create_scan_from_text(self, temp_repo):
        """Test creating scan from log text."""
        log_text = """
        foo.cpp:10: error: undefined reference to 'bar()'
        foo.cpp:20: warning: unused variable 'x'
        """

        scan_id = create_scan(
            source_path=None,
            log_text=log_text,
            kind='build',
            repo_root=temp_repo,
        )

        assert scan_id
        assert 'build' in scan_id

        # Verify scan was created
        scan_data = load_scan(scan_id, temp_repo)
        assert scan_data is not None
        assert scan_data['meta']['scan_id'] == scan_id
        assert len(scan_data['findings']) > 0

    def test_create_scan_from_file(self, temp_repo):
        """Test creating scan from log file."""
        # Get the fixture file
        fixture_path = Path(__file__).parent / "fixtures" / "logs" / "build_error.log"

        if not fixture_path.exists():
            pytest.skip("Fixture file not found")

        scan_id = create_scan(
            source_path=str(fixture_path),
            log_text=None,
            kind='build',
            repo_root=temp_repo,
        )

        assert scan_id
        scan_data = load_scan(scan_id, temp_repo)
        assert scan_data is not None

        findings = scan_data['findings']
        assert len(findings) > 0

        # Should find errors and warnings
        error_findings = [f for f in findings if f.severity == 'blocker']
        warning_findings = [f for f in findings if f.severity == 'warning']

        assert len(error_findings) > 0, "Should find at least one error"
        assert len(warning_findings) >= 0, "May find warnings"

    def test_list_scans(self, temp_repo):
        """Test listing scans."""
        # Create multiple scans
        scan_id1 = create_scan(
            source_path=None,
            log_text="error: build failed",
            kind='build',
            repo_root=temp_repo,
        )

        scan_id2 = create_scan(
            source_path=None,
            log_text="error: test failed",
            kind='run',
            repo_root=temp_repo,
        )

        scans = list_scans(temp_repo)
        assert len(scans) == 2

        scan_ids = [s['scan_id'] for s in scans]
        assert scan_id1 in scan_ids
        assert scan_id2 in scan_ids

    def test_deterministic_fingerprints(self, temp_repo):
        """Test that same log scanned twice produces same fingerprints."""
        log_text = "foo.cpp:10: error: undefined reference to 'bar()'"

        # Scan twice
        scan_id1 = create_scan(
            source_path=None,
            log_text=log_text,
            kind='build',
            repo_root=temp_repo,
        )

        scan_id2 = create_scan(
            source_path=None,
            log_text=log_text,
            kind='build',
            repo_root=temp_repo,
        )

        # Load both scans
        scan1 = load_scan(scan_id1, temp_repo)
        scan2 = load_scan(scan_id2, temp_repo)

        # Should have same fingerprints for corresponding findings
        if scan1['findings'] and scan2['findings']:
            fp1 = scan1['findings'][0].fingerprint
            fp2 = scan2['findings'][0].fingerprint
            assert fp1 == fp2, "Same log should produce same fingerprints"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
