"""Hub resolver for finding and linking packages.

This module provides package discovery and linking functionality across
repositories using the hub index. It handles ambiguity detection and
provides resolved package paths for build integration.
"""

from typing import List, Optional, Tuple
from enum import Enum

from maestro.repo.hub.index import HubIndexManager, PackageRecord
from maestro.repo.hub.link_store import HubLinkStore, HubLink


class FindResult(Enum):
    """Result type from package find operation."""
    NOT_FOUND = "not_found"
    SINGLE_MATCH = "single_match"
    AMBIGUOUS = "ambiguous"


class HubResolver:
    """Resolves package dependencies using hub index."""

    def __init__(self, repo_root: Optional[str] = None):
        """
        Initialize the hub resolver.

        Args:
            repo_root: Repository root for link store (optional)
        """
        self.hub_index = HubIndexManager()
        self.repo_root = repo_root
        if repo_root:
            self.link_store = HubLinkStore(repo_root)
        else:
            self.link_store = None

    def find_package(self, package_name: str) -> Tuple[FindResult, List[PackageRecord]]:
        """
        Find package across all repos in hub index.

        Args:
            package_name: Package name to search for

        Returns:
            Tuple of (FindResult, List[PackageRecord])
            - NOT_FOUND: Empty list
            - SINGLE_MATCH: List with one package
            - AMBIGUOUS: List with multiple packages
        """
        matches = self.hub_index.find_packages_by_name(package_name)

        if not matches:
            return FindResult.NOT_FOUND, []
        elif len(matches) == 1:
            return FindResult.SINGLE_MATCH, matches
        else:
            return FindResult.AMBIGUOUS, matches

    def link_package(self, from_package: str, to_package_id: str,
                    reason: str = 'explicit') -> Optional[HubLink]:
        """
        Create a link from local package to external package.

        Args:
            from_package: Local package name
            to_package_id: External package ID
            reason: Reason for link (default: 'explicit')

        Returns:
            HubLink if successful, None if target package not found

        Raises:
            ValueError: If no repo root specified for link store
        """
        if not self.link_store:
            raise ValueError("No repo root specified for link store")

        # Find the target package in the hub index
        index = self.hub_index.load_index()

        # Search all repos for this package ID
        target_pkg = None
        target_repo_record = None

        for repo_id, repo_info in index.repos.items():
            repo_record = self.hub_index.load_repo_record(repo_id)
            if repo_record:
                for pkg in repo_record.packages:
                    if pkg.pkg_id == to_package_id:
                        target_pkg = pkg
                        target_repo_record = repo_record
                        break
            if target_pkg:
                break

        if not target_pkg or not target_repo_record:
            return None

        # Create link
        link = self.link_store.add_link(
            from_package=from_package,
            to_package_id=to_package_id,
            to_package_name=target_pkg.name,
            to_repo_path=target_repo_record.path,
            reason=reason
        )

        return link

    def resolve_package_path(self, package_name: str) -> Optional[str]:
        """
        Resolve package to its directory path using hub links.

        Args:
            package_name: Package name to resolve

        Returns:
            Package directory path if linked, None otherwise
        """
        if not self.link_store:
            return None

        # Check if there's an explicit link
        link = self.link_store.get_link_for_package(package_name)
        if not link:
            return None

        # Load the linked package to get its directory
        index = self.hub_index.load_index()
        for repo_id, repo_info in index.repos.items():
            repo_record = self.hub_index.load_repo_record(repo_id)
            if repo_record:
                for pkg in repo_record.packages:
                    if pkg.pkg_id == link.to_package_id:
                        return pkg.dir

        return None

    def get_all_linked_package_roots(self) -> List[str]:
        """
        Get all package roots from hub links.

        This is used by the build system to add external package
        directories to compiler include paths.

        Returns:
            List of package directory paths
        """
        if not self.link_store:
            return []

        links = self.link_store.load_links()
        roots = []

        index = self.hub_index.load_index()
        for link in links:
            # Find the package directory for this link
            for repo_id, repo_info in index.repos.items():
                repo_record = self.hub_index.load_repo_record(repo_id)
                if repo_record:
                    for pkg in repo_record.packages:
                        if pkg.pkg_id == link.to_package_id:
                            roots.append(pkg.dir)
                            break

        return roots
