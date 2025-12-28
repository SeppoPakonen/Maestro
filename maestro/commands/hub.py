"""
Hub command handlers for cross-repo package discovery and linking.

Commands:
- maestro repo hub scan [PATH] - Scan repository and add to hub index
- maestro repo hub list - List all repositories in hub index
- maestro repo hub show <REPO_ID> - Show repository details
- maestro repo hub find package <NAME> - Find package across repos
- maestro repo hub link package <NAME> --to <PKG_ID> - Link to external package
- maestro repo hub link show - Show all hub links
- maestro repo hub link remove <LINK_ID> - Remove a link
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

from maestro.modules.utils import (
    print_header,
    print_success,
    print_warning,
    print_error,
    print_info,
    print_debug,
    Colors
)
from maestro.repo.hub.index import HubIndexManager
from maestro.repo.hub.scanner import HubScanner
from maestro.repo.hub.resolver import HubResolver, FindResult
from maestro.repo.hub.link_store import HubLinkStore
from maestro.repo.storage import find_repo_root as find_repo_root_v3


def handle_hub_scan(args) -> int:
    """
    Scan a repository and add it to the hub index.

    Args:
        args: Command arguments with 'path' and 'verbose' attributes

    Returns:
        Exit code (0 for success)
    """
    repo_path = getattr(args, 'path', None) or '.'
    verbose = getattr(args, 'verbose', False)

    try:
        repo_path_resolved = str(Path(repo_path).resolve())

        if verbose:
            print_info(f"Scanning repository: {repo_path_resolved}", 2)

        scanner = HubScanner()
        repo_record = scanner.scan_repository(repo_path_resolved, verbose=verbose)
        scanner.update_hub_index(repo_record, verbose=verbose)

        print_success(f"Repository added to hub index", 2)
        print_info(f"  Repo ID: {repo_record.repo_id}", 2)
        print_info(f"  Path: {repo_record.path}", 2)
        print_info(f"  Packages: {len(repo_record.packages)}", 2)

        if verbose and repo_record.packages:
            print()
            print_info("Packages found:", 2)
            for pkg in repo_record.packages[:10]:
                print_info(f"  - {pkg.name} ({pkg.build_system})", 3)
            if len(repo_record.packages) > 10:
                print_info(f"  ... and {len(repo_record.packages) - 10} more", 3)

        return 0
    except Exception as e:
        print_error(f"Failed to scan repository: {e}", 2)
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


def handle_hub_list(args) -> int:
    """
    List all repositories in the hub index.

    Args:
        args: Command arguments with 'json' and 'verbose' attributes

    Returns:
        Exit code (0 for success)
    """
    json_output = getattr(args, 'json', False)
    verbose = getattr(args, 'verbose', False)

    try:
        hub_index = HubIndexManager()
        index = hub_index.load_index()

        if json_output:
            output = {
                'repos': {
                    repo_id: {
                        'path': info['path'],
                        'last_scanned': info.get('last_scanned', 'unknown'),
                        'packages_count': info.get('packages_count', 0),
                        'git_head': info.get('git_head')
                    }
                    for repo_id, info in index.repos.items()
                }
            }
            print(json.dumps(output, indent=2))
        else:
            print_header("HUB INDEX - REPOSITORIES")
            if not index.repos:
                print()
                print_warning("No repositories in hub index", 2)
                print_info("Run 'maestro repo hub scan <path>' to add repositories", 2)
            else:
                print(f"\nTotal repositories: {len(index.repos)}\n")
                for repo_id, info in sorted(index.repos.items(), key=lambda x: x[1]['path']):
                    print_info(f"Repo ID: {repo_id}", 2)
                    print_info(f"  Path: {info['path']}", 3)
                    print_info(f"  Packages: {info.get('packages_count', 0)}", 3)
                    print_info(f"  Last scanned: {info.get('last_scanned', 'unknown')}", 3)
                    if info.get('git_head'):
                        print_info(f"  Git HEAD: {info['git_head'][:8]}", 3)
                    print()

        return 0
    except Exception as e:
        print_error(f"Failed to list repositories: {e}", 2)
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


def handle_hub_show(args) -> int:
    """
    Show detailed information about a repository.

    Args:
        args: Command arguments with 'repo_id', 'json', and 'verbose' attributes

    Returns:
        Exit code (0 for success)
    """
    repo_id = getattr(args, 'repo_id', None)
    if not repo_id:
        print_error("Repo ID is required", 2)
        return 1

    json_output = getattr(args, 'json', False)
    verbose = getattr(args, 'verbose', False)

    try:
        hub_index = HubIndexManager()
        repo_record = hub_index.load_repo_record(repo_id)

        if not repo_record:
            print_error(f"Repository not found: {repo_id}", 2)
            return 1

        if json_output:
            output = {
                'repo_id': repo_record.repo_id,
                'path': repo_record.path,
                'git_head': repo_record.git_head,
                'scan_timestamp': repo_record.scan_timestamp,
                'packages': [
                    {
                        'pkg_id': pkg.pkg_id,
                        'name': pkg.name,
                        'build_system': pkg.build_system,
                        'dir': pkg.dir,
                        'dependencies': pkg.dependencies
                    }
                    for pkg in repo_record.packages
                ]
            }
            print(json.dumps(output, indent=2))
        else:
            print_header(f"REPOSITORY: {repo_id}")
            print()
            print_info(f"Path: {repo_record.path}", 2)
            print_info(f"Git HEAD: {repo_record.git_head or 'N/A'}", 2)
            print_info(f"Last scanned: {repo_record.scan_timestamp}", 2)
            print_info(f"Packages: {len(repo_record.packages)}", 2)
            print()

            if repo_record.packages:
                print_header("PACKAGES")
                print()
                for pkg in repo_record.packages:
                    print_info(f"Package: {pkg.name} ({pkg.build_system})", 2)
                    print_info(f"  ID: {pkg.pkg_id}", 3)
                    print_info(f"  Dir: {pkg.dir}", 3)
                    if pkg.dependencies:
                        print_info(f"  Dependencies: {', '.join(pkg.dependencies)}", 3)
                    print()

        return 0
    except Exception as e:
        print_error(f"Failed to show repository: {e}", 2)
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


def handle_hub_find_package(args) -> int:
    """
    Find a package across all repositories in the hub index.

    Args:
        args: Command arguments with 'package_name', 'json', and 'verbose' attributes

    Returns:
        Exit code (0 for success, 1 for error, 2 for not found)
    """
    package_name = getattr(args, 'package_name', None)
    if not package_name:
        print_error("Package name is required", 2)
        return 1

    json_output = getattr(args, 'json', False)
    verbose = getattr(args, 'verbose', False)

    try:
        resolver = HubResolver()
        result, matches = resolver.find_package(package_name)

        if json_output:
            output = {
                'package_name': package_name,
                'result': result.value,
                'matches': [
                    {
                        'pkg_id': pkg.pkg_id,
                        'name': pkg.name,
                        'build_system': pkg.build_system,
                        'dir': pkg.dir
                    }
                    for pkg in matches
                ]
            }
            print(json.dumps(output, indent=2))
        else:
            if result == FindResult.NOT_FOUND:
                print_warning(f"Package '{package_name}' not found in hub index", 2)
                print_info("Run 'maestro repo hub scan <path>' to add repositories", 2)
                return 2
            elif result == FindResult.SINGLE_MATCH:
                pkg = matches[0]
                print_success(f"Found package: {pkg.name}", 2)
                print_info(f"  Package ID: {pkg.pkg_id}", 3)
                print_info(f"  Build system: {pkg.build_system}", 3)
                print_info(f"  Directory: {pkg.dir}", 3)
                if pkg.dependencies:
                    print_info(f"  Dependencies: {', '.join(pkg.dependencies)}", 3)
            elif result == FindResult.AMBIGUOUS:
                print_warning(f"Multiple packages found for '{package_name}':", 2)
                print()
                for i, pkg in enumerate(matches, 1):
                    print_info(f"[{i}] {pkg.name} ({pkg.build_system})", 3)
                    print_info(f"    Package ID: {pkg.pkg_id}", 4)
                    print_info(f"    Directory: {pkg.dir}", 4)
                    print()
                print_info("Use 'maestro repo hub link package <NAME> --to <PKG_ID>' to link explicitly", 2)

        return 0
    except Exception as e:
        print_error(f"Failed to find package: {e}", 2)
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


def handle_hub_link_package(args) -> int:
    """
    Create a link from local package to external package.

    Args:
        args: Command arguments with 'package_name', 'to_package_id', and 'verbose' attributes

    Returns:
        Exit code (0 for success)
    """
    package_name = getattr(args, 'package_name', None)
    to_package_id = getattr(args, 'to_package_id', None)

    if not package_name:
        print_error("Package name is required", 2)
        return 1

    if not to_package_id:
        print_error("Target package ID is required (use --to <PKG_ID>)", 2)
        return 1

    verbose = getattr(args, 'verbose', False)

    try:
        # Find repo root for link store
        repo_root = find_repo_root_v3()

        resolver = HubResolver(repo_root)
        link = resolver.link_package(
            from_package=package_name,
            to_package_id=to_package_id,
            reason='explicit'
        )

        if not link:
            print_error(f"Target package not found: {to_package_id}", 2)
            print_info("Run 'maestro repo hub find package <NAME>' to search for packages", 2)
            return 1

        print_success(f"Created link: {package_name} -> {link.to_package_name}", 2)
        print_info(f"  Link ID: {link.link_id}", 3)
        print_info(f"  To package ID: {link.to_package_id}", 3)
        print_info(f"  To repo: {link.to_repo_path}", 3)

        return 0
    except Exception as e:
        print_error(f"Failed to create link: {e}", 2)
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


def handle_hub_link_show(args) -> int:
    """
    Show all hub links for the current repository.

    Args:
        args: Command arguments with 'json' and 'verbose' attributes

    Returns:
        Exit code (0 for success)
    """
    json_output = getattr(args, 'json', False)
    verbose = getattr(args, 'verbose', False)

    try:
        repo_root = find_repo_root_v3()
        link_store = HubLinkStore(repo_root)
        links = link_store.load_links()

        if json_output:
            output = {
                'links': [
                    {
                        'link_id': link.link_id,
                        'from_package': link.from_package,
                        'to_package_id': link.to_package_id,
                        'to_package_name': link.to_package_name,
                        'to_repo_path': link.to_repo_path,
                        'created_at': link.created_at,
                        'reason': link.reason
                    }
                    for link in links
                ]
            }
            print(json.dumps(output, indent=2))
        else:
            print_header("HUB LINKS")
            if not links:
                print()
                print_warning("No hub links configured", 2)
                print_info("Use 'maestro repo hub link package <NAME> --to <PKG_ID>' to create links", 2)
            else:
                print(f"\nRepository: {repo_root}")
                print(f"Total links: {len(links)}\n")

                for link in links:
                    print_info(f"Link: {link.from_package} -> {link.to_package_name}", 2)
                    print_info(f"  Link ID: {link.link_id}", 3)
                    print_info(f"  To package: {link.to_package_id}", 3)
                    print_info(f"  To repo: {link.to_repo_path}", 3)
                    print_info(f"  Created: {link.created_at}", 3)
                    print_info(f"  Reason: {link.reason}", 3)
                    print()

        return 0
    except Exception as e:
        print_error(f"Failed to show links: {e}", 2)
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


def handle_hub_link_remove(args) -> int:
    """
    Remove a hub link.

    Args:
        args: Command arguments with 'link_id' and 'verbose' attributes

    Returns:
        Exit code (0 for success)
    """
    link_id = getattr(args, 'link_id', None)
    if not link_id:
        print_error("Link ID is required", 2)
        return 1

    verbose = getattr(args, 'verbose', False)

    try:
        repo_root = find_repo_root_v3()
        link_store = HubLinkStore(repo_root)

        removed = link_store.remove_link(link_id)

        if removed:
            print_success(f"Removed link: {link_id}", 2)
        else:
            print_warning(f"Link not found: {link_id}", 2)
            print_info("Run 'maestro repo hub link show' to see all links", 2)
            return 1

        return 0
    except Exception as e:
        print_error(f"Failed to remove link: {e}", 2)
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


def handle_hub_command(args):
    """
    Main dispatcher for hub commands.

    Args:
        args: Command arguments with 'hub_subcommand' attribute

    Returns:
        Exit code from the handler
    """
    hub_sub = getattr(args, 'hub_subcommand', None)

    if hub_sub == 'scan':
        return handle_hub_scan(args)
    elif hub_sub == 'list':
        return handle_hub_list(args)
    elif hub_sub == 'show':
        return handle_hub_show(args)
    elif hub_sub == 'find':
        find_sub = getattr(args, 'find_subcommand', None)
        if find_sub == 'package':
            return handle_hub_find_package(args)
        else:
            print_error("Use 'maestro repo hub find package <NAME>'", 2)
            return 1
    elif hub_sub == 'link':
        link_sub = getattr(args, 'link_subcommand', None)
        if link_sub == 'package':
            return handle_hub_link_package(args)
        elif link_sub == 'show':
            return handle_hub_link_show(args)
        elif link_sub == 'remove':
            return handle_hub_link_remove(args)
        else:
            print_error("Unknown link subcommand", 2)
            print_info("Use 'maestro repo hub link --help' for available commands", 2)
            return 1
    else:
        print_error(f"Unknown hub subcommand: {hub_sub}", 2)
        print_info("Use 'maestro repo hub --help' for available commands", 2)
        return 1


# Export handlers
__all__ = [
    'handle_hub_command',
    'handle_hub_scan',
    'handle_hub_list',
    'handle_hub_show',
    'handle_hub_find_package',
    'handle_hub_link_package',
    'handle_hub_link_show',
    'handle_hub_link_remove',
]
