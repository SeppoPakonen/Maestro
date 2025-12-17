"""
Workspace module for U++ package dependency resolution.

Implements the workspace scanning and dependency resolution logic
similar to U++'s Workspace class.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Set
from .base import Package
from .upp import UppPackage, UppBuilder


class Workspace:
    """
    Workspace class that manages package scanning and dependency resolution.
    
    Similar to U++'s Workspace::Scan() logic, this resolves dependencies
    by analyzing 'uses' declarations in .upp files and building a complete
    dependency graph.
    """
    
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.packages: Dict[str, UppPackage] = {}
        self.resolved_order: List[str] = []
    
    def scan(self, search_paths: List[str] = None) -> Dict[str, UppPackage]:
        """
        Scan for U++ packages in the workspace and resolve dependencies.
        
        This is similar to U++'s Workspace::Scan() method.
        """
        if search_paths is None:
            search_paths = [str(self.root_dir)]
        
        # First pass: find and parse all .upp files
        self._find_and_parse_packages(search_paths)
        
        # Second pass: resolve dependencies and determine build order
        self._resolve_dependencies()
        
        return self.packages
    
    def _find_and_parse_packages(self, search_paths: List[str]):
        """Find and parse all .upp files in the search paths."""
        for search_path in search_paths:
            path_obj = Path(search_path)
            
            # Look for .upp files in this path
            for upp_file in path_obj.rglob("*.upp"):
                try:
                    # Parse the .upp file to create a UppPackage
                    # Create minimal method and host for parsing
                    method_config = {
                        'compiler': {'cxx': 'g++'},
                        'flags': {'cflags': [], 'cxxflags': [], 'ldflags': []},
                        'config': {'build_type': 'debug'}
                    }
                    from .config import BuildMethod
                    method = BuildMethod(name="dummy", config_data=method_config)
                    from .host import LocalHost
                    host = LocalHost()
                    builder = UppBuilder(method, host)  # Dummy builder just for parsing
                    package = builder.parse_upp_file(str(upp_file))
                    
                    # Add to packages dict if not already present
                    if package.name not in self.packages:
                        self.packages[package.name] = package
                    else:
                        # Handle duplicate package names - keep the first one found
                        print(f"[WARNING] Duplicate package name found: {package.name} at {package.dir}, keeping first occurrence")
                        
                except Exception as e:
                    print(f"[ERROR] Failed to parse .upp file {upp_file}: {e}")
    
    def _resolve_dependencies(self):
        """Resolve package dependencies and determine build order."""
        # Build dependency graph
        # The graph represents: if Package1 uses Package2, then there is an edge from Package2 to Package1
        # This means Package2 must be built before Package1
        dependency_graph = {pkg_name: [] for pkg_name in self.packages}  # Initialize empty adjacency lists

        for pkg_name, pkg in self.packages.items():
            for dep_name in pkg.uses:
                if dep_name in self.packages:
                    # If pkg depends on dep_name, then dep_name -> pkg_name
                    dependency_graph[dep_name].append(pkg_name)
                else:
                    # Dependency not found in current workspace
                    # In a full implementation, this might search in MaestroHub or other locations
                    print(f"[WARNING] Dependency not found in workspace: {dep_name} for package {pkg_name}")
        
        # Perform topological sort to determine build order
        self.resolved_order = self._topological_sort(dependency_graph)
    
    def _topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """
        Perform topological sort to determine package build order.
        
        Detects circular dependencies.
        """
        # Build reverse dependency graph
        in_degree = {node: 0 for node in graph}
        
        for node in graph:
            for dep in graph[node]:
                if dep in in_degree:
                    in_degree[dep] += 1
        
        # Find nodes with no dependencies
        queue = [node for node in in_degree if in_degree[node] == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            # Reduce in-degree for dependents
            for dependent in graph.get(node, []):
                if dependent in in_degree:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
        
        # Check for circular dependencies
        if len(result) != len(in_degree):
            # Find nodes that weren't processed (circular deps)
            unprocessed = set(in_degree.keys()) - set(result)
            raise CircularDependencyError(f"Circular dependency detected among: {unprocessed}")
        
        return result
    
    def get_build_order(self) -> List[UppPackage]:
        """Get packages in the correct build order."""
        return [self.packages[name] for name in self.resolved_order if name in self.packages]
    
    def get_dependencies_for(self, package_name: str) -> List[UppPackage]:
        """Get all dependencies for a specific package."""
        if package_name not in self.packages:
            return []
        
        # Find all packages that this package depends on (directly or indirectly)
        deps = set()
        
        def collect_deps(pkg_name):
            pkg = self.packages.get(pkg_name)
            if not pkg:
                return
            for dep_name in pkg.uses:
                if dep_name in self.packages and dep_name not in deps:
                    deps.add(dep_name)
                    collect_deps(dep_name)
        
        collect_deps(package_name)
        return [self.packages[dep_name] for dep_name in deps]
    
    def find_package(self, name: str) -> Optional[UppPackage]:
        """Find a package by name."""
        return self.packages.get(name)


class CircularDependencyError(Exception):
    """Raised when circular dependencies are detected in the workspace."""
    pass


class PackageResolver:
    """
    Higher-level package resolver that integrates with maestro's repo system.
    
    Resolves packages from .maestro/repo/index.json and determines build order.
    """
    
    def __init__(self, repo_index_path: str = ".maestro/repo/index.json"):
        self.repo_index_path = repo_index_path
        self.workspace = None
    
    def resolve_from_repo(self) -> Workspace:
        """
        Resolve packages from the repository index and create a workspace.
        
        Reads .maestro/repo/index.json and creates a workspace with the packages.
        """
        import json
        
        workspace_root = os.getcwd()  # Default to current directory
        self.workspace = Workspace(workspace_root)
        
        # For now, we'll simulate reading from the repo index
        # In a real implementation, this would read from .maestro/repo/index.json
        try:
            if os.path.exists(self.repo_index_path):
                with open(self.repo_index_path, 'r') as f:
                    repo_data = json.load(f)
                
                # Extract package paths from repo index
                package_dirs = []
                for _, pkg_info in repo_data.get('packages', {}).items():
                    if pkg_info.get('build_system') == 'upp':
                        package_dirs.append(pkg_info.get('dir', ''))
                
                # Scan the identified U++ package directories
                if package_dirs:
                    self.workspace.scan(package_dirs)
            else:
                print(f"[INFO] Repository index not found at {self.repo_index_path}, scanning current directory")
                self.workspace.scan([workspace_root])
                
        except Exception as e:
            print(f"[ERROR] Failed to read repo index {self.repo_index_path}: {e}")
            # Fall back to scanning current directory
            self.workspace.scan([workspace_root])
        
        return self.workspace