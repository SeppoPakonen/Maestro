"""
Auto-grouping functionality for internal package groups.
"""

from typing import List, Dict, DefaultDict
from collections import defaultdict
from dataclasses import dataclass, field
from .package import FileGroup


class AutoGrouper:
    """Automatically group files by patterns."""

    GROUP_RULES = {
        'Documentation': ['.md', '.txt', '.rst', '.adoc'],
        'Scripts': ['.sh', '.bash', '.zsh', '.py', '.js', '.ts', '.pl', '.rb', '.php'],
        'Configuration': ['.toml', '.yaml', '.yml', '.json', '.ini', '.conf', '.xml'],
        'Build Files': ['Makefile', 'makefile', 'CMakeLists.txt', 'configure.ac', 
                       'pom.xml', 'build.gradle', 'build.gradle.kts', 'settings.gradle', 
                       'gradle.properties', 'Cargo.toml', 'go.mod'],
        'Python': ['.py'],
        'C/C++': ['.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.hxx', '.c++', '.cxx'],
        'Java': ['.java'],
        'Kotlin': ['.kt', '.kts'],
        'Web': ['.html', '.htm', '.css', '.js', '.ts', '.jsx', '.tsx', '.vue', '.svelte'],
        'Data': ['.json', '.xml', '.csv', '.tsv', '.sql', '.db'],
        'Images': ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.bmp', '.tiff'],
        'Audio': ['.mp3', '.wav', '.ogg', '.flac', '.m4a'],
        'Video': ['.mp4', '.avi', '.mov', '.mkv', '.webm'],
        'Fonts': ['.ttf', '.otf', '.woff', '.woff2'],
        'Archive': ['.zip', '.tar', '.gz', '.bz2', '.xz', '.7z'],
        'Other': [],  # Catch-all
    }

    def auto_group(self, files: List[str]) -> List[FileGroup]:
        """
        Group files by extension/pattern.
        
        Args:
            files: List of file paths to group
            
        Returns:
            List of FileGroup objects
        """
        groups: DefaultDict[str, List[str]] = defaultdict(list)

        for file in files:
            matched = False
            file_lower = file.lower()
            
            for group_name, patterns in self.GROUP_RULES.items():
                if group_name == 'Other':
                    continue
                    
                if any(file.endswith(ext) for ext in patterns):
                    groups[group_name].append(file)
                    matched = True
                    break
                elif any(pattern in file_lower for pattern in [p.lower() for p in patterns if not p.startswith('.')]):
                    groups[group_name].append(file)
                    matched = True
                    break

            if not matched:
                groups['Other'].append(file)

        result = []
        for name, files_list in sorted(groups.items()):
            if files_list:  # Only include non-empty groups
                result.append(FileGroup(
                    name=name,
                    files=sorted(files_list),
                    readonly=False,
                    auto_generated=True
                ))

        return result