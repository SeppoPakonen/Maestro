"""
Ops doctor - health checks for repository state.

Provides deterministic checks for gates and blockers with recommended next commands.
"""

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any

from maestro.repo_lock import RepoLock
from maestro.git_guard import get_current_branch, check_branch_guard
from maestro.config.paths import get_docs_root
from maestro.work_session import list_sessions


@dataclass
class Finding:
    """A single doctor finding."""
    id: str
    severity: str  # "ok", "warning", "error", "blocker"
    message: str
    details: Optional[str] = None
    recommended_commands: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "id": self.id,
            "severity": self.severity,
            "message": self.message,
            "details": self.details,
            "recommended_commands": self.recommended_commands,
        }


@dataclass
class DoctorResult:
    """Result of running doctor checks."""
    findings: List[Finding]
    exit_code: int = 0

    def has_fatal(self) -> bool:
        """Check if any fatal findings exist."""
        return any(f.severity in ("error", "blocker") for f in self.findings)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "findings": [f.to_dict() for f in self.findings],
            "exit_code": self.exit_code,
            "summary": {
                "total": len(self.findings),
                "ok": sum(1 for f in self.findings if f.severity == "ok"),
                "warnings": sum(1 for f in self.findings if f.severity == "warning"),
                "errors": sum(1 for f in self.findings if f.severity == "error"),
                "blockers": sum(1 for f in self.findings if f.severity == "blocker"),
            }
        }


def check_repo_lock(docs_root: Optional[Path] = None) -> Finding:
    """Check 1: Repo lock sanity."""
    if docs_root:
        lock_dir = Path(docs_root) / "docs" / "maestro" / "locks"
        lock = RepoLock(lock_dir=lock_dir)
    else:
        lock = RepoLock()
    lock_info = lock.get_lock_info()

    if not lock_info:
        if lock.lock_file.exists():
            return Finding(
                id="STALE_LOCK",
                severity="warning",
                message="Repository lock file is invalid",
                details=f"Lock file: {lock.lock_file}",
                recommended_commands=[
                    f"rm {lock.lock_file}",
                ]
            )
        return Finding(
            id="REPO_LOCK",
            severity="ok",
            message="No active repository lock"
        )

    # Check if process is running
    try:
        is_running = lock._is_process_running(lock_info.pid)
    except Exception:
        is_running = False

    if is_running:
        return Finding(
            id="LOCKED",
            severity="blocker",
            message=f"Repository is locked by session {lock_info.session_id}",
            details=f"PID {lock_info.pid}, started {lock_info.timestamp}",
            recommended_commands=[
                f"maestro wsession close {lock_info.session_id}",
                f"maestro discuss resume {lock_info.session_id}"
            ]
        )

    # Process dead, stale lock
    return Finding(
        id="STALE_LOCK",
        severity="warning",
        message="Stale repository lock detected",
        details=f"Lock from dead process (PID {lock_info.pid})",
        recommended_commands=[
            f"maestro wsession close {lock_info.session_id}",
            f"rm {lock.lock_file}"
        ]
    )


def check_git_status(repo_root: Optional[str] = None) -> List[Finding]:
    """Check 2: Branch/dirty guard."""
    findings = []

    # Check if in git repo
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=repo_root or None,
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            findings.append(Finding(
                id="GIT_REPO",
                severity="warning",
                message="Not in a git repository",
                recommended_commands=["git init"]
            ))
            return findings
    except FileNotFoundError:
        findings.append(Finding(
            id="GIT_REPO",
            severity="warning",
            message="Git not found in PATH"
        ))
        return findings

    # Check for dirty tree
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root or None,
        capture_output=True,
        text=True,
        check=False
    )
    if result.returncode == 0 and result.stdout.strip():
        findings.append(Finding(
            id="DIRTY_TREE",
            severity="warning",
            message="Working tree has uncommitted changes",
            details=f"{len(result.stdout.strip().splitlines())} modified files",
            recommended_commands=[
                "git status",
                "git add <files>",
                "git commit -m '<message>'"
            ]
        ))
    else:
        findings.append(Finding(
            id="DIRTY_TREE",
            severity="ok",
            message="Working tree is clean"
        ))

    # Check for detached HEAD
    current_branch = get_current_branch(repo_root)
    if current_branch == "HEAD":
        findings.append(Finding(
            id="DETACHED_HEAD",
            severity="warning",
            message="In detached HEAD state",
            recommended_commands=[
                "git branch",
                "git checkout <branch-name>"
            ]
        ))
    elif current_branch:
        findings.append(Finding(
            id="DETACHED_HEAD",
            severity="ok",
            message=f"On branch {current_branch}"
        ))
    else:
        findings.append(Finding(
            id="DETACHED_HEAD",
            severity="warning",
            message="Unable to determine current branch"
        ))

    # Check for wrong branch vs active work session
    branch_guard = check_branch_guard(repo_root)
    if branch_guard:
        findings.append(Finding(
            id="WRONG_BRANCH",
            severity="warning",
            message="Active work session branch mismatch",
            details=branch_guard,
            recommended_commands=[
                "git branch",
                "git checkout <expected-branch>",
                "maestro wsession list"
            ]
        ))
    else:
        findings.append(Finding(
            id="WRONG_BRANCH",
            severity="ok",
            message="No branch guard violations detected"
        ))

    return findings


def check_repo_truth(docs_root: Optional[Path] = None) -> Finding:
    """Check 3: Repo truth readiness."""
    if not docs_root:
        docs_root = get_docs_root()

    repo_model_path = docs_root / "docs" / "maestro" / "repo" / "model.json"

    if not repo_model_path.exists():
        return Finding(
            id="REPO_TRUTH_EXISTS",
            severity="warning",
            message="Repository model not found",
            details=f"Expected at {repo_model_path}",
            recommended_commands=["maestro repo resolve"]
        )

    # Check if file is valid JSON
    try:
        with open(repo_model_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Basic validation
        if not isinstance(data, dict):
            return Finding(
                id="REPO_TRUTH_EXISTS",
                severity="error",
                message="Repository model is invalid",
                details="Not a JSON object",
                recommended_commands=["maestro repo resolve"]
            )

        return Finding(
            id="REPO_TRUTH_EXISTS",
            severity="ok",
            message="Repository model exists and is valid"
        )
    except json.JSONDecodeError as e:
        return Finding(
            id="REPO_TRUTH_EXISTS",
            severity="error",
            message="Repository model is corrupted",
            details=str(e),
            recommended_commands=["maestro repo resolve"]
        )


def check_repo_conf(docs_root: Optional[Path] = None) -> Finding:
    """Check 4: RepoConf readiness."""
    if not docs_root:
        docs_root = get_docs_root()

    conf_path = docs_root / "docs" / "maestro" / "repo" / "conf.json"

    if not conf_path.exists():
        return Finding(
            id="REPO_CONF_EXISTS",
            severity="warning",
            message="Repository configuration not found",
            details=f"Expected at {conf_path}",
            recommended_commands=[
                "maestro repo resolve",
                "maestro repo conf show"
            ]
        )

    # Check if file is valid JSON
    try:
        with open(conf_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Check for targets
        targets = data.get("targets", [])
        if not targets:
            return Finding(
                id="REPO_CONF_EXISTS",
                severity="warning",
                message="Repository configuration has no targets",
                recommended_commands=[
                    "maestro repo conf list",
                    "maestro repo conf show"
                ]
            )

        return Finding(
            id="REPO_CONF_EXISTS",
            severity="ok",
            message=f"Repository configuration exists with {len(targets)} target(s)"
        )
    except json.JSONDecodeError as e:
        return Finding(
            id="REPO_CONF_EXISTS",
            severity="error",
            message="Repository configuration is corrupted",
            details=str(e),
            recommended_commands=["maestro repo resolve"]
        )


def check_blocker_issues(docs_root: Optional[Path] = None) -> Finding:
    """Check 5: Blocker issues gate."""
    if not docs_root:
        docs_root = get_docs_root()

    try:
        from maestro.issues.json_store import list_issues_json
        from maestro.data import parse_phase_md
    except ImportError:
        return Finding(
            id="BLOCKED_BY_ISSUES",
            severity="ok",
            message="Issues module not available (skipped)"
        )

    repo_root = str(docs_root)

    # Get all open blocker issues
    blocker_issues = list_issues_json(repo_root, severity='blocker', status='open')

    if not blocker_issues:
        return Finding(
            id="BLOCKED_BY_ISSUES",
            severity="ok",
            message="No blocker issues found"
        )

    # Reuse work gate logic: only blockers without linked in-progress tasks block
    blocking_issues = []
    phases_dir = Path(repo_root) / "docs" / "phases"

    for issue in blocker_issues:
        has_in_progress_task = False

        if issue.linked_tasks and phases_dir.exists():
            for phase_file in phases_dir.glob("*.md"):
                try:
                    phase = parse_phase_md(str(phase_file))
                except Exception:
                    continue

                for task in phase.get("tasks", []):
                    task_id = task.get("task_id")
                    task_number = task.get("task_number")
                    task_matches = (task_id and task_id in issue.linked_tasks) or \
                                 (task_number and task_number in issue.linked_tasks)
                    if task_matches:
                        task_status = task.get("status", "").lower()
                        if task_status in ["in_progress", "in progress", "active"]:
                            has_in_progress_task = True
                            break
                if has_in_progress_task:
                    break

        if not has_in_progress_task:
            blocking_issues.append(issue)

    if not blocking_issues:
        return Finding(
            id="BLOCKED_BY_ISSUES",
            severity="ok",
            message="All blocker issues are linked to in-progress tasks"
        )

    # Count issues
    count = len(blocking_issues)
    top_issues = blocking_issues[:3]

    return Finding(
        id="BLOCKED_BY_ISSUES",
        severity="blocker",
        message=f"{count} open blocker issue(s) found",
        details=f"Top issues: {', '.join(i.issue_id for i in top_issues)}",
        recommended_commands=[
            "maestro issues list --severity blocker --status open",
            "maestro issues triage",
            "maestro work --ignore-gates  # bypass (use with caution)"
        ]
    )


def _load_sessions_for_doctor(docs_root: Optional[Path]) -> List[Any]:
    if not docs_root:
        docs_root = get_docs_root()
    base_path = Path(docs_root) / "docs" / "sessions"
    return list_sessions(base_path=base_path)


def check_subwork_orphans(docs_root: Optional[Path] = None) -> Finding:
    """Check for subwork sessions whose parent is missing."""
    sessions = _load_sessions_for_doctor(docs_root)
    if not sessions:
        return Finding(
            id="SUBWORK_ORPHANS",
            severity="ok",
            message="No subwork sessions found"
        )

    session_ids = {session.session_id for session in sessions}
    orphans = []
    for session in sessions:
        parent_id = session.parent_wsession_id or session.parent_session_id
        if parent_id and parent_id not in session_ids:
            orphans.append(session)

    if not orphans:
        return Finding(
            id="SUBWORK_ORPHANS",
            severity="ok",
            message="No orphan subwork sessions detected"
        )

    orphan_ids = sorted(session.session_id for session in orphans)
    details = ", ".join(orphan_ids[:5])
    if len(orphan_ids) > 5:
        details += f" (+{len(orphan_ids) - 5} more)"

    return Finding(
        id="SUBWORK_ORPHANS",
        severity="warning",
        message=f"{len(orphan_ids)} orphan subwork session(s) detected",
        details=f"Orphans: {details}",
        recommended_commands=[
            "maestro wsession tree",
            "maestro work subwork show <CHILD_WSESSION_ID>",
            "maestro work subwork close <CHILD_WSESSION_ID> --summary \"<summary>\"",
        ],
    )


def check_subwork_open_children(docs_root: Optional[Path] = None) -> Finding:
    """Check for parent sessions with open subwork children."""
    sessions = _load_sessions_for_doctor(docs_root)
    if not sessions:
        return Finding(
            id="SUBWORK_OPEN_CHILDREN",
            severity="ok",
            message="No subwork sessions found"
        )

    open_children = {}
    for session in sessions:
        parent_id = session.parent_wsession_id or session.parent_session_id
        if not parent_id:
            continue
        if session.state in {"running", "paused"}:
            open_children.setdefault(parent_id, []).append(session.session_id)

    if not open_children:
        return Finding(
            id="SUBWORK_OPEN_CHILDREN",
            severity="ok",
            message="No open subwork sessions detected"
        )

    detail_parts = []
    for parent_id in sorted(open_children):
        children = sorted(open_children[parent_id])
        detail_parts.append(f"{parent_id}: {', '.join(children)}")
    details = "; ".join(detail_parts)

    return Finding(
        id="SUBWORK_OPEN_CHILDREN",
        severity="warning",
        message="Parent sessions have open subwork children",
        details=details,
        recommended_commands=[
            "maestro wsession tree",
            "maestro work subwork list <PARENT_WSESSION_ID>",
            "maestro work subwork close <CHILD_WSESSION_ID> --summary \"<summary>\"",
        ],
    )


def run_doctor(strict: bool = False, ignore_gates: bool = False, docs_root: Optional[Path] = None) -> DoctorResult:
    """Run all doctor checks.

    Args:
        strict: Treat warnings as errors
        ignore_gates: Report gates but do not enforce them (downgrade blockers to warnings)
        docs_root: Override docs root for testing

    Returns:
        DoctorResult with findings and exit code
    """
    findings: List[Finding] = []

    # Run all checks
    findings.append(check_repo_lock(docs_root))
    git_root = str(docs_root) if docs_root else None
    findings.extend(check_git_status(git_root))
    findings.append(check_repo_truth(docs_root))
    findings.append(check_repo_conf(docs_root))
    findings.append(check_blocker_issues(docs_root))
    findings.append(check_subwork_orphans(docs_root))
    findings.append(check_subwork_open_children(docs_root))

    # If ignore_gates, downgrade blockers to warnings
    if ignore_gates:
        for finding in findings:
            if finding.severity == "blocker":
                finding.severity = "warning"

    # Determine exit code
    has_errors = any(f.severity == "error" for f in findings)
    has_blockers = any(f.severity == "blocker" for f in findings)
    has_warnings = any(f.severity == "warning" for f in findings)

    if has_blockers:
        exit_code = 2  # Fatal findings
    elif has_errors:
        exit_code = 2  # Fatal findings
    elif strict and has_warnings:
        exit_code = 2  # Strict mode: warnings become errors
    else:
        exit_code = 0

    return DoctorResult(findings=findings, exit_code=exit_code)


def format_text_output(result: DoctorResult) -> str:
    """Format doctor result as text."""
    lines = []
    lines.append("Maestro Ops Doctor")
    lines.append("=" * 70)
    lines.append("")

    # Group by severity
    by_severity = {
        "ok": [],
        "warning": [],
        "error": [],
        "blocker": []
    }
    for finding in result.findings:
        by_severity.get(finding.severity, []).append(finding)

    # Print blockers first
    if by_severity["blocker"]:
        lines.append("BLOCKERS")
        lines.append("-" * 70)
        for finding in by_severity["blocker"]:
            lines.append(f"❌ {finding.id}: {finding.message}")
            if finding.details:
                lines.append(f"   {finding.details}")
            if finding.recommended_commands:
                lines.append("   Recommended:")
                for cmd in finding.recommended_commands:
                    lines.append(f"     • {cmd}")
            lines.append("")

    # Then errors
    if by_severity["error"]:
        lines.append("ERRORS")
        lines.append("-" * 70)
        for finding in by_severity["error"]:
            lines.append(f"⛔ {finding.id}: {finding.message}")
            if finding.details:
                lines.append(f"   {finding.details}")
            if finding.recommended_commands:
                lines.append("   Recommended:")
                for cmd in finding.recommended_commands:
                    lines.append(f"     • {cmd}")
            lines.append("")

    # Then warnings
    if by_severity["warning"]:
        lines.append("WARNINGS")
        lines.append("-" * 70)
        for finding in by_severity["warning"]:
            lines.append(f"⚠️  {finding.id}: {finding.message}")
            if finding.details:
                lines.append(f"   {finding.details}")
            if finding.recommended_commands:
                lines.append("   Recommended:")
                for cmd in finding.recommended_commands:
                    lines.append(f"     • {cmd}")
            lines.append("")

    # Finally OK checks
    if by_severity["ok"]:
        lines.append("OK")
        lines.append("-" * 70)
        for finding in by_severity["ok"]:
            lines.append(f"✅ {finding.id}: {finding.message}")
        lines.append("")

    # Summary
    lines.append("=" * 70)
    lines.append(f"Summary: {len(result.findings)} checks")
    lines.append(f"  ✅ OK: {sum(1 for f in result.findings if f.severity == 'ok')}")
    lines.append(f"  ⚠️  Warnings: {sum(1 for f in result.findings if f.severity == 'warning')}")
    lines.append(f"  ⛔ Errors: {sum(1 for f in result.findings if f.severity == 'error')}")
    lines.append(f"  ❌ Blockers: {sum(1 for f in result.findings if f.severity == 'blocker')}")
    lines.append("")
    lines.append(f"Exit code: {result.exit_code}")

    return "\n".join(lines)
