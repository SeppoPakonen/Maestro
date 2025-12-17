"""
Global configuration for Maestro - handles settings for all components
including hub, build methods, and repository scanning.
"""
import os
import toml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class HubConfig:
    """Configuration for MaestroHub system."""
    enabled: bool = True
    auto_resolve: bool = True
    default_registries: List[str] = field(default_factory=list)
    cache_ttl: int = 86400  # 24 hours in seconds
    hub_directory: str = "~/.maestro/hub"
    auto_install_missing: bool = True
    confirm_install: bool = True

    def __post_init__(self):
        if not self.default_registries:
            self.default_registries = [
                "https://raw.githubusercontent.com/umk-project/maestrohub-main/main/nests.json",
                "https://raw.githubusercontent.com/umk-project/maestrohub-community/main/nests.json"
            ]


@dataclass
class BuildConfig:
    """Build system configuration."""
    default_method: str = "auto"
    parallel_builds: bool = True
    build_directory: str = ".maestro/build"
    cache_directory: str = ".maestro/cache"


@dataclass
class RepoConfig:
    """Repository scanning configuration."""
    scan_depth: int = 10
    ignore_patterns: List[str] = field(default_factory=lambda: [
        "node_modules", 
        ".git", 
        "__pycache__", 
        "*.pyc", 
        ".build", 
        "build", 
        "dist", 
        "target"
    ])
    include_build_systems: List[str] = field(default_factory=lambda: [
        "upp", "cmake", "autoconf", "msvs", "maven", "gradle", "make"
    ])


@dataclass
class GlobalConfig:
    """Global Maestro configuration."""
    verbose: bool = False
    parallel_jobs: int = 4
    hub: HubConfig = field(default_factory=HubConfig)
    build: BuildConfig = field(default_factory=BuildConfig)
    repo: RepoConfig = field(default_factory=RepoConfig)

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> 'GlobalConfig':
        """Load configuration from file."""
        if config_path is None:
            config_path = Path.home() / ".maestro" / "config.toml"
        
        if not config_path.exists():
            # Return default configuration if file doesn't exist
            return cls()
        
        try:
            with open(config_path, 'r') as f:
                data = toml.load(f)
            return cls.from_dict(data)
        except Exception as e:
            print(f"Warning: Could not load config from {config_path}: {e}")
            return cls()
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GlobalConfig':
        """Create GlobalConfig from dictionary data."""
        # Extract hub config
        hub_data = data.get('hub', {})
        hub_config = HubConfig(
            enabled=hub_data.get('enabled', True),
            auto_resolve=hub_data.get('auto_resolve', True),
            default_registries=hub_data.get('default_registries', [
                "https://raw.githubusercontent.com/umk-project/maestrohub-main/main/nests.json",
                "https://raw.githubusercontent.com/umk-project/maestrohub-community/main/nests.json"
            ]),
            cache_ttl=hub_data.get('cache_ttl', 86400),
            hub_directory=hub_data.get('hub_directory', "~/.maestro/hub"),
            auto_install_missing=hub_data.get('auto_install_missing', True),
            confirm_install=hub_data.get('confirm_install', True)
        )
        
        # Extract build config
        build_data = data.get('build', {})
        build_config = BuildConfig(
            default_method=build_data.get('default_method', "auto"),
            parallel_builds=build_data.get('parallel_builds', True),
            build_directory=build_data.get('build_directory', ".maestro/build"),
            cache_directory=build_data.get('cache_directory', ".maestro/cache")
        )
        
        # Extract repo config
        repo_data = data.get('repo', {})
        repo_config = RepoConfig(
            scan_depth=repo_data.get('scan_depth', 10),
            ignore_patterns=repo_data.get('ignore_patterns', [
                "node_modules", ".git", "__pycache__", "*.pyc", 
                ".build", "build", "dist", "target"
            ]),
            include_build_systems=repo_data.get('include_build_systems', [
                "upp", "cmake", "autoconf", "msvs", "maven", "gradle", "make"
            ])
        )
        
        # Create main config
        config = cls(
            verbose=data.get('maestro', {}).get('verbose', False),
            parallel_jobs=data.get('maestro', {}).get('parallel_jobs', 4),
            hub=hub_config,
            build=build_config,
            repo=repo_config
        )
        
        return config
    
    def save(self, config_path: Optional[Path] = None) -> bool:
        """Save configuration to file."""
        if config_path is None:
            config_path = Path.home() / ".maestro" / "config.toml"
        
        try:
            # Ensure directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert config to dictionary
            data = {
                'maestro': {
                    'verbose': self.verbose,
                    'parallel_jobs': self.parallel_jobs
                },
                'hub': {
                    'enabled': self.hub.enabled,
                    'auto_resolve': self.hub.auto_resolve,
                    'default_registries': self.hub.default_registries,
                    'cache_ttl': self.hub.cache_ttl,
                    'hub_directory': self.hub.hub_directory,
                    'auto_install_missing': self.hub.auto_install_missing,
                    'confirm_install': self.hub.confirm_install
                },
                'build': {
                    'default_method': self.build.default_method,
                    'parallel_builds': self.build.parallel_builds,
                    'build_directory': self.build.build_directory,
                    'cache_directory': self.build.cache_directory
                },
                'repo': {
                    'scan_depth': self.repo.scan_depth,
                    'ignore_patterns': self.repo.ignore_patterns,
                    'include_build_systems': self.repo.include_build_systems
                }
            }
            
            with open(config_path, 'w') as f:
                toml.dump(data, f)
            
            return True
        except Exception as e:
            print(f"Error saving config to {config_path}: {e}")
            return False


# Global configuration instance
_global_config = None


def get_config() -> GlobalConfig:
    """Get the global configuration instance."""
    global _global_config
    if _global_config is None:
        _global_config = GlobalConfig.load()
    return _global_config


def set_config(config: GlobalConfig) -> None:
    """Set the global configuration instance."""
    global _global_config
    _global_config = config


# Example usage
if __name__ == "__main__":
    # Load the global config
    config = get_config()
    
    # Print current hub configuration
    print(f"Hub enabled: {config.hub.enabled}")
    print(f"Auto resolve: {config.hub.auto_resolve}")
    print(f"Default registries: {config.hub.default_registries}")