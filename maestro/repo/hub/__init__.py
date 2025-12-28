"""
Cross-repository package discovery and linking system.

This package provides the infrastructure for discovering packages across
multiple repositories on the local machine and creating explicit links
between them for build-time dependency resolution.

Key Components:
- HubIndexManager: Manages global hub index (~/.maestro/hub/index.json)
- HubLinkStore: Manages per-repo link decisions (./docs/maestro/repo/hub_links.json)
- HubScanner: Scans repositories and updates hub index
- HubResolver: Finds packages and resolves links

See docs/workflows/v3/cli/REPO_HUB.md for complete documentation.
"""

from maestro.repo.hub.index import (
    HubIndexManager,
    LocalHubIndex,
    RepoRecord,
    PackageRecord,
)
from maestro.repo.hub.link_store import (
    HubLinkStore,
    HubLink,
)

__all__ = [
    'HubIndexManager',
    'LocalHubIndex',
    'RepoRecord',
    'PackageRecord',
    'HubLinkStore',
    'HubLink',
]
