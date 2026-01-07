"""
Argument parser setup for repo commands.

Defines all CLI arguments and subcommands for maestro repo.
"""

from __future__ import annotations
import argparse

def add_repo_parser(subparsers):
    """
    Add repo command parser to the main argument parser.

    Args:
        subparsers: The subparsers object from argparse
    """
    repo_parser = subparsers.add_parser('repo', help='Repository analysis and resolution commands')
    repo_subparsers = repo_parser.add_subparsers(dest='repo_subcommand', help='Repository subcommands')

    # repo resolve
    repo_resolve_parser = repo_subparsers.add_parser('resolve', aliases=['res'], help='Scan repository for packages across build systems')
    repo_resolve_parser.add_argument('--path', help='Path to repository to scan (default: current directory)')
    repo_resolve_parser.add_argument('--json', action='store_true', help='Output results in JSON format')
    repo_resolve_parser.add_argument('--no-write', action='store_true', help='Skip writing artifacts to docs/maestro/')
    repo_resolve_parser.add_argument('--no-hub-update', action='store_true', help='Skip updating hub index')
    repo_resolve_parser.add_argument('--find-root', action='store_true', help='Find repository root with docs/maestro instead of scanning current directory')
    repo_resolve_parser.add_argument('--include-user-config', dest='include_user_config', action='store_true', help='Include user assemblies from ~/.config/u++/ide/*.var')
    repo_resolve_parser.add_argument('--no-user-config', dest='include_user_config', action='store_false', default=True, help='Skip reading user assembly config (default)')
    repo_resolve_parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose scan information')

    # repo show
    repo_show_parser = repo_subparsers.add_parser('show', aliases=['sh'], help='Show repository scan results from docs/maestro/')
    repo_show_parser.add_argument('--json', action='store_true', help='Output results in JSON format')
    repo_show_parser.add_argument('--path', help='Path to repository root (default: auto-detect via docs/maestro/)')

    # repo import-roadmap
    repo_import_parser = repo_subparsers.add_parser(
        'import-roadmap',
        help='Import roadmap/task folders into Maestro tracks/phases/tasks'
    )
    repo_import_parser.add_argument('--roadmap', required=True, help='Path to roadmap directory')
    repo_import_parser.add_argument('--tasks', required=True, help='Path to task directory')
    repo_import_parser.add_argument('--path', help='Path to repository root (default: auto-detect via docs/maestro/)')
    repo_import_parser.add_argument('--apply', action='store_true', help='Write tracks/phases/tasks to docs/maestro/')
    repo_import_parser.add_argument('--dry-run', action='store_true', help='Preview import plan (default)')

    # repo pkg (main parser for package commands)
    repo_pkg_parser = repo_subparsers.add_parser('pkg', help='Package query and management commands')
    repo_pkg_subparsers = repo_pkg_parser.add_subparsers(dest='pkg_subcommand', help='Package subcommands')

    # repo pkg info (default subcommand)
    repo_pkg_info_parser = repo_pkg_subparsers.add_parser('info', help='Display information about a package')
    repo_pkg_info_parser.add_argument('package_name', nargs='?', help='Package name to inspect (supports partial match)')
    repo_pkg_info_parser.add_argument('--path', help='Path to repository root (default: auto-detect via docs/maestro/)')
    repo_pkg_info_parser.add_argument('--json', action='store_true', help='Output results in JSON format')
    repo_pkg_info_parser.add_argument('--show-groups', action='store_true', help='Show package file groups')
    repo_pkg_info_parser.add_argument('--group', help='Filter to specific group (use with --show-groups)')
    
    # repo pkg add
    repo_pkg_add_parser = repo_pkg_subparsers.add_parser('add', help='Add a package to the repository model')
    repo_pkg_add_parser.add_argument('package_path', help='Relative path to the package directory')
    repo_pkg_add_parser.add_argument('--path', help='Path to repository root (default: auto-detect via docs/maestro/)')
    repo_pkg_add_parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose output')

    # Existing repo pkg subcommands
    repo_pkg_list_parser = repo_pkg_subparsers.add_parser('list', help='List files in a package')
    repo_pkg_list_parser.add_argument('package_name', help='Package name')
    repo_pkg_list_parser.add_argument('--path', help='Path to repository root')
    repo_pkg_list_parser.add_argument('--json', action='store_true', help='Output results in JSON format')

    repo_pkg_search_parser = repo_pkg_subparsers.add_parser('search', help='Search for files within a package')
    repo_pkg_search_parser.add_argument('package_name', help='Package name')
    repo_pkg_search_parser.add_argument('query', help='Search query')
    repo_pkg_search_parser.add_argument('--path', help='Path to repository root')
    repo_pkg_search_parser.add_argument('--json', action='store_true', help='Output results in JSON format')

    repo_pkg_tree_parser = repo_pkg_subparsers.add_parser('tree', help='Display package dependency tree')
    repo_pkg_tree_parser.add_argument('package_name', help='Package name')
    repo_pkg_tree_parser.add_argument('--path', help='Path to repository root')
    repo_pkg_tree_parser.add_argument('--json', action='store_true', help='Output results in JSON format')
    repo_pkg_tree_parser.add_argument('--deep', action='store_true', help='Show full tree with all duplicates')
    repo_pkg_tree_parser.add_argument('--config', help='Config number (for tree with config filter)')

    repo_pkg_conf_parser = repo_pkg_subparsers.add_parser('conf', help='Show package configurations')
    repo_pkg_conf_parser.add_argument('package_name', help='Package name')
    repo_pkg_conf_parser.add_argument('--path', help='Path to repository root')
    repo_pkg_conf_parser.add_argument('--json', action='store_true', help='Output results in JSON format')

    repo_pkg_groups_parser = repo_pkg_subparsers.add_parser('groups', help='Show package file groups')
    repo_pkg_groups_parser.add_argument('package_name', help='Package name')
    repo_pkg_groups_parser.add_argument('--path', help='Path to repository root')
    repo_pkg_groups_parser.add_argument('--json', action='store_true', help='Output results in JSON format')

    # repo asm
    repo_asm_parser = repo_subparsers.add_parser('asm', aliases=['a', 'assembly'], help='Assembly query commands')
    repo_asm_parser.add_argument('--path', help='Path to repository root (default: auto-detect via docs/maestro/)')
    repo_asm_subparsers = repo_asm_parser.add_subparsers(dest='asm_subcommand', help='Assembly subcommands')

    repo_asm_list = repo_asm_subparsers.add_parser('list', aliases=['ls', 'l'], help='List assemblies')
    repo_asm_list.add_argument('--path', help='Path to repository root (default: auto-detect via docs/maestro/)')
    repo_asm_list.add_argument('--json', action='store_true', help='Output in JSON format')

    repo_asm_show = repo_asm_subparsers.add_parser('show', aliases=['sh', 's'], help='Show assembly details')
    repo_asm_show.add_argument('assembly_ref', help='Assembly ID or name')
    repo_asm_show.add_argument('--path', help='Path to repository root (default: auto-detect via docs/maestro/)')
    repo_asm_show.add_argument('--json', action='store_true', help='Output in JSON format')

    repo_asm_import = repo_asm_subparsers.add_parser('import', help='Import assembly configuration from .var file')
    repo_asm_import.add_argument('var_file', help='Path to the .var file')
    repo_asm_import.add_argument('--name', help='Name of the configuration (defaults to var filename)')
    repo_asm_import.add_argument('--path', help='Path to repository root (default: auto-detect via docs/maestro/)')
    repo_asm_import.add_argument('--json', action='store_true', help='Output in JSON format')

    # repo asm conf
    repo_asm_conf_parser = repo_asm_subparsers.add_parser('conf', aliases=['c'], help='Assembly configuration commands')
    repo_asm_conf_parser.add_argument('--path', help='Path to repository root (default: auto-detect via docs/maestro/)')
    repo_asm_conf_subparsers = repo_asm_conf_parser.add_subparsers(dest='asm_conf_subcommand', help='Assembly configuration subcommands')

    repo_asm_conf_list = repo_asm_conf_subparsers.add_parser('list', aliases=['ls', 'l'], help='List assembly configurations')
    repo_asm_conf_list.add_argument('--path', help='Path to repository root (default: auto-detect via docs/maestro/)')
    repo_asm_conf_list.add_argument('--json', action='store_true', help='Output in JSON format')

    repo_asm_conf_add = repo_asm_conf_subparsers.add_parser('add', aliases=['create'], help='Add a new assembly configuration')
    repo_asm_conf_add.add_argument('name', help='Name of the configuration to add')
    repo_asm_conf_add.add_argument('packages', nargs='*', help='List of directory paths to include in the configuration')
    repo_asm_conf_add.add_argument('--path', help='Path to repository root (default: auto-detect via docs/maestro/)')
    repo_asm_conf_add.add_argument('--json', action='store_true', help='Output in JSON format')

    repo_asm_conf_import = repo_asm_conf_subparsers.add_parser('import', help='Import assembly configuration from .var file')
    repo_asm_conf_import.add_argument('var_file', help='Path to the .var file')
    repo_asm_conf_import.add_argument('--name', help='Name of the configuration (defaults to var filename)')
    repo_asm_conf_import.add_argument('--path', help='Path to repository root (default: auto-detect via docs/maestro/)')
    repo_asm_conf_import.add_argument('--json', action='store_true', help='Output in JSON format')

    repo_asm_conf_remove = repo_asm_conf_subparsers.add_parser('remove', aliases=['rm', 'delete'], help='Remove an assembly configuration')
    repo_asm_conf_remove.add_argument('name', help='Name of the configuration to remove')
    repo_asm_conf_remove.add_argument('--path', help='Path to repository root (default: auto-detect via docs/maestro/)')
    repo_asm_conf_remove.add_argument('--json', action='store_true', help='Output in JSON format')

    repo_asm_conf_modify = repo_asm_conf_subparsers.add_parser('modify', aliases=['update'], help='Modify an existing assembly configuration')
    repo_asm_conf_modify.add_argument('name', help='Name of the configuration to modify')
    repo_asm_conf_modify.add_argument('packages', nargs='*', help='New list of packages to include in the configuration')
    repo_asm_conf_modify.add_argument('--path', help='Path to repository root (default: auto-detect via docs/maestro/)')
    repo_asm_conf_modify.add_argument('--json', action='store_true', help='Output in JSON format')

    repo_asm_conf_select = repo_asm_conf_subparsers.add_parser('select', help='Select an active assembly configuration')
    repo_asm_conf_select.add_argument('name', help='Name of the configuration to select')
    repo_asm_conf_select.add_argument('--path', help='Path to repository root (default: auto-detect via docs/maestro/)')
    repo_asm_conf_select.add_argument('--json', action='store_true', help='Output in JSON format')

    # repo conf
    repo_conf_parser = repo_subparsers.add_parser('conf', aliases=['c'], help='Repo configuration selection and defaults')
    repo_conf_parser.add_argument('--path', help='Path to repository root (default: auto-detect via docs/maestro/)')
    repo_conf_subparsers = repo_conf_parser.add_subparsers(dest='conf_subcommand', help='Repo conf subcommands')

    repo_conf_show = repo_conf_subparsers.add_parser('show', help='Show repo configuration defaults')
    repo_conf_show.add_argument('--json', action='store_true', help='Output results in JSON format')

    repo_conf_list = repo_conf_subparsers.add_parser('list', help='List configured targets')
    repo_conf_list.add_argument('--json', action='store_true', help='Output results in JSON format')

    repo_conf_select = repo_conf_subparsers.add_parser('select-default', help='Select default repo configuration')
    repo_conf_select.add_argument('entity', choices=['target', 'asm'], help='Entity to select (target, asm)')
    repo_conf_select.add_argument('value', help='Default value for the selected entity')

    # repo refresh
    repo_refresh_parser = repo_subparsers.add_parser('refresh', help='Refresh repository metadata')
    repo_refresh_subparsers = repo_refresh_parser.add_subparsers(dest='refresh_subcommand', help='Refresh subcommands')

    # repo refresh all
    repo_refresh_all_parser = repo_refresh_subparsers.add_parser('all', help='Full refresh (resolve + conventions + rules)')
    repo_refresh_all_parser.add_argument('--path', help='Path to repository (default: auto-detect)')
    repo_refresh_all_parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose output')

    # repo refresh help
    repo_refresh_subparsers.add_parser('help', aliases=['h'], help='Show what refresh all does')

    # repo hier
    repo_hier_parser = repo_subparsers.add_parser('hier', help='Show/edit repository hierarchy')
    repo_hier_subparsers = repo_hier_parser.add_subparsers(dest='hier_subcommand', help='Hierarchy subcommands')

    # repo hier show (default)
    repo_hier_show_parser = repo_hier_subparsers.add_parser('show', help='Show repository hierarchy')
    repo_hier_show_parser.add_argument('packages', nargs='*', help='Package names to show dependency hierarchy for (optional, shows directory hierarchy if omitted)')
    repo_hier_show_parser.add_argument('--path', help='Path to repository (default: auto-detect)')
    repo_hier_show_parser.add_argument('--json', action='store_true', help='Output in JSON format')
    repo_hier_show_parser.add_argument('--show-files', action='store_true', help='Show file groups in tree view')
    repo_hier_show_parser.add_argument('--rebuild', action='store_true', help='Force rebuild hierarchy from scan data')

    # repo hier edit
    repo_hier_edit_parser = repo_hier_subparsers.add_parser('edit', help='Edit hierarchy overrides in $EDITOR')
    repo_hier_edit_parser.add_argument('--path', help='Path to repository (default: auto-detect)')

    # Also add these arguments to the main hier parser for backward compatibility
    repo_hier_parser.add_argument('--path', help='Path to repository (default: auto-detect)')
    repo_hier_parser.add_argument('--json', action='store_true', help='Output in JSON format')
    repo_hier_parser.add_argument('--show-files', action='store_true', help='Show file groups in tree view')
    repo_hier_parser.add_argument('--rebuild', action='store_true', help='Force rebuild hierarchy from scan data')

    # repo conventions
    repo_conventions_parser = repo_subparsers.add_parser('conventions', help='Show/edit detected conventions')
    repo_conventions_subparsers = repo_conventions_parser.add_subparsers(dest='conventions_subcommand', help='Conventions subcommands')

    # repo conventions detect
    repo_conventions_detect_parser = repo_conventions_subparsers.add_parser('detect', help='Detect naming conventions')
    repo_conventions_detect_parser.add_argument('--path', help='Path to repository (default: auto-detect)')
    repo_conventions_detect_parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose output')

    # repo conventions show (default)
    repo_conventions_show_parser = repo_conventions_subparsers.add_parser('show', help='Show current conventions')
    repo_conventions_show_parser.add_argument('--path', help='Path to repository (default: auto-detect)')

    # repo profile
    repo_profile_parser = repo_subparsers.add_parser('profile', help='Repository profile management')
    repo_profile_subparsers = repo_profile_parser.add_subparsers(dest='profile_subcommand', help='Profile subcommands')

    # repo profile show
    repo_profile_show_parser = repo_profile_subparsers.add_parser('show', help='Show repository profile')
    repo_profile_show_parser.add_argument('--path', help='Path to repository (default: current directory)')
    repo_profile_show_parser.add_argument('--json', action='store_true', help='Output in JSON format')

    # repo profile init
    repo_profile_init_parser = repo_profile_subparsers.add_parser('init', help='Initialize repository profile with heuristic inference')
    repo_profile_init_parser.add_argument('--path', help='Path to repository (default: current directory)')
    repo_profile_init_parser.add_argument('--maestro-dir', action='store_true', help='Save to docs/maestro/ (default)')
    repo_profile_init_parser.add_argument('--dot-maestro', action='store_true', help='Save to .maestro/')
    repo_profile_init_parser.add_argument('--force', action='store_true', help='Overwrite existing profile')

    # repo evidence
    repo_evidence_parser = repo_subparsers.add_parser('evidence', help='Evidence pack generation and management')
    repo_evidence_subparsers = repo_evidence_parser.add_subparsers(dest='evidence_subcommand', help='Evidence subcommands')

    # repo evidence pack
    repo_evidence_pack_parser = repo_evidence_subparsers.add_parser('pack', help='Generate evidence pack from repository')
    repo_evidence_pack_parser.add_argument('--path', help='Path to repository (default: current directory)')
    repo_evidence_pack_parser.add_argument('--json', action='store_true', help='Output pack as JSON to stdout (no save)')
    repo_evidence_pack_parser.add_argument('--save', action='store_true', help='Save pack to docs/maestro/evidence_packs/')
    repo_evidence_pack_parser.add_argument('--max-files', type=int, help='Maximum files to collect (default: from profile or 60)')
    repo_evidence_pack_parser.add_argument('--max-bytes', type=int, help='Maximum bytes to collect (default: from profile or 250000)')
    repo_evidence_pack_parser.add_argument('--max-help-calls', type=int, help='Maximum CLI help calls (default: from profile or 6)')
    repo_evidence_pack_parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose output')

    # repo evidence list
    repo_evidence_list_parser = repo_evidence_subparsers.add_parser('list', aliases=['ls'], help='List saved evidence packs')
    repo_evidence_list_parser.add_argument('--path', help='Path to repository (default: current directory)')
    repo_evidence_list_parser.add_argument('--json', action='store_true', help='Output in JSON format')

    # repo evidence show
    repo_evidence_show_parser = repo_evidence_subparsers.add_parser('show', help='Show evidence pack details')
    repo_evidence_show_parser.add_argument('pack_id', help='Evidence pack ID to show')
    repo_evidence_show_parser.add_argument('--path', help='Path to repository (default: current directory)')
    repo_evidence_show_parser.add_argument('--json', action='store_true', help='Output in JSON format')
    repo_evidence_show_parser.add_argument('--show-content', action='store_true', help='Show item content (may be large)')

    # repo rules
    repo_rules_parser = repo_subparsers.add_parser('rules', help='Show/edit repository rules')
    repo_rules_subparsers = repo_rules_parser.add_subparsers(dest='rules_subcommand', help='Rules subcommands')

    # repo rules show (default)
    repo_rules_show_parser = repo_rules_subparsers.add_parser('show', help='Show current rules')
    repo_rules_show_parser.add_argument('--path', help='Path to repository (default: auto-detect)')

    # repo rules edit
    repo_rules_edit_parser = repo_rules_subparsers.add_parser('edit', help='Edit rules in $EDITOR')
    repo_rules_edit_parser.add_argument('--path', help='Path to repository (default: auto-detect)')

    # repo rules inject
    repo_rules_inject_parser = repo_rules_subparsers.add_parser('inject', help='Show rules for AI injection (testing)')
    repo_rules_inject_parser.add_argument('--path', help='Path to repository (default: auto-detect)')
    repo_rules_inject_parser.add_argument('--context', default='general',
                                           choices=['general', 'build', 'refactor', 'security', 'performance', 'fix', 'feature'],
                                           help='Context for rule selection (default: general)')

    # repo hub (cross-repo package discovery and linking)
    repo_hub_parser = repo_subparsers.add_parser('hub', help='Cross-repo package discovery and linking')
    repo_hub_subparsers = repo_hub_parser.add_subparsers(dest='hub_subcommand', help='Hub subcommands')

    # repo hub scan
    repo_hub_scan_parser = repo_hub_subparsers.add_parser('scan', help='Scan repository and add to hub index')
    repo_hub_scan_parser.add_argument('path', nargs='?', help='Path to repository to scan (default: current directory)')
    repo_hub_scan_parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose output')

    # repo hub list
    repo_hub_list_parser = repo_hub_subparsers.add_parser('list', aliases=['ls'], help='List all repositories in hub index')
    repo_hub_list_parser.add_argument('--json', action='store_true', help='Output in JSON format')
    repo_hub_list_parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose output')

    # repo hub show
    repo_hub_show_parser = repo_hub_subparsers.add_parser('show', help='Show repository details')
    repo_hub_show_parser.add_argument('repo_id', help='Repository ID to show')
    repo_hub_show_parser.add_argument('--json', action='store_true', help='Output in JSON format')
    repo_hub_show_parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose output')

    # repo hub find
    repo_hub_find_parser = repo_hub_subparsers.add_parser('find', help='Find packages or repos')
    repo_hub_find_subparsers = repo_hub_find_parser.add_subparsers(dest='find_subcommand', help='Find subcommands')

    # repo hub find package
    repo_hub_find_package_parser = repo_hub_find_subparsers.add_parser('package', aliases=['pkg', 'p'], help='Find package across all repos')
    repo_hub_find_package_parser.add_argument('package_name', help='Package name to search for')
    repo_hub_find_package_parser.add_argument('--json', action='store_true', help='Output in JSON format')
    repo_hub_find_package_parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose output')

    # repo hub link
    repo_hub_link_parser = repo_hub_subparsers.add_parser('link', help='Manage cross-repo links')
    repo_hub_link_subparsers = repo_hub_link_parser.add_subparsers(dest='link_subcommand', help='Link subcommands')

    # repo hub link package
    repo_hub_link_package_parser = repo_hub_link_subparsers.add_parser('package', aliases=['pkg', 'p'], help='Link to external package')
    repo_hub_link_package_parser.add_argument('package_name', help='Local package name')
    repo_hub_link_package_parser.add_argument('--to', dest='to_package_id', required=True, help='Target package ID')
    repo_hub_link_package_parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose output')

    # repo hub link show
    repo_hub_link_show_parser = repo_hub_link_subparsers.add_parser('show', help='Show all hub links')
    repo_hub_link_show_parser.add_argument('--json', action='store_true', help='Output in JSON format')
    repo_hub_link_show_parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose output')

    # repo hub link remove
    repo_hub_link_remove_parser = repo_hub_link_subparsers.add_parser('remove', aliases=['rm'], help='Remove a link')
    repo_hub_link_remove_parser.add_argument('link_id', help='Link ID to remove')
    repo_hub_link_remove_parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose output')

    # repo help
    repo_subparsers.add_parser('help', aliases=['h'], help='Show help for repo commands')

    return repo_parser
