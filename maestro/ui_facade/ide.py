"""IDE facade module for handling IDE-related operations."""

import json
from pathlib import Path
from typing import List, Optional

from maestro.ui_facade.repo import RepoPackageInfo, find_repo_root_from_path, list_repo_packages


def get_ide_state_file_path() -> Path:
    """Get the path to the IDE state file."""
    maestro_dir = Path.home() / ".maestro"
    maestro_dir.mkdir(parents=True, exist_ok=True)
    return maestro_dir / "ide_state.json"


def save_last_package_name(package_name: str) -> None:
    """Persist the last selected package name for IDE."""
    state_file = get_ide_state_file_path()
    state = {"last_package": package_name}
    with open(state_file, "w", encoding="utf-8") as file_handle:
        json.dump(state, file_handle)


def get_last_package_name() -> Optional[str]:
    """Get the last selected package name from persistent storage."""
    state_file = get_ide_state_file_path()
    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as file_handle:
                state = json.load(file_handle)
                return state.get("last_package")
        except (json.JSONDecodeError, OSError):
            return None
    return None


def _dependency_names(pkg: RepoPackageInfo) -> List[str]:
    """Extract dependency names from RepoPackageInfo."""
    deps: List[str] = []

    if getattr(pkg, "dependencies", None):
        for dep in pkg.dependencies:
            if dep:
                deps.append(str(dep))

    if getattr(pkg, "upp", None):
        uses = pkg.upp.get("uses", [])
        if isinstance(uses, list):
            for use_item in uses:
                if isinstance(use_item, str):
                    deps.append(use_item)
                elif isinstance(use_item, dict):
                    name = use_item.get("package") or use_item.get("name")
                    if name:
                        deps.append(name)
        elif isinstance(uses, str):
            deps.append(uses)

    return deps


def get_package_with_dependencies(target_package: str, repo_root: Optional[str] = None) -> List[RepoPackageInfo]:
    """Build a list of packages with dependencies for a target package.

    Returns target first followed by dependency packages in depth-first order without duplicates.
    """
    repo_root = repo_root or find_repo_root_from_path()
    packages = list_repo_packages(repo_root)
    packages_by_name = {pkg.name.lower(): pkg for pkg in packages}

    result: List[RepoPackageInfo] = []
    visited = set()

    def visit(pkg_name: str) -> None:
        key = pkg_name.lower()
        if key in visited:
            return
        pkg = packages_by_name.get(key)
        visited.add(key)
        if not pkg:
            return
        result.append(pkg)
        for dep_name in _dependency_names(pkg):
            visit(dep_name)

    visit(target_package)
    return result


def read_file_safely(file_path: str) -> str:
    """Read file contents safely, returning empty string on failure."""
    try:
        with open(file_path, "r", encoding="utf-8") as file_handle:
            return file_handle.read()
    except Exception:
        return ""
