"""
Repository commands package.

Re-exports for backward compatibility with maestro.commands.repo imports.
"""

from __future__ import annotations

# Export parser and main dispatcher
from .parser import add_repo_parser
from .handlers import handle_repo_command

# Export utility functions
from .utils import (
    find_repo_root,
    write_repo_artifacts,
    load_repo_index,
    build_repo_hierarchy,
    save_hierarchy,
    load_hierarchy,
    load_hierarchy_overrides,
    merge_hierarchy_overrides,
    print_hierarchy_tree,
)

# Export all package handlers
from .resolve_cmd import (
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
)

# Export profile handlers
from .profile_cmd import (
    handle_repo_profile_show,
    handle_repo_profile_init,
)

# Export evidence handlers
from .evidence_cmd import (
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
