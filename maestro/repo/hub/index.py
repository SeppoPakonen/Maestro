"""Hub index manager for cross-repo package discovery.

This module manages the global hub index at ~/.maestro/hub/ which tracks
all previously scanned repositories and their packages. It provides
deterministic fingerprinting for repos and packages to ensure stable
references across scans.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import hashlib
import subprocess
import tempfile
import os
from datetime import datetime


@dataclass
class PackageRecord:
    """Record of a package in a repository."""
    pkg_id: str  # sha256 hash
    name: str
    build_system: str  # 'upp', 'cmake', 'cargo', 'python', etc.
    dir: str
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RepoRecord:
    """Record of a scanned repository."""
    repo_id: str  # sha256 hash
    path: str
    git_head: Optional[str]
    scan_timestamp: str
    packages: List[PackageRecord] = field(default_factory=list)


@dataclass
class LocalHubIndex:
    """Global index of local repositories and packages."""
    version: str = "1.0"
    updated_at: str = ""
    repos: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    packages_index: Dict[str, List[Dict[str, str]]] = field(default_factory=dict)


class HubIndexManager:
    """Manages the global hub index at ~/.maestro/hub/."""

    _default_hub_dir: Optional[Path] = None

    def __init__(self, hub_dir: Optional[Path] = None):
        """
        Initialize the hub index manager.

        Args:
            hub_dir: Hub directory path (default: ~/.maestro/hub)
        """
        if hub_dir is None:
            if self.__class__._default_hub_dir is not None:
                self.hub_dir = self.__class__._default_hub_dir
            else:
                self.hub_dir = Path.home() / ".maestro" / "hub"
        else:
            self.hub_dir = Path(hub_dir)
            self.__class__._default_hub_dir = self.hub_dir

        self.index_file = self.hub_dir / "index.json"
        self.repos_dir = self.hub_dir / "repos"
        self.packages_dir = self.hub_dir / "packages"

        # Create directories
        self.hub_dir.mkdir(parents=True, exist_ok=True)
        self.repos_dir.mkdir(exist_ok=True)
        self.packages_dir.mkdir(exist_ok=True)

    def load_index(self) -> LocalHubIndex:
        """Load hub index from disk."""
        if not self.index_file.exists():
            return LocalHubIndex()

        with open(self.index_file, 'r') as f:
            data = json.load(f)

        return LocalHubIndex(**data)

    def save_index(self, index: LocalHubIndex):
        """Save hub index to disk (atomic write)."""
        index.updated_at = datetime.now().isoformat()

        # Write to temp file first
        temp_file = self.index_file.with_suffix('.tmp')
        with open(temp_file, 'w') as f:
            json.dump({
                'version': index.version,
                'updated_at': index.updated_at,
                'repos': index.repos,
                'packages_index': index.packages_index
            }, f, indent=2)
            f.flush()
            os.fsync(f.fileno())

        # Atomic rename
        temp_file.replace(self.index_file)

    def compute_repo_id(self, repo_path: str) -> str:
        """
        Compute deterministic repo fingerprint.

        Formula: sha256(canonical_path + ":" + git_head + ":" + mtime_summary)

        Args:
            repo_path: Path to repository

        Returns:
            Repo ID in format "sha256:hexdigest"
        """
        canonical_path = Path(repo_path).resolve()

        # Get git HEAD if it's a git repo
        git_head = self._get_git_head(canonical_path)

        # Get top-level mtime summary
        mtime_summary = self._get_mtime_summary(canonical_path)

        # Hash: path + git_head + mtime
        fingerprint = f"{canonical_path}:{git_head}:{mtime_summary}"
        return "sha256:" + hashlib.sha256(fingerprint.encode()).hexdigest()

    def compute_package_id(self, build_system: str, name: str, package_root: str) -> str:
        """
        Compute deterministic package ID.

        Formula: sha256(build_system + ":" + name + ":" + normalized_root)

        Args:
            build_system: Package build system (upp, cmake, etc.)
            name: Package name
            package_root: Package root directory

        Returns:
            Package ID in format "sha256:hexdigest"
        """
        normalized_root = Path(package_root).resolve()
        fingerprint = f"{build_system}:{name}:{normalized_root}"
        return "sha256:" + hashlib.sha256(fingerprint.encode()).hexdigest()

    def add_repo(self, repo_record: RepoRecord):
        """
        Add or update a repository in the index.

        Args:
            repo_record: Repository record to add/update
        """
        index = self.load_index()

        # Update main index
        index.repos[repo_record.repo_id] = {
            'path': repo_record.path,
            'git_head': repo_record.git_head,
            'last_scanned': repo_record.scan_timestamp,
            'packages_count': len(repo_record.packages),
            'link': f"./repos/{repo_record.repo_id}.json"
        }

        # Update package index (for fast lookup by name)
        for pkg in repo_record.packages:
            if pkg.name not in index.packages_index:
                index.packages_index[pkg.name] = []

            # Remove old entries for this repo
            index.packages_index[pkg.name] = [
                entry for entry in index.packages_index[pkg.name]
                if entry['repo_id'] != repo_record.repo_id
            ]

            # Add new entry
            index.packages_index[pkg.name].append({
                'repo_id': repo_record.repo_id,
                'pkg_id': pkg.pkg_id
            })

            # Sort for determinism
            index.packages_index[pkg.name].sort(key=lambda x: (x['repo_id'], x['pkg_id']))

        # Save full repo record to separate file
        repo_file = self.repos_dir / f"{repo_record.repo_id}.json"
        temp_file = repo_file.with_suffix('.tmp')

        with open(temp_file, 'w') as f:
            json.dump({
                'repo_id': repo_record.repo_id,
                'path': repo_record.path,
                'git_head': repo_record.git_head,
                'scan_timestamp': repo_record.scan_timestamp,
                'packages': [
                    {
                        'pkg_id': pkg.pkg_id,
                        'name': pkg.name,
                        'build_system': pkg.build_system,
                        'dir': pkg.dir,
                        'dependencies': pkg.dependencies,
                        'metadata': pkg.metadata
                    } for pkg in repo_record.packages
                ]
            }, f, indent=2)
            f.flush()
            os.fsync(f.fileno())

        temp_file.replace(repo_file)

        self.save_index(index)

    def find_packages_by_name(self, name: str) -> List[PackageRecord]:
        """
        Find all packages matching the given name.

        Args:
            name: Package name to search for

        Returns:
            List of matching package records, sorted deterministically
        """
        index = self.load_index()

        if name not in index.packages_index:
            return []

        results = []
        for entry in index.packages_index[name]:
            repo_record = self.load_repo_record(entry['repo_id'])
            if repo_record:
                for pkg in repo_record.packages:
                    if pkg.pkg_id == entry['pkg_id']:
                        results.append(pkg)

        # Sort for determinism: by name, then by dir
        results.sort(key=lambda p: (p.name, p.dir))
        return results

    def load_repo_record(self, repo_id: str) -> Optional[RepoRecord]:
        """
        Load a full repo record from disk.

        Args:
            repo_id: Repository ID

        Returns:
            RepoRecord if found, None otherwise
        """
        repo_file = self.repos_dir / f"{repo_id}.json"
        if not repo_file.exists():
            return None

        with open(repo_file, 'r') as f:
            data = json.load(f)

        packages = [PackageRecord(**pkg) for pkg in data['packages']]
        return RepoRecord(
            repo_id=data['repo_id'],
            path=data['path'],
            git_head=data.get('git_head'),
            scan_timestamp=data['scan_timestamp'],
            packages=packages
        )

    def _get_git_head(self, repo_path: Path) -> Optional[str]:
        """
        Get git HEAD commit if repo is a git repository.

        Args:
            repo_path: Path to repository

        Returns:
            Commit hash or None if not a git repo
        """
        git_dir = repo_path / ".git"
        if not git_dir.exists():
            return None

        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def _get_mtime_summary(self, repo_path: Path) -> str:
        """
        Get top-level directory mtime summary.

        Uses repo_model.json mtime if it exists, otherwise returns "0".

        Args:
            repo_path: Path to repository

        Returns:
            Mtime summary as string
        """
        # Use repo_model.json mtime if it exists
        repo_model = repo_path / "docs" / "maestro" / "repo_model.json"
        if repo_model.exists():
            return str(int(repo_model.stat().st_mtime))
        return "0"
