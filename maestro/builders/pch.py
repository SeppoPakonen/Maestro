"""
Precompiled Header (PCH) support for Maestro.

Implements precompiled header functionality to speed up compilation
by pre-processing commonly used headers.
"""

import os
import hashlib
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from ..repo.package import PackageInfo


@dataclass
class PCHConfig:
    """Configuration for precompiled header generation."""
    enabled: bool = True
    auto_detect: bool = True  # Auto-detect headers to precompile
    max_headers: int = 10     # Maximum number of headers to include in PCH
    header_extensions: List[str] = None  # Extensions considered as headers
    force_include: List[str] = None      # Headers to always include in PCH
    force_exclude: List[str] = None      # Headers to exclude from PCH
    pch_filename: str = "stdafx.pch"     # Name of the generated PCH file
    include_guard_pattern: str = "#ifdef PRECOMPILED_HEADERS\n#include \"{pch_file}\"\n#endif"

    def __post_init__(self):
        if self.header_extensions is None:
            self.header_extensions = ['.h', '.hpp', '.hxx', '.hh']
        if self.force_include is None:
            self.force_include = []
        if self.force_exclude is None:
            self.force_exclude = [
                'winsock.h',  # Common problematic header
                'windows.h',  # Often causes issues when precompiled
                'gl.h',       # OpenGL headers can conflict
            ]


class PCHDetector:
    """Detects headers that are suitable for precompiled headers."""
    
    # Headers commonly used and beneficial for PCH
    COMMON_HEADERS = [
        "iostream",
        "string",
        "vector", 
        "memory",
        "algorithm",
        "functional",
        "map",
        "set",
        "unordered_map",
        "unordered_set",
        "utility",
        "tuple",
        "array",
        "deque",
        "list",
        "queue",
        "stack",
        "iomanip",
        "fstream",
        "sstream",
        "iostream",
        "cstdio",
        "cstdlib",
        "cstring",
        "cmath",
        "cassert",
        "ctime",
        "cctype",
        "locale",
        "iterator",
        "numeric",
        "random",
        "regex",
        "thread",
        "mutex",
        "future",
        "chrono",
        "exception",
        "stdexcept",
        "initializer_list",
        "type_traits",
        "ratio",
        "cfenv",
        "complex",
        "valarray",
        "atomic",
        "condition_variable",
        "shared_mutex",
        "scoped_allocator",
        "system_error",
        "typeindex",
        "typeinfo",
        "bitset",
        "forward_list",
        "unordered_map",
        "unordered_set",
        "forward_iterator",
        "input_iterator",
        "output_iterator",
        "random_access_iterator",
        "move_iterator",
        "reverse_iterator",
    ]
    
    @staticmethod
    def is_header_suitable_for_pch(header_path: str, package: PackageInfo = None) -> bool:
        """
        Determines if a header file is suitable for precompiled headers.
        
        Args:
            header_path: Path to the header file
            package: Package information (optional)
            
        Returns:
            True if the header is suitable for PCH, False otherwise
        """
        # Check if file extension indicates it's a header
        _, ext = os.path.splitext(header_path.lower())
        if ext not in ['.h', '.hpp', '.hxx', '.hh']:
            return False
            
        # Check if header is in force exclude list
        basename = os.path.basename(header_path)
        for exclude_header in PCHConfig().force_exclude:
            if exclude_header.lower() in basename.lower():
                return False
                
        # For U++ packages, consider common U++ headers
        if package and hasattr(package, 'build_system') and package.build_system == 'upp':
            upp_common_headers = [
                'Core', 'Draw', 'CtrlCore', 'CtrlLib', 'RichText', 'Rapid', 
                'Plugin', 'Sql', 'Web', 'UPPGUI', 'UPPXML', 'UPPBASE'
            ]
            for upp_header in upp_common_headers:
                if upp_header in basename:
                    return True
                    
        # Check if it's a common C++ header
        filename = os.path.basename(header_path)
        name_without_ext = os.path.splitext(filename)[0]
        if name_without_ext in PCHDetector.COMMON_HEADERS:
            return True
            
        # If it's a common header pattern, allow it
        common_patterns = [
            'std', 'boost', 'fmt', 'spdlog', 'gtest', 'gmock',
            'Core', 'Draw', 'CtrlCore', 'base', 'util', 'common'
        ]
        for pattern in common_patterns:
            if pattern.lower() in filename.lower():
                return True
                
        # If we can't determine, return False to be safe
        return False
    
    @staticmethod
    def detect_frequently_included_headers(
        package: PackageInfo, 
        source_files: List[str]
    ) -> List[str]:
        """
        Detect headers that are frequently included in source files.
        
        Args:
            package: Package information
            source_files: List of source files to analyze
            
        Returns:
            List of headers that appear frequently across source files
        """
        # Dictionary to count header occurrences
        header_count = {}
        
        for source_file in source_files:
            full_path = os.path.join(package.dir, source_file)
            if not os.path.exists(full_path):
                continue
                
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                # Simple heuristic to find #include statements
                import re
                include_pattern = r'#include\s+[<"]([^>"]+)[>"]'
                matches = re.findall(include_pattern, content)
                
                for header in matches:
                    # Normalize header path
                    normalized = os.path.normpath(header)
                    header_count[normalized] = header_count.get(normalized, 0) + 1
            except Exception:
                # Skip files that can't be read
                continue
                
        # Sort by frequency and return top candidates
        sorted_headers = sorted(
            header_count.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # Filter to only include headers that are suitable for PCH
        suitable_headers = []
        for header, count in sorted_headers:
            # Only include headers that are actually files or known common headers
            header_path = os.path.join(package.dir, header)
            if os.path.exists(header_path) and PCHDetector.is_header_suitable_for_pch(header_path, package):
                suitable_headers.append(header)
            elif any(common in header for common in PCHDetector.COMMON_HEADERS):
                suitable_headers.append(header)
                
            # Limit to max_headers
            if len(suitable_headers) >= PCHConfig().max_headers:
                break
                
        return suitable_headers[:PCHConfig().max_headers]


class PCHGenerator:
    """Generates precompiled header files."""
    
    def __init__(self, config: PCHConfig = None):
        self.config = config or PCHConfig()
        
    def generate_pch(
        self, 
        package: PackageInfo, 
        headers_to_precompile: List[str], 
        output_dir: str,
        compiler: str = 'g++'  # Compiler that will be used
    ) -> Optional[str]:
        """
        Generates a precompiled header file.
        
        Args:
            package: Package information
            headers_to_precompile: List of header files to include in PCH
            output_dir: Directory to write PCH file to
            compiler: Compiler that will be used (affects PCH extension/format)
            
        Returns:
            Path to the generated PCH file, or None if not generated
        """
        if not headers_to_precompile:
            return None
            
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Determine PCH filename based on compiler and package
        if compiler in ['g++', 'gcc']:
            pch_extension = '.gch'
        elif compiler in ['clang++', 'clang']:
            pch_extension = '.pch'
        elif compiler in ['cl', 'msvc', 'cl.exe']:
            pch_extension = '.pch'
        else:
            pch_extension = '.pch'
            
        # Create PCH filename with hash to make it unique
        headers_content = ''.join(headers_to_precompile)
        pch_hash = hashlib.md5(f"{package.name}_{headers_content}".encode()).hexdigest()[:8]
        
        if compiler in ['cl', 'msvc', 'cl.exe']:
            pch_filename = f"{package.name}_{pch_hash}.pch"
            # Also create the associated header file for MSVC
            header_filename = f"{package.name}_{pch_hash}.h"
            
            # Write the header file that will be precompiled
            header_path = os.path.join(output_dir, header_filename)
            with open(header_path, 'w', encoding='utf-8') as header_file:
                header_file.write(f"// Precompiled header for {package.name}\n")
                header_file.write("// Generated by Maestro PCH system\n\n")
                
                for header in headers_to_precompile:
                    if '<' in header and '>' in header:
                        header_file.write(f'#include <{header}>\n')
                    else:
                        header_file.write(f'#include "{header}"\n')
                header_file.write('\n')
                
            # Return the header file path (the .pch will be generated alongside it)
            return header_path
        else:
            pch_filename = f"{package.name}_{pch_hash}.h"
            pch_path = os.path.join(output_dir, pch_filename)
            
            # Write the header file that will be precompiled
            with open(pch_path, 'w', encoding='utf-8') as pch_file:
                pch_file.write(f"// Precompiled header for {package.name}\n")
                pch_file.write("// Generated by Maestro PCH system\n\n")
                
                for header in headers_to_precompile:
                    if '<' in header and '>' in header:
                        pch_file.write(f'#include <{header}>\n')
                    else:
                        pch_file.write(f'#include "{header}"\n')
                pch_file.write('\n')
                
            # Return the header file path (the .gch/.pch will be generated by the compiler)
            return pch_path
            
    def create_pch_includes(
        self, 
        pch_file_path: str, 
        source_file_path: str
    ) -> str:
        """
        Creates a modified source file that includes the PCH when appropriate.
        
        Args:
            pch_file_path: Path to the PCH file
            source_file_path: Path to the original source file
            
        Returns:
            Path to the modified source file with PCH inclusion
        """
        # Read the original source file
        with open(source_file_path, 'r', encoding='utf-8', errors='ignore') as src:
            original_content = src.read()
            
        # Check if the source file should skip PCH inclusion
        # This might be marked in comments or special pragmas
        if '// NOPCH' in original_content or '#pragma nopch' in original_content:
            return source_file_path  # Return original, no PCH for this file
            
        # Create the filename for the modified source file
        dir_path = os.path.dirname(source_file_path)
        filename = os.path.basename(source_file_path)
        name, ext = os.path.splitext(filename)
        modified_filename = f"{name}_with_pch{ext}"
        modified_path = os.path.join(dir_path, modified_filename)
        
        # Extract the PCH filename without path and extension for the include guard
        pch_basename = os.path.basename(pch_file_path)
        pch_name_no_ext = os.path.splitext(pch_basename)[0]
        
        # Write the modified source file with PCH inclusion
        with open(modified_path, 'w', encoding='utf-8') as modified:
            # Add the PCH include at the top, before other includes
            modified.write(f"#ifdef PRECOMPILED_HEADERS\n")
            modified.write(f'#include "{pch_basename}"\n')
            modified.write("#else\n")
            
            # Copy the original content
            modified.write(original_content)
            
            # Close the conditional
            modified.write("#endif\n")
            
        return modified_path


def needs_pch_regeneration(
    pch_file_path: str, 
    headers_to_precompile: List[str], 
    threshold_hours: float = 24.0
) -> bool:
    """
    Determines if a PCH file needs to be regenerated.
    
    Args:
        pch_file_path: Path to the PCH file
        headers_to_precompile: List of headers included in the PCH
        threshold_hours: Hours after which PCH should be regenerated
        
    Returns:
        True if the PCH needs regeneration, False otherwise
    """
    if not os.path.exists(pch_file_path):
        return True
        
    pch_mtime = os.path.getmtime(pch_file_path)
    import time
    if time.time() - pch_mtime > threshold_hours * 3600:
        return True
        
    # Check if any of the included headers are newer than the PCH
    for header in headers_to_precompile:
        if os.path.exists(header):
            if os.path.getmtime(header) > pch_mtime:
                return True
                
    return False


def should_use_pch_for_file(
    source_file: str, 
    config: PCHConfig
) -> bool:
    """
    Determines if PCH should be used for a specific source file.
    
    Args:
        source_file: Path to the source file
        config: PCH configuration
        
    Returns:
        True if PCH should be used for the file, False otherwise
    """
    filename = os.path.basename(source_file)
    
    # Check if file is in force exclude list
    for exclude in config.force_exclude:
        if exclude in filename:
            return False
            
    # Check if file is explicitly marked to skip PCH
    try:
        with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            if '// NOPCH' in content or '#pragma nopch' in content:
                return False
    except Exception:
        pass
        
    # Generally, all C++ source files can use PCH
    _, ext = os.path.splitext(filename.lower())
    if ext in ['.cpp', '.cxx', '.cc', '.c++']:
        return True
        
    return False