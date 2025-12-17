"""
Preprocessor dependency tracker (PPInfo) for U++ builds.

Implements sophisticated header dependency tracking with:
- Include file resolution
- Macro/define tracking
- Conditional include handling (#if flagXXX)
- Cache for faster incremental builds
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from .cache import PPInfoCache


class PPInfo:
    """
    Preprocessor dependency information tracker.
    
    Similar to U++'s PPInfo class, this tracks header dependencies
    and handles conditional compilation directives.
    """
    
    def __init__(self, cache: PPInfoCache = None):
        self.cache = cache or PPInfoCache()
        self.include_regex = re.compile(r'^\s*#\s*include\s+(["<])([^">]+)([">])', re.MULTILINE)
        self.define_regex = re.compile(r'^\s*#\s*define\s+(\w+)', re.MULTILINE)
        self.ifdef_regex = re.compile(r'^\s*#\s*(ifdef|ifndef|if)\s+(.+)', re.MULTILINE)
        self.endif_regex = re.compile(r'^\s*#\s*endif', re.MULTILINE)
        self.else_regex = re.compile(r'^\s*#\s*else', re.MULTILINE)
        self.elif_regex = re.compile(r'^\s*#\s*elif', re.MULTILINE)
    
    def extract_dependencies(self, source_file: str, include_paths: List[str] = None) -> Tuple[List[str], List[str]]:
        """
        Extract dependencies (headers) and defines from a source file.
        
        Args:
            source_file: Path to the source file to analyze
            include_paths: List of include paths to resolve headers
            
        Returns:
            Tuple of (headers, defines) found in the file
        """
        if include_paths is None:
            include_paths = []
        
        # Check if we can use cached results
        if not self.cache.needs_preprocess_rerun(source_file, [], []):
            cached_includes = self.cache.get_includes_for_file(source_file)
            return cached_includes, []
        
        headers = set()
        defines = set()
        
        try:
            with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Fallback to latin-1 if UTF-8 fails
            with open(source_file, 'r', encoding='latin-1', errors='ignore') as f:
                content = f.read()
        
        # Extract includes
        for match in self.include_regex.finditer(content):
            header_name = match.group(2)
            
            # Determine if it's a system include (<>) or local include ("")
            is_system = match.group(1) == '<'
            
            # Resolve the header to an actual file path
            header_path = self._resolve_header(header_name, source_file, include_paths, is_system)
            if header_path:
                headers.add(header_path)
        
        # Extract defines
        for match in self.define_regex.finditer(content):
            define_name = match.group(1)
            defines.add(define_name)
        
        # Cache the results
        self.cache.track_preprocessor_info(
            source_file,
            list(headers),
            list(defines),
            []
        )
        self.cache.save()
        
        return list(headers), list(defines)
    
    def _resolve_header(self, header_name: str, source_file: str, include_paths: List[str], is_system: bool) -> Optional[str]:
        """
        Resolve a header name to an actual file path.
        
        Args:
            header_name: Name of the header (e.g., "Core/Core.h", <stdio.h>)
            source_file: Path to the source file that includes this header
            include_paths: List of include paths to search
            is_system: True if it's a system include (<...>), False if local ("...")
            
        Returns:
            Full path to the header file, or None if not found
        """
        # For local includes ("..."), first check relative to source file
        if not is_system:
            local_path = Path(source_file).parent / header_name
            if local_path.exists():
                return str(local_path.resolve())
        
        # Search in include paths
        for inc_path in include_paths:
            full_path = Path(inc_path) / header_name
            if full_path.exists():
                return str(full_path.resolve())
        
        # If not found in include paths, return None
        return None
    
    def track_conditional_includes(self, source_file: str, active_defines: Set[str], include_paths: List[str] = None) -> List[str]:
        """
        Track headers that are conditionally included based on preprocessor defines.
        
        This handles #ifdef, #ifndef, #if, etc. directives to determine which
        headers are included based on the current set of active defines.
        """
        if include_paths is None:
            include_paths = []
        
        headers = set()
        
        try:
            with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            with open(source_file, 'r', encoding='latin-1', errors='ignore') as f:
                lines = f.readlines()
        
        # Track conditional compilation state
        condition_stack = [True]  # True means the current block is active
        
        for line in lines:
            line = line.strip()
            
            # Check for conditional directives
            ifdef_match = self.ifdef_regex.match(line)
            if ifdef_match:
                directive = ifdef_match.group(1)
                condition = ifdef_match.group(2).strip()
                
                # Evaluate the condition based on active defines
                is_active = self._evaluate_condition(condition, active_defines, directive)
                
                # Push to stack: new state is current state AND condition result
                condition_stack.append(condition_stack[-1] and is_active)
                continue
            
            # Check for else/elif directives
            elif_match = self.else_regex.match(line)
            elif_match_alt = self.elif_regex.match(line)
            
            if elif_match:
                # For #else, flip the state within the current conditional block
                if len(condition_stack) > 1:
                    parent_state = condition_stack[-2]
                    current_state = condition_stack.pop()
                    # The else block is active if parent was active but if-block was not
                    else_state = parent_state and not self._is_prev_block_active(source_file, lines, lines.index(line))
                    condition_stack.append(else_state)
            elif elif_match_alt:
                # For #elif, evaluate the new condition
                if len(condition_stack) > 1:
                    parent_state = condition_stack[-2]
                    condition = line.split(None, 2)[1].strip() if len(line.split(None, 2)) > 2 else ""
                    if condition:
                        is_active = self._evaluate_condition(condition, active_defines, "if")
                        condition_stack[-1] = parent_state and is_active
            
            # Check for endif
            endif_match = self.endif_regex.match(line)
            if endif_match:
                if len(condition_stack) > 1:
                    condition_stack.pop()
                continue
            
            # If current block is active, process includes
            if condition_stack[-1]:
                include_match = self.include_regex.match(line)
                if include_match:
                    header_name = include_match.group(2)
                    is_system = include_match.group(1) == '<'
                    
                    header_path = self._resolve_header(header_name, source_file, include_paths, is_system)
                    if header_path:
                        headers.add(header_path)
        
        return list(headers)
    
    def _evaluate_condition(self, condition: str, active_defines: Set[str], directive: str) -> bool:
        """
        Evaluate a preprocessor condition.
        
        Args:
            condition: The condition string (e.g., "DEBUG", "FLAG1 && FLAG2")
            active_defines: Set of currently defined macros
            directive: The directive type ('ifdef', 'ifndef', 'if')
            
        Returns:
            True if condition is satisfied, False otherwise
        """
        condition = condition.strip()
        
        if directive == 'ifdef':
            return condition in active_defines
        elif directive == 'ifndef':
            return condition not in active_defines
        elif directive == 'if':
            # Simple evaluation for conditions like "FLAG" or "FLAG == 1"
            # This is a simplified implementation - a full implementation would require
            # a more sophisticated preprocessor
            condition = condition.strip()
            
            # Handle simple cases: single flag or flag comparison
            if '==' in condition:
                left, right = condition.split('==', 1)
                left = left.strip()
                right = right.strip()
                
                if left in active_defines:
                    # If the macro is defined, check its value if possible
                    # For now, assume it's true if defined with any value
                    return True
            elif '&&' in condition:
                # Handle logical AND
                parts = [part.strip() for part in condition.split('&&')]
                return all(part in active_defines for part in parts)
            elif '||' in condition:
                # Handle logical OR
                parts = [part.strip() for part in condition.split('||')]
                return any(part in active_defines for part in parts)
            else:
                # Simple flag check
                return condition in active_defines
        
        return False
    
    def _is_prev_block_active(self, source_file: str, lines: List[str], current_index: int) -> bool:
        """
        Helper to determine if the previous block in an if/elif/else chain was active.
        This is a simplified implementation.
        """
        # In a real implementation, this would need to analyze the condition of the previous block
        # For now, we'll return False to indicate that the else block should be considered
        return False
    
    def get_incremental_dependencies(self, source_file: str, include_paths: List[str] = None, 
                                   active_defines: Set[str] = None) -> Tuple[List[str], List[str]]:
        """
        Get dependencies considering incremental build requirements.
        
        Args:
            source_file: Path to the source file
            include_paths: List of include paths
            active_defines: Set of active preprocessor defines
            
        Returns:
            Tuple of (headers, defines) that may affect the build
        """
        if include_paths is None:
            include_paths = []
        if active_defines is None:
            active_defines = set()
        
        # Get basic dependencies
        headers, defines = self.extract_dependencies(source_file, include_paths)
        
        # Add conditionally included headers
        if active_defines:
            cond_headers = self.track_conditional_includes(source_file, active_defines, include_paths)
            headers.extend(cond_headers)
        
        return list(set(headers)), list(set(defines))