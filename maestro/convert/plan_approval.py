"""Plan approval and run gating for convert pipelines."""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from maestro.config.paths import get_docs_root
from maestro.repo_lock import RepoLock


VALID_STATUSES = {
    "draft",
    "planned",
    "approved",
    "rejected",
    "running",
    "done",
    "failed",
}

ALLOWED_TRANSITIONS = {
    "draft": {"planned", "approved", "rejected"},
    "planned": {"approved", "rejected"},
    "approved": {"running"},
    "running": {"done", "failed"},
    "rejected": set(),
    "done": set(),
    "failed": set(),
}


class PlanStateError(RuntimeError):
    """Raised when a pipeline transitions to an invalid state."""


@dataclass
class RunResult:
    success: bool
    run_id: Optional[str] = None
    run_path: Optional[Path] = None


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _docs_root(repo_root: Optional[str] = None) -> Path:
    if repo_root:
        return Path(repo_root).resolve()
    return get_docs_root()


def _convert_root(repo_root: Optional[str] = None) -> Path:
    return _docs_root(repo_root) / "docs" / "maestro" / "convert"


def _pipeline_dir(pipeline_id: str, repo_root: Optional[str] = None) -> Path:
    _validate_pipeline_id(pipeline_id)
    return _convert_root(repo_root) / "pipelines" / pipeline_id


def _meta_path(pipeline_id: str, repo_root: Optional[str] = None) -> Path:
    return _pipeline_dir(pipeline_id, repo_root) / "meta.json"


def _plan_path(pipeline_id: str, repo_root: Optional[str] = None) -> Path:
    return _pipeline_dir(pipeline_id, repo_root) / "plan.json"


def _decision_path(pipeline_id: str, repo_root: Optional[str] = None) -> Path:
    return _pipeline_dir(pipeline_id, repo_root) / "decision.json"


def _runs_dir(pipeline_id: str, repo_root: Optional[str] = None) -> Path:
    return _pipeline_dir(pipeline_id, repo_root) / "runs"


def _run_dir(pipeline_id: str, run_id: str, repo_root: Optional[str] = None) -> Path:
    return _runs_dir(pipeline_id, repo_root) / run_id


def _atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", delete=False, dir=path.parent, suffix=".tmp") as tmp:
        json.dump(data, tmp, indent=2)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = tmp.name
    os.replace(tmp_path, path)


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _validate_pipeline_id(pipeline_id: str) -> None:
    if not pipeline_id or pipeline_id.strip() != pipeline_id:
        raise ValueError("Pipeline ID must be a non-empty string.")
    if os.path.sep in pipeline_id or (os.path.altsep and os.path.altsep in pipeline_id):
        raise ValueError(f"Invalid pipeline ID: {pipeline_id}")
    if ".." in pipeline_id:
        raise ValueError(f"Invalid pipeline ID: {pipeline_id}")


def _default_plan(pipeline_id: str, source_repo: str, target_repo: str) -> Dict[str, Any]:
    return {
        "pipeline_id": pipeline_id,
        "created_at": _now(),
        "updated_at": _now(),
        "steps": [
            {
                "step_id": "step-1",
                "title": "Review source and target scope",
                "artifacts": [],
                "expected_outputs": [],
            }
        ],
        "artifacts": [],
        "expected_outputs": [],
        "source_repo": source_repo,
        "target_repo": target_repo,
    }


def create_pipeline(
    pipeline_id: str,
    source_repo: Optional[str] = None,
    target_repo: Optional[str] = None,
    repo_root: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a pipeline meta/plan skeleton if it does not exist."""
    meta_path = _meta_path(pipeline_id, repo_root)
    existing = _load_json(meta_path)
    if existing:
        return existing

    repo_root = repo_root or os.getcwd()
    source_repo = str(Path(source_repo or repo_root).resolve())
    target_repo = str(Path(target_repo or repo_root).resolve())
    now = _now()
    meta = {
        "pipeline_id": pipeline_id,
        "status": "draft",
        "created_at": now,
        "updated_at": now,
        "source_repo": source_repo,
        "target_repo": target_repo,
    }
    _atomic_write_json(meta_path, meta)

    plan_path = _plan_path(pipeline_id, repo_root)
    if not plan_path.exists():
        _atomic_write_json(plan_path, _default_plan(pipeline_id, source_repo, target_repo))

    return meta


def load_meta(pipeline_id: str, repo_root: Optional[str] = None) -> Dict[str, Any]:
    meta = _load_json(_meta_path(pipeline_id, repo_root))
    if not meta:
        raise FileNotFoundError(f"Pipeline not found: {pipeline_id}")
    return meta


def load_plan(pipeline_id: str, repo_root: Optional[str] = None) -> Dict[str, Any]:
    plan = _load_json(_plan_path(pipeline_id, repo_root))
    if not plan:
        raise FileNotFoundError(f"Plan not found for pipeline: {pipeline_id}")
    return plan


def _update_status(meta: Dict[str, Any], new_status: str, allow_override: bool = False) -> bool:
    current = meta.get("status", "draft")
    if current == new_status:
        return False
    if new_status not in VALID_STATUSES:
        raise PlanStateError(f"Unknown status: {new_status}")
    if not allow_override and new_status not in ALLOWED_TRANSITIONS.get(current, set()):
        raise PlanStateError(f"Invalid transition: {current} -> {new_status}")
    meta["status"] = new_status
    meta["updated_at"] = _now()
    return True


def plan_conversion(
    pipeline_id: str,
    repo_root: Optional[str] = None,
    steps: Optional[list[dict]] = None,
    artifacts: Optional[list[str]] = None,
    expected_outputs: Optional[list[str]] = None,
) -> Dict[str, Any]:
    """Create or refresh plan.json and set status to planned."""
    meta = create_pipeline(pipeline_id, repo_root=repo_root)
    status = meta.get("status", "draft")
    if status not in {"draft", "planned"}:
        raise PlanStateError(f"Cannot plan pipeline in status: {status}")

    plan_path = _plan_path(pipeline_id, repo_root)
    existing_plan = _load_json(plan_path)
    source_repo = meta.get("source_repo", "")
    target_repo = meta.get("target_repo", "")
    plan = existing_plan or _default_plan(pipeline_id, source_repo, target_repo)
    plan["updated_at"] = _now()
    if steps is not None:
        plan["steps"] = steps
    if artifacts is not None:
        plan["artifacts"] = artifacts
    if expected_outputs is not None:
        plan["expected_outputs"] = expected_outputs
    _atomic_write_json(plan_path, plan)

    if _update_status(meta, "planned"):
        _atomic_write_json(_meta_path(pipeline_id, repo_root), meta)

    return plan


def approve_plan(
    pipeline_id: str,
    reason: Optional[str] = None,
    decided_by: str = "user",
    repo_root: Optional[str] = None,
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    meta = load_meta(pipeline_id, repo_root)
    status = meta.get("status", "draft")
    if status == "approved":
        return meta, None
    if status not in {"draft", "planned"}:
        raise PlanStateError(f"Cannot approve pipeline in status: {status}")

    plan_path = _plan_path(pipeline_id, repo_root)
    if not plan_path.exists():
        raise FileNotFoundError(f"Plan not found for pipeline: {pipeline_id}")

    decision = {
        "decision": "approved",
        "reason": reason or "",
        "decided_by": decided_by,
        "decided_at": _now(),
    }
    _atomic_write_json(_decision_path(pipeline_id, repo_root), decision)
    if _update_status(meta, "approved"):
        _atomic_write_json(_meta_path(pipeline_id, repo_root), meta)
    return meta, decision


def reject_plan(
    pipeline_id: str,
    reason: Optional[str] = None,
    decided_by: str = "user",
    repo_root: Optional[str] = None,
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    meta = load_meta(pipeline_id, repo_root)
    status = meta.get("status", "draft")
    if status == "rejected":
        return meta, None
    if status not in {"draft", "planned"}:
        raise PlanStateError(f"Cannot reject pipeline in status: {status}")

    plan_path = _plan_path(pipeline_id, repo_root)
    if not plan_path.exists():
        raise FileNotFoundError(f"Plan not found for pipeline: {pipeline_id}")

    decision = {
        "decision": "rejected",
        "reason": reason or "",
        "decided_by": decided_by,
        "decided_at": _now(),
    }
    _atomic_write_json(_decision_path(pipeline_id, repo_root), decision)
    if _update_status(meta, "rejected"):
        _atomic_write_json(_meta_path(pipeline_id, repo_root), meta)
    return meta, decision


def _gate_block_message(pipeline_id: str, status: str) -> None:
    print("============================================")
    print("GATE: CONVERT_PLAN_NOT_APPROVED")
    print("============================================")
    print(f"Pipeline {pipeline_id} is not approved (status: {status}).")
    print("Approve or reject the plan before running:")
    print(f"  maestro convert plan approve {pipeline_id} --reason \"...\"")
    print(f"  maestro convert plan reject {pipeline_id} --reason \"...\"")
    print("Or bypass gates explicitly:")
    print(f"  maestro convert run {pipeline_id} --ignore-gates")
    print()


def _warning_ignore_gates(pipeline_id: str, status: str) -> None:
    print(f"Warning: bypassing convert plan gates for {pipeline_id} (status: {status}).")


def _ensure_repo_root(repo_path: str) -> Path:
    path = Path(repo_path).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _workspace_fingerprint(repo_root: str) -> Optional[Dict[str, Any]]:
    import subprocess

    fingerprint: Dict[str, Any] = {}
    try:
        result = subprocess.run(
            ["git", "-C", repo_root, "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            fingerprint["git_head"] = result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    try:
        result = subprocess.run(
            ["git", "-C", repo_root, "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            fingerprint["git_dirty"] = bool(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    return fingerprint or None


def _create_run_id() -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    return f"run-{timestamp}"


def run_conversion_pipeline(
    pipeline_id: str,
    repo_root: Optional[str] = None,
    ignore_gates: bool = False,
) -> RunResult:
    meta = load_meta(pipeline_id, repo_root)
    status = meta.get("status", "draft")

    if not ignore_gates and status != "approved":
        _gate_block_message(pipeline_id, status)
        return RunResult(success=False)

    if ignore_gates and status != "approved":
        _warning_ignore_gates(pipeline_id, status)

    plan_path = _plan_path(pipeline_id, repo_root)
    if not plan_path.exists():
        print(f"Error: plan.json missing for pipeline {pipeline_id}.")
        return RunResult(success=False)

    source_repo = meta.get("source_repo") or (repo_root or os.getcwd())
    target_repo = meta.get("target_repo") or source_repo
    source_repo_path = _ensure_repo_root(source_repo)
    target_repo_path = _ensure_repo_root(target_repo)
    run_id = _create_run_id()
    session_id = f"convert-run-{pipeline_id}-{run_id}"

    source_lock = RepoLock(lock_dir=source_repo_path / "docs" / "maestro" / "locks")
    target_lock = None

    try:
        source_lock.acquire(session_id)
        if target_repo_path.resolve() != source_repo_path.resolve():
            target_lock = RepoLock(lock_dir=target_repo_path / "docs" / "maestro" / "locks")
            target_lock.acquire(session_id)

        run_dir = _run_dir(pipeline_id, run_id, repo_root=str(target_repo_path))
        run_dir.mkdir(parents=True, exist_ok=True)

        run_payload = {
            "run_id": run_id,
            "pipeline_id": pipeline_id,
            "status": "running",
            "started_at": _now(),
            "completed_at": None,
            "source_repo": str(source_repo_path),
            "target_repo": str(target_repo_path),
            "inputs": {
                "plan_path": str(plan_path),
            },
            "outputs": {
                "run_dir": str(run_dir),
            },
            "ignore_gates": bool(ignore_gates),
            "prompt_hash": None,
        }

        workspace_fp = _workspace_fingerprint(str(source_repo_path))
        if workspace_fp:
            run_payload["workspace_fingerprint"] = workspace_fp

        _atomic_write_json(run_dir / "run.json", run_payload)

        _update_status(meta, "running", allow_override=ignore_gates)
        _atomic_write_json(_meta_path(pipeline_id, repo_root), meta)

        run_payload["status"] = "done"
        run_payload["completed_at"] = _now()
        _atomic_write_json(run_dir / "run.json", run_payload)

        _update_status(meta, "done", allow_override=ignore_gates)
        _atomic_write_json(_meta_path(pipeline_id, repo_root), meta)
        return RunResult(success=True, run_id=run_id, run_path=run_dir)
    except Exception as exc:
        print(f"Error: convert run failed: {exc}")
        try:
            _update_status(meta, "failed", allow_override=True)
            _atomic_write_json(_meta_path(pipeline_id, repo_root), meta)
        except Exception:
            pass
        return RunResult(success=False)
    finally:
        if target_lock:
            target_lock.release(session_id)
        source_lock.release(session_id)
