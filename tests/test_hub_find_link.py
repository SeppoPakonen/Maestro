"""Tests for hub find and link operations.

Tests cover:
- Package finding with single match, ambiguous, and not found cases
- Link creation and validation
- Ambiguity handling
- Link removal
"""

import pytest
import tempfile
from pathlib import Path

from maestro.repo.hub.index import HubIndexManager, RepoRecord, PackageRecord
from maestro.repo.hub.link_store import HubLinkStore
from maestro.repo.hub.resolver import HubResolver, FindResult


class TestPackageFinding:
    """Test package finding functionality."""

    def test_find_package_single_match(self):
        """Finding a unique package should return SINGLE_MATCH."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = HubIndexManager(Path(tmpdir))

            # Add a repo with one package
            pkg = PackageRecord(
                pkg_id="sha256:abc123",
                name="UniquePackage",
                build_system="cmake",
                dir="/tmp/repo/UniquePackage"
            )
            repo = RepoRecord(
                repo_id="sha256:repo1",
                path="/tmp/repo",
                git_head=None,
                scan_timestamp="2025-01-01T00:00:00Z",
                packages=[pkg]
            )
            manager.add_repo(repo)

            # Find the package
            resolver = HubResolver()
            result, matches = resolver.find_package("UniquePackage")

            assert result == FindResult.SINGLE_MATCH
            assert len(matches) == 1
            assert matches[0].name == "UniquePackage"

    def test_find_package_not_found(self):
        """Finding a non-existent package should return NOT_FOUND."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = HubIndexManager(Path(tmpdir))

            # Add an empty repo
            repo = RepoRecord(
                repo_id="sha256:repo1",
                path="/tmp/repo",
                git_head=None,
                scan_timestamp="2025-01-01T00:00:00Z",
                packages=[]
            )
            manager.add_repo(repo)

            # Try to find a package
            resolver = HubResolver()
            result, matches = resolver.find_package("NonExistent")

            assert result == FindResult.NOT_FOUND
            assert len(matches) == 0

    def test_find_package_ambiguous(self):
        """Finding a package with multiple matches should return AMBIGUOUS."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = HubIndexManager(Path(tmpdir))

            # Add two repos with same package name
            pkg1 = PackageRecord(
                pkg_id="sha256:pkg1",
                name="Common",
                build_system="cmake",
                dir="/tmp/repo1/Common"
            )
            repo1 = RepoRecord(
                repo_id="sha256:repo1",
                path="/tmp/repo1",
                git_head=None,
                scan_timestamp="2025-01-01T00:00:00Z",
                packages=[pkg1]
            )

            pkg2 = PackageRecord(
                pkg_id="sha256:pkg2",
                name="Common",
                build_system="maven",
                dir="/tmp/repo2/Common"
            )
            repo2 = RepoRecord(
                repo_id="sha256:repo2",
                path="/tmp/repo2",
                git_head=None,
                scan_timestamp="2025-01-01T00:00:00Z",
                packages=[pkg2]
            )

            manager.add_repo(repo1)
            manager.add_repo(repo2)

            # Find the package
            resolver = HubResolver()
            result, matches = resolver.find_package("Common")

            assert result == FindResult.AMBIGUOUS
            assert len(matches) == 2
            # Should be sorted by dir
            assert matches[0].dir == "/tmp/repo1/Common"
            assert matches[1].dir == "/tmp/repo2/Common"

    def test_find_package_case_sensitive(self):
        """Package finding should be case-sensitive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = HubIndexManager(Path(tmpdir))

            pkg = PackageRecord(
                pkg_id="sha256:abc",
                name="MyPackage",
                build_system="upp",
                dir="/tmp/repo/MyPackage"
            )
            repo = RepoRecord(
                repo_id="sha256:repo",
                path="/tmp/repo",
                git_head=None,
                scan_timestamp="2025-01-01T00:00:00Z",
                packages=[pkg]
            )
            manager.add_repo(repo)

            resolver = HubResolver()

            # Exact match should work
            result, _ = resolver.find_package("MyPackage")
            assert result == FindResult.SINGLE_MATCH

            # Different case should not match
            result, _ = resolver.find_package("mypackage")
            assert result == FindResult.NOT_FOUND


class TestLinkCreation:
    """Test link creation and management."""

    def test_create_link_success(self):
        """Creating a link to an existing package should succeed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup hub index with a package
            hub_dir = Path(tmpdir) / "hub"
            hub_dir.mkdir()
            manager = HubIndexManager(hub_dir)

            pkg = PackageRecord(
                pkg_id="sha256:external_pkg",
                name="ExternalLib",
                build_system="cmake",
                dir="/tmp/other-repo/ExternalLib"
            )
            repo = RepoRecord(
                repo_id="sha256:other_repo",
                path="/tmp/other-repo",
                git_head="abc123",
                scan_timestamp="2025-01-01T00:00:00Z",
                packages=[pkg]
            )
            manager.add_repo(repo)

            # Create a local repo
            local_repo = Path(tmpdir) / "local-repo"
            local_repo.mkdir()

            # Create link
            resolver = HubResolver(str(local_repo))
            link = resolver.link_package(
                from_package="MyApp",
                to_package_id="sha256:external_pkg",
                reason="explicit"
            )

            assert link is not None
            assert link.from_package == "MyApp"
            assert link.to_package_id == "sha256:external_pkg"
            assert link.to_package_name == "ExternalLib"
            assert link.to_repo_path == "/tmp/other-repo"
            assert link.reason == "explicit"

    def test_create_link_package_not_found(self):
        """Creating a link to a non-existent package should return None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hub_dir = Path(tmpdir) / "hub"
            hub_dir.mkdir()
            HubIndexManager(hub_dir)  # Empty index

            local_repo = Path(tmpdir) / "local-repo"
            local_repo.mkdir()

            resolver = HubResolver(str(local_repo))
            link = resolver.link_package(
                from_package="MyApp",
                to_package_id="sha256:nonexistent",
                reason="explicit"
            )

            assert link is None

    def test_create_link_updates_existing(self):
        """Creating a link with same from/to should update existing link."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hub_dir = Path(tmpdir) / "hub"
            hub_dir.mkdir()
            manager = HubIndexManager(hub_dir)

            # Add two versions of a package
            pkg1 = PackageRecord(
                pkg_id="sha256:v1",
                name="Lib",
                build_system="cmake",
                dir="/tmp/repo1/Lib"
            )
            pkg2 = PackageRecord(
                pkg_id="sha256:v1",  # Same ID
                name="Lib_Updated",
                build_system="cmake",
                dir="/tmp/repo2/Lib"
            )

            repo1 = RepoRecord(
                repo_id="sha256:repo1",
                path="/tmp/repo1",
                git_head=None,
                scan_timestamp="2025-01-01T00:00:00Z",
                packages=[pkg1]
            )
            repo2 = RepoRecord(
                repo_id="sha256:repo2",
                path="/tmp/repo2",
                git_head=None,
                scan_timestamp="2025-01-02T00:00:00Z",
                packages=[pkg2]
            )

            manager.add_repo(repo1)

            local_repo = Path(tmpdir) / "local-repo"
            local_repo.mkdir()

            resolver = HubResolver(str(local_repo))

            # Create initial link
            link1 = resolver.link_package("MyApp", "sha256:v1", "test1")
            assert link1.to_package_name == "Lib"

            # Update to different repo
            manager.add_repo(repo2)
            link2 = resolver.link_package("MyApp", "sha256:v1", "test2")

            # Should have same link ID but updated info
            assert link2.link_id == link1.link_id
            assert link2.reason == "test2"

    def test_link_requires_repo_root(self):
        """Creating a link without repo root should raise ValueError."""
        resolver = HubResolver()  # No repo root

        with pytest.raises(ValueError, match="No repo root specified"):
            resolver.link_package("MyApp", "sha256:pkg", "explicit")


class TestLinkRetrieval:
    """Test link retrieval and resolution."""

    def test_get_link_for_package(self):
        """Getting a link for a specific package should work."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            store = HubLinkStore(str(repo_root))

            # Add a link
            link = store.add_link(
                from_package="MyApp",
                to_package_id="sha256:ext",
                to_package_name="ExtLib",
                to_repo_path="/tmp/other"
            )

            # Retrieve it
            retrieved = store.get_link_for_package("MyApp")
            assert retrieved is not None
            assert retrieved.link_id == link.link_id
            assert retrieved.from_package == "MyApp"

    def test_get_link_for_nonexistent_package(self):
        """Getting a link for a package with no link should return None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            store = HubLinkStore(str(repo_root))

            retrieved = store.get_link_for_package("NonExistent")
            assert retrieved is None

    def test_resolve_package_path(self):
        """Resolving a linked package should return its directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hub_dir = Path(tmpdir) / "hub"
            hub_dir.mkdir()
            manager = HubIndexManager(hub_dir)

            # Add a package to hub
            pkg = PackageRecord(
                pkg_id="sha256:lib",
                name="ExtLib",
                build_system="cmake",
                dir="/tmp/other-repo/ExtLib"
            )
            repo = RepoRecord(
                repo_id="sha256:other",
                path="/tmp/other-repo",
                git_head=None,
                scan_timestamp="2025-01-01T00:00:00Z",
                packages=[pkg]
            )
            manager.add_repo(repo)

            # Create local repo with link
            local_repo = Path(tmpdir) / "local"
            local_repo.mkdir()

            resolver = HubResolver(str(local_repo))
            resolver.link_package("MyApp", "sha256:lib")

            # Resolve the path
            path = resolver.resolve_package_path("MyApp")
            assert path == "/tmp/other-repo/ExtLib"

    def test_resolve_package_path_no_link(self):
        """Resolving a package with no link should return None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            local_repo = Path(tmpdir)
            resolver = HubResolver(str(local_repo))

            path = resolver.resolve_package_path("NonLinked")
            assert path is None

    def test_get_all_linked_package_roots(self):
        """Getting all linked roots should return list of directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hub_dir = Path(tmpdir) / "hub"
            hub_dir.mkdir()
            manager = HubIndexManager(hub_dir)

            # Add two packages
            pkg1 = PackageRecord(
                pkg_id="sha256:lib1",
                name="Lib1",
                build_system="cmake",
                dir="/tmp/repo1/Lib1"
            )
            pkg2 = PackageRecord(
                pkg_id="sha256:lib2",
                name="Lib2",
                build_system="upp",
                dir="/tmp/repo2/Lib2"
            )

            repo1 = RepoRecord(
                repo_id="sha256:r1",
                path="/tmp/repo1",
                git_head=None,
                scan_timestamp="2025-01-01T00:00:00Z",
                packages=[pkg1]
            )
            repo2 = RepoRecord(
                repo_id="sha256:r2",
                path="/tmp/repo2",
                git_head=None,
                scan_timestamp="2025-01-01T00:00:00Z",
                packages=[pkg2]
            )

            manager.add_repo(repo1)
            manager.add_repo(repo2)

            # Create links
            local_repo = Path(tmpdir) / "local"
            local_repo.mkdir()

            resolver = HubResolver(str(local_repo))
            resolver.link_package("App1", "sha256:lib1")
            resolver.link_package("App2", "sha256:lib2")

            # Get all roots
            roots = resolver.get_all_linked_package_roots()
            assert len(roots) == 2
            assert "/tmp/repo1/Lib1" in roots
            assert "/tmp/repo2/Lib2" in roots


class TestLinkRemoval:
    """Test link removal operations."""

    def test_remove_link_success(self):
        """Removing an existing link should succeed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            store = HubLinkStore(str(repo_root))

            # Add a link
            link = store.add_link(
                from_package="MyApp",
                to_package_id="sha256:ext",
                to_package_name="ExtLib",
                to_repo_path="/tmp/other"
            )

            # Remove it
            removed = store.remove_link(link.link_id)
            assert removed is True

            # Verify it's gone
            links = store.load_links()
            assert len(links) == 0

    def test_remove_link_not_found(self):
        """Removing a non-existent link should return False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            store = HubLinkStore(str(repo_root))

            removed = store.remove_link("sha256:nonexistent")
            assert removed is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
