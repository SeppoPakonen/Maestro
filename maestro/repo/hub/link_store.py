"""Hub link store for managing cross-repo package links.

This module manages per-repository link decisions stored in
./docs/maestro/repo/hub_links.json. Each link represents an explicit
dependency from a local package to an external package in another repo.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
import json
import hashlib
import tempfile
import os
from datetime import datetime


@dataclass
class HubLink:
    """Represents a link from local package to external package."""
    link_id: str
    from_package: str  # Local package name
    to_package_id: str  # External package ID (sha256)
    to_package_name: str
    to_repo_path: str
    created_at: str
    reason: str  # 'explicit', 'auto', 'inferred'
    metadata: Dict[str, Any] = field(default_factory=dict)


class HubLinkStore:
    """Manages hub links for a repository."""

    def __init__(self, repo_root: str):
        """
        Initialize the link store.

        Args:
            repo_root: Path to repository root
        """
        self.repo_root = Path(repo_root)
        self.links_file = self.repo_root / "docs" / "maestro" / "repo" / "hub_links.json"

        # Ensure parent directory exists
        self.links_file.parent.mkdir(parents=True, exist_ok=True)

    def load_links(self) -> List[HubLink]:
        """
        Load all links from store.

        Returns:
            List of hub links
        """
        if not self.links_file.exists():
            return []

        with open(self.links_file, 'r') as f:
            data = json.load(f)

        return [HubLink(**link) for link in data.get('links', [])]

    def save_links(self, links: List[HubLink]):
        """
        Save links to store (atomic write).

        Args:
            links: List of hub links to save
        """
        data = {
            'version': '1.0',
            'links': [
                {
                    'link_id': link.link_id,
                    'from_package': link.from_package,
                    'to_package_id': link.to_package_id,
                    'to_package_name': link.to_package_name,
                    'to_repo_path': link.to_repo_path,
                    'created_at': link.created_at,
                    'reason': link.reason,
                    'metadata': link.metadata
                } for link in links
            ]
        }

        # Atomic write
        temp_file = self.links_file.with_suffix('.tmp')
        with open(temp_file, 'w') as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        temp_file.replace(self.links_file)

    def add_link(self, from_package: str, to_package_id: str, to_package_name: str,
                 to_repo_path: str, reason: str = 'explicit', metadata: Optional[Dict[str, Any]] = None) -> HubLink:
        """
        Add a new link.

        If a link with the same ID already exists, it will be updated.

        Args:
            from_package: Local package name
            to_package_id: External package ID
            to_package_name: External package name
            to_repo_path: Path to repository containing external package
            reason: Reason for link (default: 'explicit')
            metadata: Optional additional metadata

        Returns:
            The created or updated HubLink
        """
        links = self.load_links()

        # Generate link ID
        link_id = self._compute_link_id(from_package, to_package_id)

        # Check if link already exists
        for link in links:
            if link.link_id == link_id:
                # Update existing link
                link.to_package_name = to_package_name
                link.to_repo_path = to_repo_path
                link.reason = reason
                link.metadata = metadata or {}
                self.save_links(links)
                return link

        # Create new link
        new_link = HubLink(
            link_id=link_id,
            from_package=from_package,
            to_package_id=to_package_id,
            to_package_name=to_package_name,
            to_repo_path=to_repo_path,
            created_at=datetime.now().isoformat(),
            reason=reason,
            metadata=metadata or {}
        )

        links.append(new_link)
        self.save_links(links)
        return new_link

    def remove_link(self, link_id: str) -> bool:
        """
        Remove a link by ID.

        Args:
            link_id: Link ID to remove

        Returns:
            True if link was removed, False if not found
        """
        links = self.load_links()
        original_count = len(links)
        links = [link for link in links if link.link_id != link_id]

        if len(links) < original_count:
            self.save_links(links)
            return True
        return False

    def get_link_for_package(self, package_name: str) -> Optional[HubLink]:
        """
        Get link for a specific package.

        Args:
            package_name: Package name to find link for

        Returns:
            HubLink if found, None otherwise
        """
        links = self.load_links()
        for link in links:
            if link.from_package == package_name:
                return link
        return None

    def _compute_link_id(self, from_package: str, to_package_id: str) -> str:
        """
        Compute deterministic link ID.

        Formula: sha256(from_package + ":" + to_package_id)[:16]

        Args:
            from_package: Local package name
            to_package_id: External package ID

        Returns:
            Link ID in format "sha256:hexdigest" (truncated to 16 chars)
        """
        fingerprint = f"{from_package}:{to_package_id}"
        full_hash = hashlib.sha256(fingerprint.encode()).hexdigest()
        return "sha256:" + full_hash[:16]
