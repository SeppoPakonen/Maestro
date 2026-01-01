from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path
import os


@dataclass
class AssemblyInfo:
    """Information about a detected assembly."""
    name: str                          # Assembly name (typically directory name)
    dir: str                           # Absolute path to assembly directory
    assembly_type: str                 # 'upp', 'python', 'java', 'gradle', 'maven', 'misc', 'multi'
    packages: List[str]                # List of package names contained in this assembly
    package_dirs: List[str]            # List of package directory paths
    build_systems: List[str]           # List of build systems used (for multi-type assemblies)
    metadata: Dict[str, Any] = field(default_factory=dict)
    package_ids: List[str] = field(default_factory=list)  # List of package IDs contained in this assembly

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'dir': self.dir,
            'assembly_type': self.assembly_type,
            'packages': self.packages,
            'package_dirs': self.package_dirs,
            'build_systems': self.build_systems,
            'metadata': self.metadata,
            'package_ids': self.package_ids
        }


def detect_assemblies(repo_root: str, packages: List, verbose: bool = False) -> List[AssemblyInfo]:
    """
    Detect assemblies in the repository by analyzing package organization.

    Args:
        repo_root: Root directory of the repository
        packages: List of detected packages (from existing scanners)
        verbose: Enable verbose output

    Returns:
        List of AssemblyInfo objects
    """
    # Import here to avoid circular dependency
    from .package import PackageInfo as RepoPackageInfo
    # Convert packages to the correct type if needed
    typed_packages = packages  # packages should already be of the right type
    
    # Group packages by parent directory
    dir_to_packages = {}
    for pkg in packages:
        parent_dir = os.path.dirname(pkg.dir)  # Parent directory of the package
        if parent_dir not in dir_to_packages:
            dir_to_packages[parent_dir] = []
        dir_to_packages[parent_dir].append(pkg)
    
    assemblies = []
    
    for dir_path, pkgs_in_dir in dir_to_packages.items():
        # An assembly is typically a directory that contains 2+ packages OR has a specific structure
        if len(pkgs_in_dir) >= 2:
            # Check if directory qualifies as an assembly based on package count
            asm_info = classify_assembly_type_with_detection(dir_path, pkgs_in_dir)
            if asm_info:
                assemblies.append(asm_info)
        else:
            # Even single packages may form assemblies if they have specific patterns
            asm_info = classify_assembly_type_with_detection(dir_path, pkgs_in_dir)
            if asm_info:
                assemblies.append(asm_info)
    
    return assemblies


def classify_assembly_type_with_detection(dir_path: str, packages_in_dir: List) -> Optional[AssemblyInfo]:
    """Classify assembly type and create AssemblyInfo object."""
    assembly_type = classify_assembly_type(dir_path, packages_in_dir)
    
    if assembly_type:
        # Collect package names and directories
        package_names = [pkg.name for pkg in packages_in_dir]
        package_dirs = [pkg.dir for pkg in packages_in_dir]
        
        # Determine build systems used
        build_systems = list(set([pkg.build_system for pkg in packages_in_dir]))
        
        # Create AssemblyInfo
        assembly_name = os.path.basename(dir_path.rstrip('/'))
        return AssemblyInfo(
            name=assembly_name,
            dir=dir_path,
            assembly_type=assembly_type,
            packages=package_names,
            package_dirs=package_dirs,
            build_systems=build_systems
        )
    
    return None


def classify_assembly_type(dir_path: str, packages_in_dir: List) -> Optional[str]:
    """
    Classify the assembly type based on package analysis.

    Returns:
        'upp', 'python', 'java', 'gradle', 'maven', 'misc', or 'multi'
    """
    # Check for multi-type assembly first
    unique_build_systems = list(set([pkg.build_system for pkg in packages_in_dir]))
    if len(unique_build_systems) > 1:
        return 'multi'
    
    # Determine based on build system or directory structure
    if len(packages_in_dir) > 0:
        build_system = packages_in_dir[0].build_system
        
        # Map build system names to assembly types
        build_system_to_type = {
            'upp': 'upp',
            'cmake': 'cmake',
            'maven': 'maven',
            'gradle': 'gradle',
            'autoconf': 'autoconf',
            'visual_studio': 'visual_studio'
        }
        
        if build_system in build_system_to_type:
            return build_system_to_type[build_system]
        else:
            return 'misc'
    
    # If no packages match known build systems, try structural detection
    return detect_by_structure_only(dir_path)


def detect_by_structure_only(dir_path: str) -> Optional[str]:
    """Detect assembly type based on directory structure without packages."""
    # Look for Python assembly indicators
    python_assembly = detect_python_assembly(dir_path)
    if python_assembly:
        return 'python'
    
    # Look for general indicators of Java assemblies
    java_indicators = ['.gradle', 'gradlew', 'settings.gradle', 'pom.xml', 'build.gradle']
    for indicator in java_indicators:
        if os.path.exists(os.path.join(dir_path, indicator)):
            return 'java'  # Could be gradle or maven, we'll classify more specifically later
    
    # If nothing specific found, return misc
    return 'misc'


def detect_upp_assembly(dir_path: str, packages_in_dir: List) -> Optional[AssemblyInfo]:
    """Detect if a directory is a U++ assembly."""
    # Check for multiple .upp package directories
    upp_packages = [pkg for pkg in packages_in_dir if pkg.build_system == 'upp']
    if len(upp_packages) >= 2:
        # Common U++ assembly names: uppsrc, src, packages
        assembly_name = os.path.basename(dir_path.rstrip('/'))
        if any(name in dir_path.lower() for name in ['uppsrc', 'upp', 'src']):
            return AssemblyInfo(
                name=assembly_name,
                dir=dir_path,
                assembly_type='upp',
                packages=[pkg.name for pkg in upp_packages],
                package_dirs=[pkg.dir for pkg in upp_packages],
                build_systems=['upp']
            )
    return None


def detect_python_assembly(dir_path: str) -> Optional[AssemblyInfo]:
    """Detect if a directory is a Python assembly."""
    # Look for subdirectories with setup.py files
    try:
        subdirs = [entry for entry in os.listdir(dir_path) 
                   if os.path.isdir(os.path.join(dir_path, entry))]
        
        setup_py_dirs = []
        for subdir in subdirs:
            subdir_path = os.path.join(dir_path, subdir)
            if os.path.exists(os.path.join(subdir_path, 'setup.py')):
                setup_py_dirs.append(subdir_path)
        
        if len(setup_py_dirs) >= 2:
            # Found multiple subdirectories with setup.py - this is a Python assembly
            assembly_name = os.path.basename(dir_path.rstrip('/'))
            package_names = [os.path.basename(d.rstrip('/')) for d in setup_py_dirs]
            
            return AssemblyInfo(
                name=assembly_name,
                dir=dir_path,
                assembly_type='python',
                packages=package_names,
                package_dirs=setup_py_dirs,
                build_systems=['python']
            )
    except OSError:
        pass
    
    return None


def detect_java_assembly(dir_path: str, packages_in_dir: List) -> Optional[AssemblyInfo]:
    """Detect if a directory is a Java/Maven/Gradle assembly."""
    # Check for Maven/Gradle project structure
    java_packages = [pkg for pkg in packages_in_dir 
                     if pkg.build_system in ['maven', 'gradle']]
    
    if len(java_packages) >= 1:  # Even one could indicate an assembly if structure is right
        # Common gradle/maven indicators in the directory
        if (os.path.exists(os.path.join(dir_path, 'build.gradle')) or 
            os.path.exists(os.path.join(dir_path, 'pom.xml')) or 
            os.path.exists(os.path.join(dir_path, 'settings.gradle'))):
            
            assembly_name = os.path.basename(dir_path.rstrip('/'))
            return AssemblyInfo(
                name=assembly_name,
                dir=dir_path,
                assembly_type='java',
                packages=[pkg.name for pkg in java_packages],
                package_dirs=[pkg.dir for pkg in java_packages],
                build_systems=list(set([pkg.build_system for pkg in java_packages]))
            )
    
    return None


def detect_multi_type_assembly(dir_path: str, packages_in_dir: List) -> Optional[AssemblyInfo]:
    """Detect if a directory contains multiple types of packages."""
    # If there are multiple build systems in the same directory, it's a multi-type assembly
    build_systems = set([pkg.build_system for pkg in packages_in_dir])
    if len(build_systems) > 1:
        assembly_name = os.path.basename(dir_path.rstrip('/'))
        return AssemblyInfo(
            name=assembly_name,
            dir=dir_path,
            assembly_type='multi',
            packages=[pkg.name for pkg in packages_in_dir],
            package_dirs=[pkg.dir for pkg in packages_in_dir],
            build_systems=list(build_systems)
        )
    
    return None