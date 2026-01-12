"""
Builder selection logic module.

Implements builder selection logic with select_builder function
that chooses the appropriate builder based on package type and configuration.
"""

from typing import Dict, Any, Optional, Type
from .base import Builder, Package
from .gcc import GccBuilder
from .msvc import MsvcBuilder
from .cmake import CMakeBuilder
from .autotools import AutotoolsBuilder
from .msbuild import MsBuildBuilder
from .maven import MavenBuilder
from .gradle import GradleBuilder
from .android import AndroidBuilder
from .java import JavaBuilder
from .upp import UppBuilder
from .makefile import MakefileBuilder
from .config import MethodConfig


def select_builder(package_info: Dict[str, Any], config: MethodConfig = None) -> Optional[Builder]:
    """
    Select appropriate builder for a package based on its metadata.
    
    Args:
        package_info: Dictionary containing package information from repo scan
        config: Optional MethodConfig for the build
        
    Returns:
        Builder instance appropriate for the package, or None if no suitable builder found
    """
    build_system = package_info.get('build_system', 'upp')
    
    # Handle multi-build system packages
    if build_system == 'multi' and 'metadata' in package_info:
        metadata = package_info['metadata']
        build_system = metadata.get('primary_build_system', build_system)
    
    # Create a default config if none provided
    if config is None:
        from .config import MethodConfig, BuildType
        config = MethodConfig(name="default", builder="auto")
    
    # Import the Host class to create UppBuilder which requires it
    from .host import get_current_host
    
    # Select builder based on build system type
    if build_system == 'upp':
        # For U++ packages, we typically use UppBuilder which requires a host
        host = get_current_host()
        builder = UppBuilder(host, config)
    elif build_system == 'cmake':
        builder = CMakeBuilder(config)
    elif build_system == 'autoconf' or build_system == 'autotools':
        builder = AutotoolsBuilder(config)
    elif build_system == 'msvs' or build_system == 'msbuild':
        builder = MsBuildBuilder(config)
    elif build_system == 'maven':
        builder = MavenBuilder(config)
    elif build_system == 'gradle':
        builder = GradleBuilder(config)
    elif build_system == 'android':
        builder = AndroidBuilder(config)
    elif build_system == 'java':
        builder = JavaBuilder(config)
    elif build_system == 'gcc':
        builder = GccBuilder(config)
    elif build_system == 'msvc':
        builder = MsvcBuilder(config)
    elif build_system == 'make':
        builder = MakefileBuilder(config)
    else:
        # Default fallback to UppBuilder for unknown systems
        host = get_current_host()
        builder = UppBuilder(host, config)
    
    return builder


def get_builder_by_name(builder_name: str, config: MethodConfig = None) -> Optional[Builder]:
    """
    Get a builder instance by its name string.
    
    Args:
        builder_name: Name of the builder (e.g., 'gcc', 'cmake', 'gradle')
        config: Optional MethodConfig for the build
        
    Returns:
        Builder instance or None if builder name is not recognized
    """
    if config is None:
        from .config import MethodConfig
        config = MethodConfig(name="default", builder=builder_name)
    
    from .host import get_current_host
    
    builder_map = {
        'upp': lambda c: UppBuilder(get_current_host(), c),
        'gcc': GccBuilder,
        'msvc': MsvcBuilder,
        'cmake': CMakeBuilder,
        'autotools': AutotoolsBuilder,
        'msbuild': MsBuildBuilder,
        'maven': MavenBuilder,
        'gradle': GradleBuilder,
        'android': AndroidBuilder,
        'java': JavaBuilder,
        'make': MakefileBuilder
    }
    
    builder_constructor = builder_map.get(builder_name.lower())
    if builder_constructor:
        return builder_constructor(config)
    
    return None


def get_available_builders() -> Dict[str, Type[Builder]]:
    """
    Get a dictionary of all available builder types.
    
    Returns:
        Dictionary mapping builder names to their classes
    """
    from .host import get_current_host
    
    # Note: We can't include UppBuilder in this mapping directly because it requires a host object
    # So we include a special factory for it
    def create_upp_builder(config):
        return UppBuilder(get_current_host(), config)
    
    return {
        'gcc': GccBuilder,
        'msvc': MsvcBuilder,
        'cmake': CMakeBuilder,
        'autotools': AutotoolsBuilder,
        'msbuild': MsBuildBuilder,
        'maven': MavenBuilder,
        'gradle': GradleBuilder,
        'android': AndroidBuilder,
        'java': JavaBuilder,
        'make': MakefileBuilder,
        'upp_factory': create_upp_builder  # Special factory for UppBuilder
    }


def validate_builder_compatibility(builder: Builder, package_info: Dict[str, Any]) -> bool:
    """
    Validate if a builder is compatible with a package.
    
    Args:
        builder: Builder instance to validate
        package_info: Dictionary containing package information
        
    Returns:
        True if builder is compatible with package, False otherwise
    """
    build_system = package_info.get('build_system', 'upp')
    builder_name = type(builder).__name__.lower().replace('builder', '')
    
    # Define compatibility rules
    compatibility_rules = {
        'upp': ['upp', 'gcc', 'msvc'],
        'cmake': ['cmake'],
        'autotools': ['autotools'],
        'msvs': ['msbuild'],
        'make': ['make'],
        'gradle': ['gradle'],
        'maven': ['maven'],
        'android': ['android'],
        'java': ['java', 'gradle', 'maven']
    }
    
    compatible_builders = compatibility_rules.get(build_system, [build_system])
    return builder_name in compatible_builders


def get_builder_priority_list() -> list:
    """
    Get the priority list for builder selection.
    
    Returns:
        List of builder names in priority order for selection
    """
    return [
        'upp',       # U++ packages first
        'cmake',     # CMake projects
        'gradle',    # Gradle projects
        'maven',     # Maven projects
        'autotools', # Autotools projects
        'make',      # Makefile projects
        'msbuild',   # MSBuild projects
        'android',   # Android projects
        'java',      # Java projects
        'gcc',       # GCC builds
        'msvc'       # MSVC builds
    ]


# Main select_builder function as required in the spec
def select_builder_function(package_info: Dict[str, Any], config: MethodConfig = None, 
                           explicit_builder: str = None) -> Optional[Builder]:
    """
    Main builder selection function following the priority:
    1. Explicit builder (if provided)
    2. Package type auto-detection
    3. Error if no suitable builder found
    
    Args:
        package_info: Dictionary containing package information
        config: Optional MethodConfig for the build
        explicit_builder: Explicitly specified builder name
        
    Returns:
        Builder instance appropriate for the package
    """
    # 1. If explicit builder is provided, use it
    if explicit_builder:
        return get_builder_by_name(explicit_builder, config)
    
    # 2. Otherwise, auto-detect based on package info
    return select_builder(package_info, config)
