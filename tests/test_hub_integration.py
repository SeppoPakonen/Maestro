"""End-to-end integration tests for hub system.

Tests the complete workflow:
1. Scan repositories
2. Find packages
3. Create links
4. Use links in build
"""

import pytest
import tempfile
import json
from pathlib import Path

from maestro.repo.hub.scanner import HubScanner
from maestro.repo.hub.resolver import HubResolver, FindResult
from maestro.repo.hub.index import HubIndexManager
from maestro.repo.hub.link_store import HubLinkStore


class TestEndToEndWorkflow:
    """Test complete hub workflow from scan to link."""

    def test_scan_and_find_workflow(self):
        """Complete workflow: scan repo, find package, create link."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup: Create two mock repositories
            hub_dir = Path(tmpdir) / ".maestro" / "hub"
            hub_dir.mkdir(parents=True)

            repo1_path = Path(tmpdir) / "repo1"
            repo1_path.mkdir()
            (repo1_path / "docs" / "maestro").mkdir(parents=True)

            # Create minimal repo_model.json for repo1
            repo1_model = {
                'packages_detected': [
                    {
                        'name': 'CoreLib',
                        'build_system': 'cmake',
                        'dir': str(repo1_path / 'CoreLib'),
                        'dependencies': []
                    }
                ]
            }
            with open(repo1_path / "docs" / "maestro" / "repo_model.json", 'w') as f:
                json.dump(repo1_model, f)

            repo2_path = Path(tmpdir) / "repo2"
            repo2_path.mkdir()
            (repo2_path / "docs" / "maestro").mkdir(parents=True)

            repo2_model = {
                'packages_detected': [
                    {
                        'name': 'MyApp',
                        'build_system': 'upp',
                        'dir': str(repo2_path / 'MyApp'),
                        'dependencies': ['CoreLib']
                    }
                ]
            }
            with open(repo2_path / "docs" / "maestro" / "repo_model.json", 'w') as f:
                json.dump(repo2_model, f)

            # Step 1: Scan both repositories
            scanner = HubScanner()
            scanner.hub_index = HubIndexManager(hub_dir)

            repo1_record = scanner.scan_repository(str(repo1_path))
            scanner.update_hub_index(repo1_record)

            repo2_record = scanner.scan_repository(str(repo2_path))
            scanner.update_hub_index(repo2_record)

            # Verify repos were added
            index = scanner.hub_index.load_index()
            assert len(index.repos) == 2

            # Step 2: Find CoreLib package
            resolver = HubResolver(str(repo2_path))
            resolver.hub_index = HubIndexManager(hub_dir)

            result, matches = resolver.find_package("CoreLib")
            assert result == FindResult.SINGLE_MATCH
            assert len(matches) == 1
            assert matches[0].name == "CoreLib"

            # Step 3: Create link from MyApp to CoreLib
            link = resolver.link_package(
                from_package="MyApp",
                to_package_id=matches[0].pkg_id,
                reason="explicit"
            )

            assert link is not None
            assert link.from_package == "MyApp"
            assert link.to_package_name == "CoreLib"

            # Step 4: Verify link was persisted
            link_store = HubLinkStore(str(repo2_path))
            links = link_store.load_links()
            assert len(links) == 1
            assert links[0].from_package == "MyApp"

            # Step 5: Resolve package roots for build
            roots = resolver.get_all_linked_package_roots()
            assert len(roots) == 1
            assert "CoreLib" in roots[0]

    def test_ambiguous_package_resolution(self):
        """Test handling of ambiguous package names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hub_dir = Path(tmpdir) / ".maestro" / "hub"
            hub_dir.mkdir(parents=True)

            # Create two repos with same package name
            repo1_path = Path(tmpdir) / "repo1"
            repo1_path.mkdir()
            (repo1_path / "docs" / "maestro").mkdir(parents=True)

            repo1_model = {
                'packages_detected': [
                    {
                        'name': 'Common',
                        'build_system': 'cmake',
                        'dir': str(repo1_path / 'Common'),
                        'dependencies': []
                    }
                ]
            }
            with open(repo1_path / "docs" / "maestro" / "repo_model.json", 'w') as f:
                json.dump(repo1_model, f)

            repo2_path = Path(tmpdir) / "repo2"
            repo2_path.mkdir()
            (repo2_path / "docs" / "maestro").mkdir(parents=True)

            repo2_model = {
                'packages_detected': [
                    {
                        'name': 'Common',
                        'build_system': 'maven',
                        'dir': str(repo2_path / 'Common'),
                        'dependencies': []
                    }
                ]
            }
            with open(repo2_path / "docs" / "maestro" / "repo_model.json", 'w') as f:
                json.dump(repo2_model, f)

            # Scan both repos
            scanner = HubScanner()
            scanner.hub_index = HubIndexManager(hub_dir)

            repo1_record = scanner.scan_repository(str(repo1_path))
            scanner.update_hub_index(repo1_record)

            repo2_record = scanner.scan_repository(str(repo2_path))
            scanner.update_hub_index(repo2_record)

            # Find Common package (should be ambiguous)
            resolver = HubResolver()
            resolver.hub_index = HubIndexManager(hub_dir)

            result, matches = resolver.find_package("Common")
            assert result == FindResult.AMBIGUOUS
            assert len(matches) == 2

            # Packages should be sorted by dir
            assert matches[0].dir < matches[1].dir

    def test_multiple_links_in_same_repo(self):
        """Test creating multiple links in one repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hub_dir = Path(tmpdir) / ".maestro" / "hub"
            hub_dir.mkdir(parents=True)

            # Create external repo with two libraries
            external_repo = Path(tmpdir) / "external"
            external_repo.mkdir()
            (external_repo / "docs" / "maestro").mkdir(parents=True)

            external_model = {
                'packages_detected': [
                    {
                        'name': 'Lib1',
                        'build_system': 'cmake',
                        'dir': str(external_repo / 'Lib1'),
                        'dependencies': []
                    },
                    {
                        'name': 'Lib2',
                        'build_system': 'cmake',
                        'dir': str(external_repo / 'Lib2'),
                        'dependencies': []
                    }
                ]
            }
            with open(external_repo / "docs" / "maestro" / "repo_model.json", 'w') as f:
                json.dump(external_model, f)

            # Create local repo
            local_repo = Path(tmpdir) / "local"
            local_repo.mkdir()
            (local_repo / "docs" / "maestro").mkdir(parents=True)

            local_model = {
                'packages_detected': [
                    {
                        'name': 'App',
                        'build_system': 'upp',
                        'dir': str(local_repo / 'App'),
                        'dependencies': ['Lib1', 'Lib2']
                    }
                ]
            }
            with open(local_repo / "docs" / "maestro" / "repo_model.json", 'w') as f:
                json.dump(local_model, f)

            # Scan external repo
            scanner = HubScanner()
            scanner.hub_index = HubIndexManager(hub_dir)

            external_record = scanner.scan_repository(str(external_repo))
            scanner.update_hub_index(external_record)

            # Create links to both libraries
            resolver = HubResolver(str(local_repo))
            resolver.hub_index = HubIndexManager(hub_dir)

            _, lib1_matches = resolver.find_package("Lib1")
            link1 = resolver.link_package("App", lib1_matches[0].pkg_id)

            _, lib2_matches = resolver.find_package("Lib2")
            link2 = resolver.link_package("App", lib2_matches[0].pkg_id)

            # Verify both links exist
            link_store = HubLinkStore(str(local_repo))
            links = link_store.load_links()
            assert len(links) == 2

            # Verify we can get all package roots
            roots = resolver.get_all_linked_package_roots()
            assert len(roots) == 2

    def test_rescan_updates_index(self):
        """Test that rescanning a repo updates the index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hub_dir = Path(tmpdir) / ".maestro" / "hub"
            hub_dir.mkdir(parents=True)

            repo_path = Path(tmpdir) / "repo"
            repo_path.mkdir()
            (repo_path / "docs" / "maestro").mkdir(parents=True)

            # Initial scan with one package
            initial_model = {
                'packages_detected': [
                    {
                        'name': 'Pkg1',
                        'build_system': 'cmake',
                        'dir': str(repo_path / 'Pkg1'),
                        'dependencies': []
                    }
                ]
            }
            with open(repo_path / "docs" / "maestro" / "repo_model.json", 'w') as f:
                json.dump(initial_model, f)

            scanner = HubScanner()
            scanner.hub_index = HubIndexManager(hub_dir)

            initial_record = scanner.scan_repository(str(repo_path))
            scanner.update_hub_index(initial_record)

            # Verify one package
            resolver = HubResolver()
            resolver.hub_index = HubIndexManager(hub_dir)
            _, matches = resolver.find_package("Pkg1")
            assert len(matches) == 1

            # Update repo with two packages
            updated_model = {
                'packages_detected': [
                    {
                        'name': 'Pkg1',
                        'build_system': 'cmake',
                        'dir': str(repo_path / 'Pkg1'),
                        'dependencies': []
                    },
                    {
                        'name': 'Pkg2',
                        'build_system': 'maven',
                        'dir': str(repo_path / 'Pkg2'),
                        'dependencies': []
                    }
                ]
            }
            with open(repo_path / "docs" / "maestro" / "repo_model.json", 'w') as f:
                json.dump(updated_model, f)

            # Rescan
            updated_record = scanner.scan_repository(str(repo_path))
            scanner.update_hub_index(updated_record)

            # Verify two packages now
            resolver_updated = HubResolver()
            resolver_updated.hub_index = HubIndexManager(hub_dir)

            _, pkg1_matches = resolver_updated.find_package("Pkg1")
            assert len(pkg1_matches) == 1

            _, pkg2_matches = resolver_updated.find_package("Pkg2")
            assert len(pkg2_matches) == 1


class TestLinkPersistence:
    """Test that links persist across sessions."""

    def test_links_survive_resolver_restart(self):
        """Links should persist when resolver is recreated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hub_dir = Path(tmpdir) / ".maestro" / "hub"
            hub_dir.mkdir(parents=True)

            # Create and scan a repo
            external_repo = Path(tmpdir) / "external"
            external_repo.mkdir()
            (external_repo / "docs" / "maestro").mkdir(parents=True)

            external_model = {
                'packages_detected': [
                    {
                        'name': 'PersistentLib',
                        'build_system': 'cmake',
                        'dir': str(external_repo / 'PersistentLib'),
                        'dependencies': []
                    }
                ]
            }
            with open(external_repo / "docs" / "maestro" / "repo_model.json", 'w') as f:
                json.dump(external_model, f)

            scanner = HubScanner()
            scanner.hub_index = HubIndexManager(hub_dir)
            external_record = scanner.scan_repository(str(external_repo))
            scanner.update_hub_index(external_record)

            # Create local repo and link
            local_repo = Path(tmpdir) / "local"
            local_repo.mkdir()

            resolver1 = HubResolver(str(local_repo))
            resolver1.hub_index = HubIndexManager(hub_dir)

            _, matches = resolver1.find_package("PersistentLib")
            link1 = resolver1.link_package("MyApp", matches[0].pkg_id)

            # Create new resolver (simulating restart)
            resolver2 = HubResolver(str(local_repo))
            resolver2.hub_index = HubIndexManager(hub_dir)

            # Verify link still exists
            link_from_store = resolver2.link_store.get_link_for_package("MyApp")
            assert link_from_store is not None
            assert link_from_store.link_id == link1.link_id

            # Verify we can still resolve paths
            path = resolver2.resolve_package_path("MyApp")
            assert path is not None
            assert "PersistentLib" in path


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
