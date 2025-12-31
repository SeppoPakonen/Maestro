"""Helpers for safe structure fix apply/revert workflows."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from maestro.modules.dataclasses import FixPlan, FixOperation, RenameOperation, WriteFileOperation


def _git_root_for_path(path: str) -> Optional[Path]:
    base = Path(path).resolve()
    if base.is_file() or not base.exists():
        base = base.parent
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=base,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    resolved = result.stdout.strip()
    return Path(resolved) if resolved else None


def is_git_repo(path: str) -> bool:
    """Return True if the path is inside a git repository."""
    return _git_root_for_path(path) is not None


def create_git_backup(session_path: str, patch_file: str) -> bool:
    """Capture the current git diff to a patch file."""
    repo_root = _git_root_for_path(session_path)
    if not repo_root:
        return False
    patch_path = Path(patch_file)
    patch_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "diff", "--binary"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False
    patch_path.write_text(result.stdout, encoding="utf-8")
    return True


def _remove_untracked(repo_root: Path) -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False
    for line in result.stdout.splitlines():
        if not line.startswith("?? "):
            continue
        rel_path = line[3:].strip()
        if not rel_path:
            continue
        target = repo_root / rel_path
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        else:
            try:
                target.unlink()
            except FileNotFoundError:
                continue
    return True


def restore_from_git(session_path: str) -> bool:
    """Restore tracked files and remove untracked files from the repo."""
    repo_root = _git_root_for_path(session_path)
    if not repo_root:
        return False
    result = subprocess.run(
        ["git", "restore", "--staged", "--worktree", "."],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False
    return _remove_untracked(repo_root)


def _apply_operation(operation: FixOperation) -> None:
    if isinstance(operation, WriteFileOperation):
        path = Path(operation.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(operation.content, encoding="utf-8")
        return
    if isinstance(operation, RenameOperation):
        source = Path(operation.from_path)
        target = Path(operation.to_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source, target)
        return
    raise ValueError(f"Unsupported operation: {operation.op}")


def apply_fix_plan_operations(fix_plan: FixPlan, verbose: bool = False) -> int:
    """Apply each operation in a FixPlan in order."""
    applied = 0
    total = len(fix_plan.operations)
    for idx, operation in enumerate(fix_plan.operations, start=1):
        if verbose:
            print(f"[maestro] op {idx}/{total} {operation.op}")
        _apply_operation(operation)
        applied += 1
    return applied


def _diagnostic_signatures(diagnostics: Iterable) -> tuple[set, set]:
    errors = set()
    warnings = set()
    for diag in diagnostics:
        severity = getattr(diag, "severity", "")
        signature = getattr(diag, "signature", None)
        if not signature:
            continue
        if severity == "error":
            errors.add(signature)
        elif severity == "warning":
            warnings.add(signature)
    return errors, warnings


def check_verification_improvement(before, after):
    """Compare diagnostics sets and determine improvement."""
    before_errors, before_warnings = _diagnostic_signatures(before)
    after_errors, after_warnings = _diagnostic_signatures(after)
    before_score = len(before_errors) * 2 + len(before_warnings)
    after_score = len(after_errors) * 2 + len(after_warnings)
    improved = after_score < before_score
    return {
        "improved": improved,
        "before": {"errors": len(before_errors), "warnings": len(before_warnings)},
        "after": {"errors": len(after_errors), "warnings": len(after_warnings)},
    }


def report_revert_action(structure_dir: str, reason: str) -> None:
    """Append a revert record to the structure fix report."""
    report_path = Path(structure_dir) / "revert_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if report_path.exists():
        data = json.loads(report_path.read_text(encoding="utf-8"))
    else:
        data = {"reverts": []}
    data["reverts"].append(
        {
            "type": "structure_fix_revert",
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        }
    )
    report_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
