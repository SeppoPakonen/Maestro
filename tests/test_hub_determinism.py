"""Tests for hub determinism guarantees.

These tests ensure that the hub system produces stable, deterministic
IDs for repos, packages, and links across multiple scans.
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from maestro.repo.hub.index import HubIndexManager, RepoRecord, PackageRecord
from maestro.repo.hub.link_store import HubLinkStore


class TestRepoIDStability:
    """Test repo ID determinism."""

    def test_repo_id_same_for_same_path(self):
        """Repo ID should be stable for same repo state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = HubIndexManager(Path(tmpdir))
            repo_path = "/tmp/test-repo"

            id1 = manager.compute_repo_id(repo_path)
            id2 = manager.compute_repo_id(repo_path)

            assert id1 == id2, "Repo ID should be deterministic for same path"

    def test_repo_id_format(self):
        """Repo ID should have correct format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = HubIndexManager(Path(tmpdir))
            repo_id = manager.compute_repo_id("/tmp/test-repo")

            assert repo_id.startswith("sha256:"), "Repo ID should start with 'sha256:'"
            assert len(repo_id) == 71, "Repo ID should be 'sha256:' + 64 hex chars"

    def test_different_paths_different_ids(self):
        """Different repo paths should produce different repo IDs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = HubIndexManager(Path(tmpdir))

            id1 = manager.compute_repo_id("/tmp/repo1")
            id2 = manager.compute_repo_id("/tmp/repo2")

            assert id1 != id2, "Different paths should produce different IDs"


class TestPackageIDStability:
    """Test package ID determinism."""

    def test_package_id_same_for_same_package(self):
        """Package ID should be stable for same package."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = HubIndexManager(Path(tmpdir))

            id1 = manager.compute_package_id("cmake", "MyLib", "/tmp/test-repo/MyLib")
            id2 = manager.compute_package_id("cmake", "MyLib", "/tmp/test-repo/MyLib")

            assert id1 == id2, "Package ID should be deterministic"

    def test_package_id_format(self):
        """Package ID should have correct format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = HubIndexManager(Path(tmpdir))
            pkg_id = manager.compute_package_id("cmake", "MyLib", "/tmp/test-repo/MyLib")

            assert pkg_id.startswith("sha256:"), "Package ID should start with 'sha256:'"
            assert len(pkg_id) == 71, "Package ID should be 'sha256:' + 64 hex chars"

    def test_different_names_different_ids(self):
        """Different package names should produce different IDs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = HubIndexManager(Path(tmpdir))

            id1 = manager.compute_package_id("cmake", "MyLib", "/tmp/test-repo/MyLib")
            id2 = manager.compute_package_id("cmake", "OtherLib", "/tmp/test-repo/OtherLib")

            assert id1 != id2, "Different names should produce different IDs"

    def test_different_build_systems_different_ids(self):
        """Different build systems should produce different IDs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = HubIndexManager(Path(tmpdir))

            id1 = manager.compute_package_id("cmake", "MyLib", "/tmp/test-repo/MyLib")
            id2 = manager.compute_package_id("upp", "MyLib", "/tmp/test-repo/MyLib")

            assert id1 != id2, "Different build systems should produce different IDs"

    def test_different_paths_different_ids(self):
        """Different package paths should produce different IDs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = HubIndexManager(Path(tmpdir))

            id1 = manager.compute_package_id("cmake", "MyLib", "/tmp/repo1/MyLib")
            id2 = manager.compute_package_id("cmake", "MyLib", "/tmp/repo2/MyLib")

            assert id1 != id2, "Different paths should produce different IDs"


class TestLinkIDStability:
    """Test link ID determinism."""

    def test_link_id_same_for_same_link(self):
        """Link ID should be stable for same from/to pair."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = HubLinkStore(tmpdir)

            # Compute link ID via internal method
            id1 = store._compute_link_id("MyApp", "sha256:abc123...")
            id2 = store._compute_link_id("MyApp", "sha256:abc123...")

            assert id1 == id2, "Link ID should be deterministic"

    def test_link_id_format(self):
        """Link ID should have correct format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = HubLinkStore(tmpdir)
            link_id = store._compute_link_id("MyApp", "sha256:abc123...")

            assert link_id.startswith("sha256:"), "Link ID should start with 'sha256:'"
            assert len(link_id) == 23, "Link ID should be 'sha256:' + 16 hex chars (truncated)"

    def test_different_from_different_ids(self):
        """Different from_package should produce different link IDs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = HubLinkStore(tmpdir)

            id1 = store._compute_link_id("MyApp", "sha256:abc...")
            id2 = store._compute_link_id("OtherApp", "sha256:abc...")

            assert id1 != id2, "Different from_package should produce different IDs"

    def test_different_to_different_ids(self):
        """Different to_package_id should produce different link IDs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = HubLinkStore(tmpdir)

            id1 = store._compute_link_id("MyApp", "sha256:abc...")
            id2 = store._compute_link_id("MyApp", "sha256:def...")

            assert id1 != id2, "Different to_package_id should produce different IDs"


class TestPackageSorting:
    """Test package search results sorting."""

    def test_packages_sorted_by_name_then_path(self):
        """Package search results should be sorted deterministically."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = HubIndexManager(Path(tmpdir))

            # Create multiple package records with same name
            pkg1 = PackageRecord(
                pkg_id="sha256:111",
                name="Common",
                build_system="cmake",
                dir="/home/user/repo2/Common"
            )
            pkg2 = PackageRecord(
                pkg_id="sha256:222",
                name="Common",
                build_system="upp",
                dir="/home/user/repo1/Common"
            )
            pkg3 = PackageRecord(
                pkg_id="sha256:333",
                name="Common",
                build_system="maven",
                dir="/home/user/repo3/Common"
            )

            # Add repos in random order
            repo1 = RepoRecord(
                repo_id="sha256:r1",
                path="/home/user/repo1",
                git_head=None,
                scan_timestamp="2025-01-01T00:00:00",
                packages=[pkg2]
            )
            repo2 = RepoRecord(
                repo_id="sha256:r2",
                path="/home/user/repo2",
                git_head=None,
                scan_timestamp="2025-01-01T00:00:00",
                packages=[pkg1]
            )
            repo3 = RepoRecord(
                repo_id="sha256:r3",
                path="/home/user/repo3",
                git_head=None,
                scan_timestamp="2025-01-01T00:00:00",
                packages=[pkg3]
            )

            manager.add_repo(repo3)  # Add in non-sorted order
            manager.add_repo(repo1)
            manager.add_repo(repo2)

            # Find packages - should be sorted by dir
            results = manager.find_packages_by_name("Common")

            assert len(results) == 3, "Should find all 3 packages"
            assert results[0].dir == "/home/user/repo1/Common", "Should be sorted by dir"
            assert results[1].dir == "/home/user/repo2/Common"
            assert results[2].dir == "/home/user/repo3/Common"


class TestIndexStability:
    """Test hub index stability across save/load cycles."""

    def test_index_round_trip_preserves_data(self):
        """Saving and loading index should preserve all data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = HubIndexManager(Path(tmpdir))

            # Create a repo record
            pkg = PackageRecord(
                pkg_id="sha256:abc123",
                name="TestPkg",
                build_system="cmake",
                dir="/tmp/test/TestPkg",
                dependencies=["Dep1", "Dep2"],
                metadata={"key": "value"}
            )
            repo = RepoRecord(
                repo_id="sha256:def456",
                path="/tmp/test",
                git_head="abc123commit",
                scan_timestamp="2025-01-01T00:00:00Z",
                packages=[pkg]
            )

            # Add repo
            manager.add_repo(repo)

            # Load index
            index = manager.load_index()

            assert "sha256:def456" in index.repos, "Repo should be in index"
            assert index.repos["sha256:def456"]["path"] == "/tmp/test"
            assert index.repos["sha256:def456"]["git_head"] == "abc123commit"
            assert index.repos["sha256:def456"]["packages_count"] == 1

            # Load repo record
            loaded_repo = manager.load_repo_record("sha256:def456")
            assert loaded_repo is not None, "Should load repo record"
            assert loaded_repo.repo_id == "sha256:def456"
            assert loaded_repo.path == "/tmp/test"
            assert len(loaded_repo.packages) == 1
            assert loaded_repo.packages[0].name == "TestPkg"
            assert loaded_repo.packages[0].dependencies == ["Dep1", "Dep2"]
            assert loaded_repo.packages[0].metadata == {"key": "value"}

    def test_package_index_updated_on_rescan(self):
        """Re-scanning a repo should update package index correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = HubIndexManager(Path(tmpdir))

            # First scan
            pkg1 = PackageRecord(
                pkg_id="sha256:old",
                name="TestPkg",
                build_system="cmake",
                dir="/tmp/test/TestPkg"
            )
            repo1 = RepoRecord(
                repo_id="sha256:repo",
                path="/tmp/test",
                git_head=None,
                scan_timestamp="2025-01-01T00:00:00Z",
                packages=[pkg1]
            )
            manager.add_repo(repo1)

            # Second scan with updated package
            pkg2 = PackageRecord(
                pkg_id="sha256:new",
                name="TestPkg",
                build_system="cmake",
                dir="/tmp/test/TestPkg"
            )
            repo2 = RepoRecord(
                repo_id="sha256:repo",
                path="/tmp/test",
                git_head="newcommit",
                scan_timestamp="2025-01-02T00:00:00Z",
                packages=[pkg2]
            )
            manager.add_repo(repo2)

            # Package index should have new package ID
            results = manager.find_packages_by_name("TestPkg")
            assert len(results) == 1, "Should have only one package"
            assert results[0].pkg_id == "sha256:new", "Should have updated package ID"


class TestLinkStoreStability:
    """Test link store stability."""

    def test_link_round_trip_preserves_data(self):
        """Saving and loading links should preserve all data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = HubLinkStore(tmpdir)

            # Add a link
            link = store.add_link(
                from_package="MyApp",
                to_package_id="sha256:abc123",
                to_package_name="Core",
                to_repo_path="/tmp/other-repo",
                reason="explicit",
                metadata={"note": "test"}
            )

            # Load links
            links = store.load_links()
            assert len(links) == 1, "Should have 1 link"
            assert links[0].from_package == "MyApp"
            assert links[0].to_package_id == "sha256:abc123"
            assert links[0].to_package_name == "Core"
            assert links[0].to_repo_path == "/tmp/other-repo"
            assert links[0].reason == "explicit"
            assert links[0].metadata == {"note": "test"}

    def test_updating_link_preserves_id(self):
        """Updating a link should preserve the link ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = HubLinkStore(tmpdir)

            # Add link
            link1 = store.add_link(
                from_package="MyApp",
                to_package_id="sha256:abc",
                to_package_name="OldCore",
                to_repo_path="/tmp/old"
            )

            # Update link (same from/to, different details)
            link2 = store.add_link(
                from_package="MyApp",
                to_package_id="sha256:abc",
                to_package_name="NewCore",
                to_repo_path="/tmp/new",
                reason="updated"
            )

            # Should have same link ID
            assert link1.link_id == link2.link_id, "Link ID should be stable across updates"

            # Should only have one link
            links = store.load_links()
            assert len(links) == 1, "Should have only 1 link after update"
            assert links[0].to_package_name == "NewCore", "Should have updated name"
            assert links[0].to_repo_path == "/tmp/new", "Should have updated path"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
