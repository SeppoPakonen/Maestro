"""
Repository analysis and resolution commands for Maestro CLI.

This module is a compatibility shim that re-exports from the maestro.commands.repo package.

Commands:
- maestro repo resolve - Scan repository for packages across build systems
- maestro repo show - Show repository scan results
- maestro repo pkg - Package query and inspection
- maestro repo conf - Show build configurations
- maestro repo asm - Assembly management
- maestro repo refresh - Refresh repository metadata
- maestro repo hier - Repository hierarchy
- maestro repo conventions - Naming conventions
- maestro repo rules - Repository rules
- maestro repo profile - Repo profile management
- maestro repo evidence - Evidence pack generation
"""

from __future__ import annotations

# Re-export everything from the package for backward compatibility
from maestro.commands.repo import (
    # Parser and dispatcher
    add_repo_parser,
    handle_repo_command,
    # Utilities
    find_repo_root,
    write_repo_artifacts,
    load_repo_index,
    build_repo_hierarchy,
    save_hierarchy,
    load_hierarchy,
    load_hierarchy_overrides,
    merge_hierarchy_overrides,
    print_hierarchy_tree,
    # Package handlers
    handle_repo_pkg_list,
    handle_repo_pkg_info,
    handle_repo_pkg_files,
    handle_repo_pkg_groups,
    handle_repo_pkg_search,
    handle_repo_pkg_tree,
    handle_repo_pkg_conf,
    handle_repo_refresh_all,
    handle_repo_refresh_help,
    handle_repo_hier_edit,
    handle_repo_hier,
    handle_repo_conventions_detect,
    handle_repo_conventions_show,
    handle_repo_rules_show,
    handle_repo_rules_edit,
    handle_repo_rules_inject,
    # Profile handlers
    handle_repo_profile_show,
    handle_repo_profile_init,
    # Evidence handlers
    handle_repo_evidence_pack,
    handle_repo_evidence_list,
    handle_repo_evidence_show,
)

__all__ = [
    # Parser and dispatcher
    'add_repo_parser',
    'handle_repo_command',
    # Utilities
    'find_repo_root',
    'write_repo_artifacts',
    'load_repo_index',
    'build_repo_hierarchy',
    'save_hierarchy',
    'load_hierarchy',
    'load_hierarchy_overrides',
    'merge_hierarchy_overrides',
    'print_hierarchy_tree',
    # Package handlers
    'handle_repo_pkg_list',
    'handle_repo_pkg_info',
    'handle_repo_pkg_files',
    'handle_repo_pkg_groups',
    'handle_repo_pkg_search',
    'handle_repo_pkg_tree',
    'handle_repo_pkg_conf',
    'handle_repo_refresh_all',
    'handle_repo_refresh_help',
    'handle_repo_hier_edit',
    'handle_repo_hier',
    'handle_repo_conventions_detect',
    'handle_repo_conventions_show',
    'handle_repo_rules_show',
    'handle_repo_rules_edit',
    'handle_repo_rules_inject',
    # Profile handlers
    'handle_repo_profile_show',
    'handle_repo_profile_init',
    # Evidence handlers
    'handle_repo_evidence_pack',
    'handle_repo_evidence_list',
    'handle_repo_evidence_show',
]
