"""
Blitz build (unity build) support for Maestro.

Implements unity build functionality where multiple source files
are concatenated into a single translation unit to speed up compilation.
"""

import os
import hashlib
from pathlib import Path
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass
from ..repo.package import PackageInfo


@dataclass
class BlitzConfig:
    """Configuration for blitz build."""
    enabled: bool = True
    max_chunk_size: int = 50  # Max number of files per chunk
    include_guard_pattern: str = "#ifndef BLITZ_{hash}_H\n#define BLITZ_{hash}_H\n{content}\n#endif"
    exclude_patterns: List[str] = None  # Patterns for files to exclude from blitz
    force_exclude: List[str] = None     # Specific files to exclude from blitz

    def __post_init__(self):
        if self.exclude_patterns is None:
            self.exclude_patterns = [
                "*.c",  # C files might have conflicts with C++ headers
                "*_test.cpp",  # Test files often have conflicting definitions
                "*_unittest.cpp",
                "*mock*",      # Mock objects often have conflicting names
            ]
        if self.force_exclude is None:
            self.force_exclude = []


class BlitzDetector:
    """Detects files that are suitable for blitz builds."""
    
    # Files that are typically NOT safe for blitz builds
    BLITZ_UNSAFE_PATTERNS = [
        ".*\\.c$",  # C files may have C-specific constructs that conflict in unity builds
        ".*_test\\.cpp$",  # Test files often define global fixtures
        ".*_unittest\\.cpp$",
        ".*mock.*\\.(cpp|h)$",  # Mock files often have conflicting definitions
        ".*main\\.cpp$",  # Main files often have duplicate main() definitions
    ]
    
    # Static variable patterns that make files unsafe for blitz
    STATIC_VAR_PATTERNS = [
        r"\bstatic\s+.*\b[A-Za-z_][A-Za-z0-9_]*\s*=",
        r"\bstatic\s+.*\b[A-Za-z_][A-Za-z0-9_]*\s*\(",
        r"namespace\s+\w+\s*\{[^}]*static[^}]*\}",
    ]
    
    @staticmethod
    def is_blitz_safe(file_path: str) -> bool:
        """
        Determines if a file is safe for blitz builds.
        
        Args:
            file_path: Path to the source file
            
        Returns:
            True if the file is safe for blitz builds, False otherwise
        """
        import re
        
        # Check against patterns that make files unsafe
        for pattern in BlitzDetector.BLITZ_UNSAFE_PATTERNS:
            if re.search(pattern, file_path):
                return False
        
        # For C++ files, check for static variables that could cause conflicts
        if file_path.lower().endswith(('.cpp', '.cc', '.cxx')):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Look for problematic static variable declarations
                for var_pattern in BlitzDetector.STATIC_VAR_PATTERNS:
                    if re.search(var_pattern, content):
                        return False
            except Exception:
                # If we can't read the file, assume it's not safe
                return False
                
        return True
    
    @staticmethod
    def can_blitz_together(file1_path: str, file2_path: str) -> bool:
        """
        Determines if two files can be blitzed together.
        
        Args:
            file1_path: Path to first source file
            file2_path: Path to second source file
            
        Returns:
            True if the files can be blitzed together, False otherwise
        """
        # Don't blitz test files together with regular files
        f1_is_test = '_test' in file1_path or '_unittest' in file1_path
        f2_is_test = '_test' in file2_path or '_unittest' in file2_path
        
        if f1_is_test != f2_is_test:
            return False
            
        return True


class BlitzGenerator:
    """Generates blitz files from a list of source files."""
    
    def __init__(self, config: BlitzConfig = None):
        self.config = config or BlitzConfig()
        
    def generate_blitz_files(
        self, 
        package: PackageInfo, 
        source_files: List[str], 
        output_dir: str
    ) -> List[Tuple[str, List[str]]]:
        """
        Generates blitz files for the given source files.
        
        Args:
            package: Package information
            source_files: List of source file paths to blitz
            output_dir: Directory to write blitz files to
            
        Returns:
            List of tuples (blitz_file_path, source_files_in_blitz)
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Filter source files based on blitz safety and exclude patterns
        safe_sources = []
        for src in source_files:
            full_path = os.path.join(package.dir, src) if not os.path.isabs(src) else src
            
            # Check if file should be force-excluded
            should_exclude = any(os.path.basename(src).find(excl) >= 0 for excl in self.config.force_exclude)
            
            # Check if file matches exclude patterns
            if not should_exclude:
                for pattern in self.config.exclude_patterns:
                    import fnmatch
                    if fnmatch.fnmatch(os.path.basename(src), pattern):
                        should_exclude = True
                        break
            
            # Check if file is blaze safe
            if not should_exclude and BlitzDetector.is_blitz_safe(full_path):
                safe_sources.append(src)
        
        # Group files into chunks
        chunks = []
        current_chunk = []
        
        for src in safe_sources:
            if len(current_chunk) >= self.config.max_chunk_size:
                # Start a new chunk
                chunks.append(current_chunk)
                current_chunk = [src]
            else:
                # Check if this file can be added to current chunk
                can_add = True
                for existing_src in current_chunk:
                    if not BlitzDetector.can_blitz_together(src, existing_src):
                        can_add = False
                        break
                
                if can_add:
                    current_chunk.append(src)
                else:
                    # Start a new chunk with this file
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = [src]
        
        # Add the last chunk if it has files
        if current_chunk:
            chunks.append(current_chunk)
        
        # Generate blitz files
        blitz_files = []
        for idx, chunk in enumerate(chunks):
            if len(chunk) <= 1:
                # Don't blitz single files
                continue
                
            # Create blitz file name based on package and chunk index
            chunk_hash = hashlib.md5(f"{package.name}_{idx}".encode()).hexdigest()[:8]
            blitz_filename = f"blitz_{package.name}_{chunk_hash}.cpp"
            blitz_path = os.path.join(output_dir, blitz_filename)
            
            # Generate the blitz file content
            with open(blitz_path, 'w', encoding='utf-8') as blitz_file:
                # Add comment header
                blitz_file.write(f"// Unity build file generated from {len(chunk)} source files\n")
                blitz_file.write("// DO NOT EDIT - This file is automatically generated\n\n")
                
                # Include all the source files
                for src in chunk:
                    src_path = os.path.relpath(os.path.join(package.dir, src), output_dir)
                    blitz_file.write(f'#include "{src_path}"\n')
                
                blitz_file.write("\n")  # Add final newline
            
            blitz_files.append((blitz_path, chunk))
        
        return blitz_files


def is_blitz_file(filepath: str) -> bool:
    """
    Checks if a file is a blitz-generated file.
    
    Args:
        filepath: Path to the file to check
        
    Returns:
        True if the file is a blitz-generated file, False otherwise
    """
    filename = os.path.basename(filepath)
    return filename.startswith('blitz_') and ('.cpp' in filename or '.cc' in filename)


def should_blitz_file(filepath: str, config: BlitzConfig) -> bool:
    """
    Determines if a file should be included in blitz builds based on configuration.
    
    Args:
        filepath: Path to the file to check
        config: Blitz configuration
        
    Returns:
        True if the file should be included in blitz builds, False otherwise
    """
    filename = os.path.basename(filepath)
    
    # Check force exclude list
    if any(os.path.basename(filepath).find(excl) >= 0 for excl in config.force_exclude):
        return False
    
    # Check exclude patterns
    import fnmatch
    for pattern in config.exclude_patterns:
        if fnmatch.fnmatch(filename, pattern):
            return False
    
    # Check if file is blitz safe
    return BlitzDetector.is_blitz_safe(filepath)