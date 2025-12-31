"""Hub scanner for discovering packages in repositories.

This module scans repositories and updates the hub index with package
information. It supports both maestro-initialized repos (with repo_model.json)
and arbitrary directories (performs lightweight scan).
"""

from pathlib import Path
from typing import Optional
from datetime import datetime

from maestro.repo.hub.index import HubIndexManager, RepoRecord, PackageRecord
from maestro.repo.storage import load_repo_model


class HubScanner:
    """Scans repositories and updates hub index."""

    def __init__(self):
        """Initialize the hub scanner."""
        self.hub_index = HubIndexManager()

    def scan_repository(self, repo_path: str, verbose: bool = False) -> RepoRecord:
        """
        Scan a repository and return a RepoRecord.

        This method can scan both maestro-initialized repos (with
        docs/maestro/repo_model.json) and arbitrary directories.

        Args:
            repo_path: Path to repository
            verbose: Show detailed scan progress

        Returns:
            RepoRecord containing scanned package information
        """
        repo_path_obj = Path(repo_path).resolve()

        # Check if repo has been scanned (repo_model.json exists)
        repo_model_path = repo_path_obj / "docs" / "maestro" / "repo_model.json"

        if repo_model_path.exists():
            # Load from existing repo_model.json
            if verbose:
                print(f"Loading repo model from {repo_model_path}")
            repo_model = load_repo_model(str(repo_path_obj))
        else:
            # Perform scan
            if verbose:
                print(f"Scanning repository: {repo_path}")

            # Import here to avoid circular dependency
            from maestro.repo.scanner import scan_upp_repo_v2

            scan_result = scan_upp_repo_v2(
                str(repo_path_obj),
                verbose=verbose,
                include_user_config=False,
                collect_files=False,  # Don't need full file list for hub index
                scan_unknown_paths=False  # Skip unknown paths for speed
            )

            # Convert scan result to dict format
            repo_model = {
                'packages_detected': [
                    {
                        'name': pkg.name,
                        'build_system': pkg.build_system,
                        'dir': pkg.dir,
                        'dependencies': getattr(pkg, 'dependencies', [])
                    } for pkg in scan_result.packages_detected
                ]
            }

        # Compute repo ID
        repo_id = self.hub_index.compute_repo_id(str(repo_path_obj))

        # Build package records
        packages = []
        for pkg_data in repo_model.get('packages_detected', []):
            pkg_id = self.hub_index.compute_package_id(
                pkg_data['build_system'],
                pkg_data['name'],
                pkg_data['dir']
            )

            packages.append(PackageRecord(
                pkg_id=pkg_id,
                name=pkg_data['name'],
                build_system=pkg_data['build_system'],
                dir=pkg_data['dir'],
                dependencies=pkg_data.get('dependencies', []),
                metadata={}
            ))

        # Create repo record
        repo_record = RepoRecord(
            repo_id=repo_id,
            path=str(repo_path_obj),
            git_head=self.hub_index._get_git_head(repo_path_obj),
            scan_timestamp=datetime.now().isoformat(),
            packages=packages
        )

        return repo_record

    def update_hub_index(self, repo_record: RepoRecord, verbose: bool = False):
        """
        Update the global hub index with repo record.

        Args:
            repo_record: Repository record to add/update
            verbose: Show progress messages
        """
        if verbose:
            print(f"Updating hub index: {repo_record.repo_id}")
            print(f"  Path: {repo_record.path}")
            print(f"  Packages: {len(repo_record.packages)}")

        self.hub_index.add_repo(repo_record)

        if verbose:
            print(f"Hub index updated successfully")
