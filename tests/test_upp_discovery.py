#!/usr/bin/env python3
"""
Test suite for U++ package/assembly discovery conformance.
"""

import os
import sys
import unittest
from pathlib import Path

# Add the maestro module to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from maestro.main import scan_upp_repo, resolve_upp_dependencies, UppRepoIndex


class TestUppDiscovery(unittest.TestCase):
    """Test U++ package/assembly discovery functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.fixture_dir = os.path.join(os.path.dirname(__file__), 'fixtures', 'upp_workspace')
    
    def test_scan_single_assembly(self):
        """Test scanning a single assembly."""
        assembly_path = os.path.join(self.fixture_dir, 'assemblyA')
        repo_index = scan_upp_repo(assembly_path, verbose=False)
        
        # Should find 1 package in assemblyA
        self.assertEqual(len(repo_index.assemblies), 1)
        self.assertEqual(len(repo_index.packages), 1)
        self.assertEqual(repo_index.packages[0].name, 'PkgX')
        self.assertTrue(repo_index.packages[0].dir_path.endswith('PkgX'))
        
    def test_scan_multiple_assemblies(self):
        """Test scanning multiple assemblies."""
        assemblies = [
            os.path.join(self.fixture_dir, 'assemblyA'),
            os.path.join(self.fixture_dir, 'assemblyB')
        ]
        repo_index = scan_upp_repo(self.fixture_dir, verbose=False, assemblies=assemblies)
        
        # Should find both assemblies
        self.assertEqual(len(repo_index.assemblies), 2)
        
        # Should find all packages: PkgX, PkgY, PkgX2
        self.assertEqual(len(repo_index.packages), 3)
        package_names = {pkg.name for pkg in repo_index.packages}
        self.assertEqual(package_names, {'PkgX', 'PkgY', 'PkgX2'})
    
    def test_deterministic_search_order(self):
        """Test that search order is deterministic."""
        assemblies = [
            os.path.join(self.fixture_dir, 'assemblyB'),
            os.path.join(self.fixture_dir, 'assemblyA')
        ]
        repo_index1 = scan_upp_repo(self.fixture_dir, verbose=False, assemblies=assemblies)
        
        # Reverse the order to ensure deterministic results
        assemblies_reversed = [
            os.path.join(self.fixture_dir, 'assemblyA'),
            os.path.join(self.fixture_dir, 'assemblyB')
        ]
        repo_index2 = scan_upp_repo(self.fixture_dir, verbose=False, assemblies=assemblies_reversed)
        
        # Both should find the same packages, just potentially in different order
        pkgs1_names = {pkg.name for pkg in repo_index1.packages}
        pkgs2_names = {pkg.name for pkg in repo_index2.packages}
        self.assertEqual(pkgs1_names, pkgs2_names)
        self.assertEqual(pkgs1_names, {'PkgX', 'PkgY', 'PkgX2'})
    
    def test_dependency_resolution(self):
        """Test dependency resolution with first-match-wins."""
        assemblies = [
            os.path.join(self.fixture_dir, 'assemblyA'),
            os.path.join(self.fixture_dir, 'assemblyB')
        ]
        repo_index = scan_upp_repo(self.fixture_dir, verbose=False, assemblies=assemblies)
        
        # Resolve dependencies for PkgY which depends on PkgX
        resolved_deps = resolve_upp_dependencies(repo_index, 'PkgY', verbose=False)
        
        # Should find Core, Draw, and PkgX dependencies
        self.assertIn('Core', resolved_deps)
        self.assertIn('Draw', resolved_deps)
        self.assertIn('PkgX', resolved_deps)
        
        # PkgX should be resolved to the one in assemblyA (first in search order)
        if resolved_deps['PkgX'] is not None:
            self.assertTrue(resolved_deps['PkgX'].dir_path.startswith(assemblies[0]))
    
    def test_dependency_resolution_first_match_wins(self):
        """Test that first-match-wins works correctly."""
        assemblies = [
            os.path.join(self.fixture_dir, 'assemblyA'),  # PkgX here
            os.path.join(self.fixture_dir, 'assemblyB')   # PkgX2 here (not PkgX)
        ]
        repo_index = scan_upp_repo(self.fixture_dir, verbose=False, assemblies=assemblies)
        
        # Resolve dependencies for PkgY which depends on PkgX
        resolved_deps = resolve_upp_dependencies(repo_index, 'PkgY', verbose=False)
        
        # PkgX should be resolved from assemblyA (first match in order)
        if resolved_deps['PkgX'] is not None:
            self.assertTrue(resolved_deps['PkgX'].dir_path.startswith(assemblies[0]))
    
    def test_package_exists_iff_upp_file_exists(self):
        """Test that a package exists only if <Name>/<Name>.upp exists."""
        # Create a directory without .upp file
        no_upp_dir = os.path.join(self.fixture_dir, 'assemblyA', 'Folder1', 'NoPkg')
        os.makedirs(no_upp_dir, exist_ok=True)
        
        try:
            repo_index = scan_upp_repo(os.path.join(self.fixture_dir, 'assemblyA'), verbose=False)
            
            # Should not find NoPkg since it has no .upp file
            package_names = {pkg.name for pkg in repo_index.packages}
            self.assertNotIn('NoPkg', package_names)
        finally:
            # Clean up
            if os.path.exists(no_upp_dir):
                os.rmdir(no_upp_dir)
    
    def test_verbose_trace_output(self):
        """Test that verbose mode produces trace output."""
        import io
        import contextlib
        
        assemblies = [
            os.path.join(self.fixture_dir, 'assemblyA'),
            os.path.join(self.fixture_dir, 'assemblyB')
        ]
        
        # Capture the verbose output
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            repo_index = scan_upp_repo(self.fixture_dir, verbose=True, assemblies=assemblies)
            if repo_index.packages:
                resolve_upp_dependencies(repo_index, repo_index.packages[0].name, verbose=True)
        
        output = f.getvalue()
        
        # Check that important trace messages are present
        self.assertIn('[maestro] assemblies', output)
        self.assertIn('scanning assembly:', output)
        self.assertIn('package folders:', output)
        self.assertIn('FOUND (package:', output)
        self.assertIn('resolve dependency:', output)


class TestUppDiscoveryConformance(unittest.TestCase):
    """Conformance tests against expected behavior."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.fixture_dir = os.path.join(os.path.dirname(__file__), 'fixtures', 'upp_workspace')
    
    def test_expected_discovery_behavior(self):
        """Test that discovery matches expected conformance behavior."""
        assemblies = [
            os.path.join(self.fixture_dir, 'assemblyA'),
            os.path.join(self.fixture_dir, 'assemblyB')
        ]
        repo_index = scan_upp_repo(self.fixture_dir, verbose=False, assemblies=assemblies)
        
        # Expected: 2 assemblies found
        self.assertEqual(len(repo_index.assemblies), 2)
        
        # Expected: 3 packages found (PkgX, PkgY, PkgX2)
        self.assertEqual(len(repo_index.packages), 3)
        
        # Expected: each package has correct directory structure
        for pkg in repo_index.packages:
            self.assertTrue(os.path.exists(pkg.dir_path))
            self.assertTrue(os.path.exists(pkg.upp_path))
            self.assertTrue(pkg.name in pkg.dir_path)
    
    def test_expected_dependency_resolution(self):
        """Test that dependency resolution matches expected behavior."""
        assemblies = [
            os.path.join(self.fixture_dir, 'assemblyA'),
            os.path.join(self.fixture_dir, 'assemblyB')
        ]
        repo_index = scan_upp_repo(self.fixture_dir, verbose=False, assemblies=assemblies)
        
        # Find PkgY which has dependencies
        pkg_y = next((pkg for pkg in repo_index.packages if pkg.name == 'PkgY'), None)
        self.assertIsNotNone(pkg_y, "PkgY should exist")
        
        # Resolve its dependencies
        resolved_deps = resolve_upp_dependencies(repo_index, 'PkgY', verbose=False)
        
        # Should have Core and PkgX dependencies
        self.assertIn('Core', resolved_deps)  # Expected but might not exist in fixture
        self.assertIn('PkgX', resolved_deps)  # Should exist and be resolved


if __name__ == '__main__':
    unittest.main()