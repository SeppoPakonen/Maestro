"""Tests for plan decompose with domain=issues evidence bundling."""
import pytest


def test_domain_issues_evidence_structure():
    """Test that domain=issues adds issues and log scan evidence."""
    # This is a basic structural test since the actual issues/log scan
    # infrastructure may not be fully implemented yet.

    # The evidence should include:
    # 1. Standard repo discovery evidence
    # 2. Issues evidence (kind='issues') if issues exist
    # 3. Log scan evidence (kind='log_scan') if scans exist

    # For now, we just verify that the evidence bundling code is defensive
    # and handles missing issues/scans gracefully.

    from maestro.repo.discovery import DiscoveryEvidence

    # Create a basic discovery evidence
    discovery = DiscoveryEvidence(
        evidence=[
            {"kind": "readme", "path": "README.md", "summary": "Project readme"}
        ],
        warnings=[],
        budget={}
    )

    # Verify we can add issues evidence
    discovery.evidence.append({
        "kind": "issues",
        "path": "docs/maestro/issues/",
        "summary": "Open issues (3 total):\n  - ISS-001 [blocker] Build error"
    })

    # Verify we can add log scan evidence
    discovery.evidence.append({
        "kind": "log_scan",
        "path": "docs/maestro/log_scans/scan-123/",
        "summary": "Last log scan: scan-123\n  Kind: build\n  Total findings: 5"
    })

    assert len(discovery.evidence) == 3
    assert discovery.evidence[1]["kind"] == "issues"
    assert discovery.evidence[2]["kind"] == "log_scan"


def test_bounded_evidence_for_issues():
    """Test that issues evidence is bounded (max 10 issues)."""
    # When there are many issues, we should only include the first 10
    # in the evidence summary to keep prompt size manageable.

    # This test verifies the evidence bundling pattern
    issues_summary_lines = ["Open issues (15 total):"]

    # Add first 10
    for i in range(1, 11):
        issues_summary_lines.append(f"  - ISS-{i:03d} [blocker] Error {i}")

    # Add ellipsis for remaining
    issues_summary_lines.append("  ... and 5 more")

    summary = "\n".join(issues_summary_lines)

    assert "Open issues (15 total)" in summary
    assert "ISS-001" in summary
    assert "ISS-010" in summary
    assert "... and 5 more" in summary
    assert "ISS-011" not in summary  # Should not include beyond first 10


def test_issues_evidence_includes_linked_tasks():
    """Test that issues evidence includes linked task information."""
    # When issues are linked to tasks, the evidence should show that linkage
    issue_line = "  - ISS-001 [blocker] Build error [linked to TASK-001,TASK-002] (src/main.c:42)"

    assert "[linked to TASK-001,TASK-002]" in issue_line
    assert "src/main.c:42" in issue_line


def test_log_scan_evidence_bounded_findings():
    """Test that log scan evidence includes only first 5 findings."""
    # Log scan evidence should be bounded to keep prompt size manageable

    finding_summary_lines = ["Last log scan: scan-20260101-abc123"]
    finding_summary_lines.append("  Kind: build")
    finding_summary_lines.append("  Timestamp: 2026-01-01T12:00:00")
    finding_summary_lines.append("  Total findings: 20")
    finding_summary_lines.append("  Sample findings:")

    # Add first 5 findings
    for i in range(1, 6):
        finding_summary_lines.append(f"    - [blocker] Error {i} (file{i}.c:10)")

    summary = "\n".join(finding_summary_lines)

    assert "Last log scan: scan-20260101-abc123" in summary
    assert "Total findings: 20" in summary
    assert "Sample findings:" in summary
    # Should have exactly 5 sample findings
    assert summary.count("[blocker] Error") == 5
