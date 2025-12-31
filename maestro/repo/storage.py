"""Repository storage helpers for v3 repo truth invariants."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from maestro.modules.utils import print_error

REPO_TRUTH_REL = Path("docs") / "maestro"
REPO_MODEL_FILENAME = "repo_model.json"
REPO_STATE_FILENAME = "repo_state.json"
REPOCONF_FILENAME = "repoconf.json"


def find_repo_root(start_path: Optional[str] = None) -> str:
    """Find the repo root by locating docs/maestro; forbid .maestro usage."""
    current = Path(start_path or os.getcwd()).resolve()

    while current != current.parent:
        if (current / REPO_TRUTH_REL).is_dir():
            return str(current)
        if (current / ".maestro").is_dir():
            _raise_dot_maestro_error(current)
        current = current.parent

    if (current / REPO_TRUTH_REL).is_dir():
        return str(current)
    if (current / ".maestro").is_dir():
        _raise_dot_maestro_error(current)

    print_error("Could not find docs/maestro/ directory.", 2)
    print_error("Run 'maestro init' first to initialize the repository.", 2)
    raise SystemExit(1)


def ensure_repo_truth_dir(repo_root: Optional[str] = None, create: bool = False) -> Path:
    """Ensure repo truth directory exists and .maestro is not used."""
    root = Path(repo_root or os.getcwd()).resolve()
    repo_truth = root / REPO_TRUTH_REL
    if not create:
        if not repo_truth.exists():
            _reject_dot_maestro(root)
    if not repo_truth.exists():
        if create:
            repo_truth.mkdir(parents=True, exist_ok=True)
        else:
            print_error("Repo truth missing: docs/maestro/ not found.", 2)
            print_error("Run 'maestro init' to create repo truth.", 2)
            raise SystemExit(1)
    return repo_truth


def repo_model_path(repo_root: Optional[str] = None, require: bool = False) -> Path:
    """Return path to repo_model.json, optionally requiring it to exist."""
    repo_truth = ensure_repo_truth_dir(repo_root)
    path = repo_truth / REPO_MODEL_FILENAME
    if require and not path.exists():
        print_error(f"Repository model not found: {path}", 2)
        print_error("Run 'maestro repo resolve' first to scan the repository.", 2)
        raise SystemExit(1)
    return path


def repoconf_path(repo_root: Optional[str] = None, require: bool = False) -> Path:
    """Return path to repoconf.json, optionally requiring it to exist."""
    repo_truth = ensure_repo_truth_dir(repo_root)
    path = repo_truth / REPOCONF_FILENAME
    if require and not path.exists():
        print_error(f"RepoConf not found: {path}", 2)
        print_error("Run 'maestro repo conf select-default target <TARGET>' first.", 2)
        raise SystemExit(1)
    return path


def write_repo_model(repo_root: str, model_data: Dict[str, Any]) -> Path:
    """Write repo model data to repo_model.json (atomic)."""
    repo_truth = ensure_repo_truth_dir(repo_root, create=True)
    path = repo_truth / REPO_MODEL_FILENAME
    _atomic_write_json(path, model_data)
    return path


def write_repo_state(repo_root: str, state_data: Dict[str, Any]) -> Path:
    """Write repo state metadata to repo_state.json (atomic)."""
    repo_truth = ensure_repo_truth_dir(repo_root, create=True)
    path = repo_truth / REPO_STATE_FILENAME
    _atomic_write_json(path, state_data)
    return path


def load_repo_model(repo_root: Optional[str] = None) -> Dict[str, Any]:
    """Load repo model data from repo_model.json."""
    path = repo_model_path(repo_root, require=True)
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_repoconf(repo_root: Optional[str] = None) -> Dict[str, Any]:
    """Load repoconf.json if present."""
    path = repoconf_path(repo_root, require=True)
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def save_repoconf(repo_root: str, repoconf: Dict[str, Any]) -> Path:
    """Write repoconf.json to repo truth."""
    repo_truth = ensure_repo_truth_dir(repo_root)
    path = repo_truth / REPOCONF_FILENAME
    _atomic_write_json(path, repoconf)
    return path


def require_repo_model(repo_root: Optional[str] = None) -> Path:
    """Return repo_model.json path, failing if missing."""
    return repo_model_path(repo_root, require=True)


def ensure_repoconf_target(repo_root: Optional[str] = None) -> Dict[str, Any]:
    """Load repoconf and ensure selected_target exists."""
    repoconf = load_repoconf(repo_root)
    if not repoconf.get("selected_target"):
        print_error("RepoConf missing selected target.", 2)
        print_error("Run 'maestro repo conf select-default target <TARGET>' first.", 2)
        raise SystemExit(1)
    return repoconf


def _atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", delete=False, dir=path.parent, suffix=".tmp") as tmp:
        json.dump(data, tmp, indent=2)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = tmp.name
    os.replace(tmp_path, path)


def _reject_dot_maestro(repo_root: Path) -> None:
    dot_maestro = repo_root / ".maestro"
    if dot_maestro.exists():
        _raise_dot_maestro_error(repo_root)


def _raise_dot_maestro_error(repo_root: Path) -> None:
    print_error(f"Forbidden repo state path detected: {repo_root / '.maestro'}", 2)
    print_error("Use ./docs/maestro/ (repo truth) instead.", 2)
    raise SystemExit(1)


def default_repo_state(repo_root: str, model_path: Path, scan_counts: Dict[str, int]) -> Dict[str, Any]:
    """Create a minimal repo state metadata payload."""
    return {
        "last_resolved_at": datetime.now().isoformat(),
        "repo_root": repo_root,
        "repo_model_path": str(model_path),
        "packages_count": scan_counts.get("packages", 0),
        "assemblies_count": scan_counts.get("assemblies", 0),
        "user_assemblies_count": scan_counts.get("user_assemblies", 0),
        "internal_packages_count": scan_counts.get("internal_packages", 0),
        "unknown_count": scan_counts.get("unknown_paths", 0),
        "scanner_version": "0.9.0"
    }
