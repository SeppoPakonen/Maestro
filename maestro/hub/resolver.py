"""
Hub resolver implementation for MaestroHub - Handles dependency resolution
and integration with the build system.
"""
import os
from pathlib import Path
from typing import Dict, List, Optional, Set
from .client import MaestroHub, HubNest, HubRegistry


class HubResolver:
    """Handles dependency resolution using the MaestroHub system."""
    
    def __init__(self, hub: MaestroHub):
        """
        Initialize the HubResolver.
        
        Args:
            hub: Initialized MaestroHub instance
        """
        self.hub = hub
    
    def resolve_workspace_dependencies(self, workspace_dir: str, 
                                     package_dependencies: List[str],
                                     auto_install: bool = True) -> Dict[str, str]:
        """
        Resolve dependencies for a workspace.
        
        Args:
            workspace_dir: Path to the workspace directory
            package_dependencies: List of package names that are needed
            auto_install: Whether to automatically install missing packages
            
        Returns:
            Dictionary mapping package names to their installation locations
        """
        resolved = {}
        missing = []
        
        for pkg in package_dependencies:
            # Check if package exists in workspace
            if self._package_exists_in_workspace(workspace_dir, pkg):
                resolved[pkg] = "workspace"
                continue
                
            # Check if package exists in hub installations
            if self._package_exists_in_hub(pkg):
                resolved[pkg] = "hub"
                continue
                
            # Package is missing
            missing.append(pkg)
        
        # Attempt to resolve missing packages
        if missing:
            print(f"Missing packages: {missing}")
            
            for pkg in missing:
                results = self.hub.search_package(pkg)
                
                if results:
                    registry, nest = results[0]  # Take first match
                    
                    if auto_install:
                        success = self.hub.install_nest(nest.name)
                        if success:
                            resolved[pkg] = f"hub/{nest.name}"
                            print(f"Successfully installed {pkg} from {nest.name}")
                        else:
                            print(f"Failed to install {pkg} from {nest.name}")
                    else:
                        print(f"Package {pkg} available in nest '{nest.name}'")
                        resolved[pkg] = f"available/{nest.name}"
                else:
                    print(f"Package {pkg} not found in any hub")
                    resolved[pkg] = "not_found"
        
        return resolved
    
    def _package_exists_in_workspace(self, workspace_dir: str, package_name: str) -> bool:
        """
        Check if package exists in the workspace directory.
        
        Args:
            workspace_dir: Path to workspace directory
            package_name: Name of package to look for
            
        Returns:
            True if package exists in workspace, False otherwise
        """
        workspace_path = Path(workspace_dir)
        
        # Look for package in common U++ locations
        upp_package = workspace_path / f"{package_name}.upp"
        if upp_package.exists():
            return True
            
        # Look in potential package subdirectories
        for dir_path in workspace_path.iterdir():
            if dir_path.is_dir():
                upp_file = dir_path / f"{package_name}.upp"
                if upp_file.exists():
                    return True
                    
                # Also check if directory name matches package name
                if dir_path.name.lower() == package_name.lower():
                    # Check if it contains package files
                    if any(f.suffix in ['.upp', '.h', '.cpp', '.cc', '.c'] 
                          for f in dir_path.iterdir() if f.is_file()):
                        return True
        
        return False
    
    def _package_exists_in_hub(self, package_name: str) -> bool:
        """
        Check if package exists in hub installations.
        
        Args:
            package_name: Name of package to look for
            
        Returns:
            True if package exists in hub installations, False otherwise
        """
        # Use the hub's local existence check
        return self.hub._package_exists_locally(package_name)
    
    def get_dependency_chain(self, package_name: str, 
                           visited: Optional[Set[str]] = None) -> List[str]:
        """
        Get the full dependency chain for a package (recursive resolution).
        
        Args:
            package_name: Name of the package to resolve dependencies for
            visited: Set of already visited packages to prevent cycles
            
        Returns:
            List of all dependencies in order they should be built
        """
        if visited is None:
            visited = set()
            
        if package_name in visited:
            return []  # Prevent cycles
            
        visited.add(package_name)
        dependencies = []
        
        # Check if package exists locally or in hub
        if (not self._package_exists_in_workspace(".", package_name) and
            not self._package_exists_in_hub(package_name)):
            # Try to find in hubs
            results = self.hub.search_package(package_name)
            if not results:
                print(f"Could not find package {package_name} anywhere")
                return []
            
            # Install it if not available
            registry, nest = results[0]
            self.hub.install_nest(nest.name)
        
        # For now, we'll assume dependencies are defined in package metadata
        # In a real implementation, we'd parse .upp files to extract 'uses' clauses
        # or read build system files to understand dependencies
        direct_deps = self._get_direct_dependencies(package_name)
        
        # Process direct dependencies first
        for dep in direct_deps:
            if dep not in dependencies:
                dep_chain = self.get_dependency_chain(dep, visited.copy())
                dependencies.extend(dep_chain)
                
        # Add the current package at the end
        if package_name not in dependencies:
            dependencies.append(package_name)
        
        return dependencies
    
    def _get_direct_dependencies(self, package_name: str) -> List[str]:
        """
        Get direct dependencies for a package (placeholder implementation).
        
        Args:
            package_name: Name of package to get dependencies for
            
        Returns:
            List of direct dependency names
        """
        # This is a placeholder - in reality, this would parse:
        # - .upp files for 'uses' clauses
        # - CMakeLists.txt for find_package/find_library calls
        # - configure.ac for dependency checks
        # - .vcxproj files for project references
        # - pom.xml for Maven dependencies
        # etc.
        
        # For now, return an empty list - this would be implemented
        # based on the build system of the package
        return []
    
    def resolve_build_order(self, package_names: List[str]) -> List[str]:
        """
        Determine the correct build order for a list of packages based on dependencies.
        
        Args:
            package_names: List of package names to build
            
        Returns:
            List of package names in correct build order
        """
        all_deps = set()
        
        # Get full dependency chain for all packages
        for pkg in package_names:
            chain = self.get_dependency_chain(pkg)
            all_deps.update(chain)
        
        # Return packages in build order (dependencies first)
        # This is a simplified implementation - a full implementation would
        # build a proper dependency graph and perform topological sort
        ordered = []
        processed = set()
        
        for pkg in package_names:
            chain = self.get_dependency_chain(pkg)
            for dep in chain:
                if dep not in processed:
                    ordered.append(dep)
                    processed.add(dep)
        
        # Remove duplicates while preserving order
        result = []
        seen = set()
        for pkg in ordered:
            if pkg not in seen and pkg in all_deps:
                result.append(pkg)
                seen.add(pkg)
        
        return result
    
    def create_build_path(self, package_name: str) -> Optional[str]:
        """
        Create the proper build path for a package, considering search order:
        local project -> hub installations -> system paths
        
        Args:
            package_name: Name of package to find/build path for
            
        Returns:
            Path to the package if found, None otherwise
        """
        # Check workspace first
        if self._package_exists_in_workspace(".", package_name):
            # Return path relative to workspace
            # For now, we return a placeholder - actual implementation would
            # locate the exact directory
            return f"./{package_name}"
        
        # Check hub installations
        hub_path = self._find_package_in_hub(package_name)
        if hub_path:
            return hub_path
        
        # Not found anywhere
        return None
    
    def _find_package_in_hub(self, package_name: str) -> Optional[str]:
        """
        Find package in hub installations.
        
        Args:
            package_name: Name of package to find
            
        Returns:
            Path to package if found in hub, None otherwise
        """
        hub_dir = self.hub.hub_dir
        
        # Look for package in each hub nest directory
        for nest_dir in hub_dir.iterdir():
            if nest_dir.is_dir():
                # Check if package file exists directly
                upp_file = nest_dir / f"{package_name}.upp"
                if upp_file.exists():
                    return str(nest_dir / package_name)
                
                # Check if subdirectory with package name exists
                pkg_dir = nest_dir / package_name
                if pkg_dir.exists():
                    # Verify it contains package files
                    if any(f.suffix in ['.upp', '.h', '.cpp', '.cc', '.c'] 
                          for f in pkg_dir.iterdir() if f.is_file()):
                        return str(pkg_dir)
        
        return None


# Example usage
if __name__ == "__main__":
    hub = MaestroHub()
    resolver = HubResolver(hub)
    
    print("HubResolver initialized successfully!")