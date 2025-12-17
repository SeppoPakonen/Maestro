"""
Hub client implementation for MaestroHub - Universal package hub system.
Handles loading hub metadata, searching for packages, installing nests,
and auto-resolving dependencies.
"""
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Union
from urllib.parse import urlparse
import urllib.request
from dataclasses import dataclass


@dataclass
class HubNest:
    """Represents a package nest in a hub."""
    name: str
    description: str
    repository: str
    branch: str = "main"
    packages: List[str] = None
    category: str = "libraries"
    status: str = "stable"
    website: str = ""
    readme: str = ""
    build_system: str = "upp"
    
    def __post_init__(self):
        if self.packages is None:
            self.packages = []


@dataclass
class HubRegistry:
    """Represents a hub registry containing multiple nests."""
    name: str
    description: str
    nests: List[HubNest] = None
    links: List[str] = None
    
    def __post_init__(self):
        if self.nests is None:
            self.nests = []
        if self.links is None:
            self.links = []


class MaestroHub:
    """Main hub client for managing package registries and dependencies."""
    
    def __init__(self, hub_dir: Optional[str] = None):
        """
        Initialize the MaestroHub client.
        
        Args:
            hub_dir: Directory to store hub repositories (~/.maestro/hub/ by default)
        """
        if hub_dir is None:
            home_dir = Path.home()
            self.hub_dir = home_dir / ".maestro" / "hub"
        else:
            self.hub_dir = Path(hub_dir)
            
        self.cache_file = self.hub_dir / ".hub-cache.json"
        self.config_file = self.hub_dir.parent / "config.toml"
        
        # Create hub directory if it doesn't exist
        self.hub_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize registries
        self.registries: Dict[str, HubRegistry] = {}
        
        # Load existing cache
        self._load_cache()
    
    def _load_cache(self):
        """Load hub metadata cache from file."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                    
                for reg_name, reg_data in cache_data.get('registries', {}).items():
                    nests = []
                    for nest_data in reg_data.get('nests', []):
                        nest = HubNest(
                            name=nest_data['name'],
                            description=nest_data['description'],
                            repository=nest_data['repository'],
                            branch=nest_data.get('branch', 'main'),
                            packages=nest_data.get('packages', []),
                            category=nest_data.get('category', 'libraries'),
                            status=nest_data.get('status', 'stable'),
                            website=nest_data.get('website', ''),
                            readme=nest_data.get('readme', ''),
                            build_system=nest_data.get('build_system', 'upp')
                        )
                        nests.append(nest)
                    
                    registry = HubRegistry(
                        name=reg_data['name'],
                        description=reg_data['description'],
                        nests=nests,
                        links=reg_data.get('links', [])
                    )
                    self.registries[reg_name] = registry
            except Exception:
                pass  # If cache is corrupted, start fresh
    
    def _save_cache(self):
        """Save hub metadata cache to file."""
        cache_data = {
            'registries': {},
            'timestamp': None  # Could add timestamp here
        }
        
        for reg_name, registry in self.registries.items():
            reg_dict = {
                'name': registry.name,
                'description': registry.description,
                'nests': [],
                'links': registry.links
            }
            
            for nest in registry.nests:
                nest_dict = {
                    'name': nest.name,
                    'description': nest.description,
                    'repository': nest.repository,
                    'branch': nest.branch,
                    'packages': nest.packages,
                    'category': nest.category,
                    'status': nest.status,
                    'website': nest.website,
                    'readme': nest.readme,
                    'build_system': nest.build_system
                }
                reg_dict['nests'].append(nest_dict)
            
            cache_data['registries'][reg_name] = reg_dict
        
        with open(self.cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
    
    def load_hub(self, url: str) -> Optional[HubRegistry]:
        """
        Load hub metadata from URL or local file.
        
        Args:
            url: URL to hub registry JSON file or local file path
            
        Returns:
            HubRegistry object or None if failed to load
        """
        try:
            parsed = urlparse(url)
            if parsed.scheme in ('http', 'https'):
                # Download from web using urllib
                response = urllib.request.urlopen(url)
                hub_data = json.loads(response.read().decode())
            elif parsed.scheme in ('file', '') or url.startswith('/'):
                # Load from local file
                with open(url, 'r') as f:
                    hub_data = json.load(f)
            else:
                raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")
            
            # Create registry from data
            registry = HubRegistry(
                name=hub_data.get('name', 'unnamed'),
                description=hub_data.get('description', 'No description'),
                links=hub_data.get('links', [])
            )
            
            # Process nests
            for nest_data in hub_data.get('nests', []):
                if 'name' in nest_data and 'repository' in nest_data:
                    nest = HubNest(
                        name=nest_data['name'],
                        description=nest_data.get('description', ''),
                        repository=nest_data['repository'],
                        branch=nest_data.get('branch', 'main'),
                        packages=nest_data.get('packages', []),
                        category=nest_data.get('category', 'libraries'),
                        status=nest_data.get('status', 'stable'),
                        website=nest_data.get('website', ''),
                        readme=nest_data.get('readme', ''),
                        build_system=nest_data.get('build_system', 'upp')
                    )
                    registry.nests.append(nest)
            
            # Store in registry dict
            self.registries[registry.name] = registry
            
            # Save to cache
            self._save_cache()
            
            return registry
            
        except Exception as e:
            print(f"Failed to load hub from {url}: {e}")
            return None
    
    def search_package(self, package_name: str) -> List[tuple[HubRegistry, HubNest]]:
        """
        Search for package across all registered hubs.
        
        Args:
            package_name: Name of package to search for
            
        Returns:
            List of tuples (registry, nest) where package was found
        """
        results = []
        
        for registry_name, registry in self.registries.items():
            for nest in registry.nests:
                # Check if package name is in the nest's packages list
                if package_name in nest.packages:
                    results.append((registry, nest))
                # Also check if package name matches nest name (some nests are single packages)
                elif nest.name.lower() == package_name.lower():
                    results.append((registry, nest))
        
        return results
    
    def install_nest(self, nest_name: str, update: bool = False) -> bool:
        """
        Clone/update repository nest.
        
        Args:
            nest_name: Name of the nest to install
            update: Whether to update if already installed
            
        Returns:
            True if successful, False otherwise
        """
        # Find the nest across all registries
        found_nest = None
        found_registry = None
        
        for registry in self.registries.values():
            for nest in registry.nests:
                if nest.name.lower() == nest_name.lower():
                    found_nest = nest
                    found_registry = registry
                    break
            if found_nest:
                break
        
        if not found_nest:
            print(f"Nest '{nest_name}' not found in any registered hub.")
            return False
        
        nest_dir = self.hub_dir / nest_name
        
        if nest_dir.exists() and not update:
            print(f"Nest '{nest_name}' already exists at {nest_dir}. Use --update to refresh.")
            return True
        
        if nest_dir.exists() and update:
            # Pull latest changes if possible
            try:
                subprocess.run(['git', 'pull'], check=True, cwd=nest_dir, capture_output=True)
                print(f"Updated nest '{nest_name}' from {found_nest.repository}")
                return True
            except subprocess.CalledProcessError:
                print(f"Failed to update nest '{nest_name}', attempting fresh clone...")
                shutil.rmtree(nest_dir)
        
        # Clone the repository
        try:
            subprocess.run([
                'git', 'clone', 
                '--depth', '1',  # Shallow clone to save space
                '-b', found_nest.branch, 
                found_nest.repository, 
                str(nest_dir)
            ], check=True, capture_output=True)
            
            print(f"Successfully installed nest '{nest_name}' from {found_nest.repository}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Failed to clone repository for nest '{nest_name}': {e}")
            return False
        except Exception as e:
            print(f"Error installing nest '{nest_name}': {e}")
            return False
    
    def auto_resolve(self, workspace_packages: List[str]) -> Dict[str, str]:
        """
        Automatically resolve missing dependencies.
        
        Args:
            workspace_packages: List of package names currently in workspace
            
        Returns:
            Dictionary mapping missing package names to their nest locations
        """
        missing_packages = {}
        
        # For each package in workspace, check if it's available
        for pkg in workspace_packages:
            found = False
            
            # Check if package exists in local workspace
            if self._package_exists_locally(pkg):
                continue
                
            # Search in hubs
            results = self.search_package(pkg)
            if results:
                # Take first match
                registry, nest = results[0]
                missing_packages[pkg] = nest.name
                print(f"Found missing package '{pkg}' in nest '{nest.name}'")
            else:
                print(f"Could not find package '{pkg}' in any registered hub")
        
        return missing_packages
    
    def _package_exists_locally(self, package_name: str) -> bool:
        """
        Check if a package exists in the local workspace or hub installations.
        
        Args:
            package_name: Name of package to check
            
        Returns:
            True if package exists locally, False otherwise
        """
        # Check in hub-installed packages
        for nest_dir in self.hub_dir.iterdir():
            if nest_dir.is_dir():
                # Look for the package in this nest directory
                # For U++ packages, we'd look for .upp files named after the package
                upp_file = nest_dir / f"{package_name}.upp"
                if upp_file.exists():
                    return True
                    
                # For other build systems, we'd need to check differently
                # This is a simplified check for now
                if (nest_dir / package_name).exists():
                    return True
                    
        return False
    
    def list_registries(self) -> Dict[str, HubRegistry]:
        """Return all loaded registries."""
        return self.registries.copy()
    
    def get_all_packages(self) -> List[Dict[str, str]]:
        """Get list of all packages available in all registries."""
        packages = []
        
        for registry_name, registry in self.registries.items():
            for nest in registry.nests:
                for pkg in nest.packages:
                    packages.append({
                        'package': pkg,
                        'nest': nest.name,
                        'registry': registry_name,
                        'description': nest.description,
                        'build_system': nest.build_system
                    })
        
        return packages


# Example usage:
if __name__ == "__main__":
    hub = MaestroHub()
    
    # Load a sample hub registry (if available)
    # hub.load_hub("https://example.com/maestro-hub.json")
    
    print("MaestroHub client initialized successfully!")