"""
Main dispatcher for repo commands.

Routes repo subcommands to appropriate handlers.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from maestro.modules.utils import (
    print_header,
    print_success,
    print_warning,
    print_error,
    print_info,
    print_debug,
)
from maestro.repo.storage import (
    REPO_TRUTH_REL,
    load_repoconf,
    save_repoconf,
    repo_model_path,
)
from maestro.git_guard import check_branch_guard

from maestro.commands.repo.utils import find_repo_root, write_repo_artifacts, load_repo_index
from maestro.commands.repo.profile_cmd import handle_repo_profile_show, handle_repo_profile_init
from maestro.commands.repo.evidence_cmd import handle_repo_evidence_pack, handle_repo_evidence_list, handle_repo_evidence_show
from maestro.repo.storage import save_repo_model, load_repo_model, repo_model_path, load_repoconf, save_repoconf
from maestro.builders.host import Host, LocalHost
from maestro.builders.upp import UppPackage

from maestro.commands.repo.resolve_cmd import (
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
from maestro.commands.repo.import_roadmap import handle_repo_import_roadmap

def handle_repo_pkg_add(args):
    """
    Handle the 'repo pkg add' command to add a package to the repository model.
    """
    repo_root = getattr(args, 'path', None)
    if not repo_root:
        repo_root = find_repo_root()
    
    if not repo_root:
        print_error("Repository root not found. Please specify --path or run from a Maestro repository.", 2)
        sys.exit(1)

    host = LocalHost() # Instantiate LocalHost
    package_path = os.path.join(repo_root, args.package_path)

    if not os.path.exists(package_path):
        print_error(f"Package path does not exist: {package_path}", 2)
        sys.exit(1)
    if not os.path.isdir(package_path):
        print_error(f"Package path is not a directory: {package_path}", 2)
        sys.exit(1)

    print_info(f"Scanning package: {package_path}")

    try:
        # Create an UppPackage instance to scan the package
        pkg = UppPackage(
            name=os.path.basename(package_path), # Guess name from directory
            dir=os.path.relpath(package_path, repo_root),
            path=package_path
        )
        pkg.scan_package(host, verbose=args.verbose)

        repo_model = load_repo_model(repo_root)
        
        # Check if package already exists and update it, otherwise add it
        found = False
        for i, existing_pkg in enumerate(repo_model.get('packages_detected', [])):
            if existing_pkg.get('name') == pkg.name and existing_pkg.get('dir') == pkg.dir:
                repo_model['packages_detected'][i] = pkg.to_dict()
                found = True
                print_success(f"Updated existing package '{pkg.name}' in repo model.", 2)
                break
        
        if not found:
            repo_model.setdefault('packages_detected', []).append(pkg.to_dict())
            print_success(f"Added new package '{pkg.name}' to repo model.", 2)
        
        save_repo_model(repo_root, repo_model)
        
        # Reload the index to ensure it reflects the new state
        load_repo_index(repo_root, force_reload=True)
        
    except Exception as e:
        print_error(f"Failed to add package: {e}", 2)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    return 0


def handle_repo_command(args):
    """
    Main handler for maestro repo commands.

    Dispatches to appropriate sub-handlers based on repo_subcommand.
    """
    from maestro.repo import scan_upp_repo_v2
    from maestro.repo.assembly_commands import handle_asm_command

    def _find_repo_root_if_truth(path: str) -> Optional[str]:
        current = Path(path).resolve()
        while current != current.parent:
            if (current / REPO_TRUTH_REL).is_dir():
                return str(current)
            current = current.parent
        if (current / REPO_TRUTH_REL).is_dir():
            return str(current)
        return None

    # Handle repository analysis and resolution commands (no session required)
    if hasattr(args, 'repo_subcommand') and args.repo_subcommand:
        if args.repo_subcommand == 'resolve':
            # Get the path to scan - auto-detect or use provided path
            if hasattr(args, 'path') and args.path:
                scan_path = args.path
                # Ensure the path exists
                if not os.path.exists(scan_path):
                    print_error(f"Path does not exist: {scan_path}", 2)
                    sys.exit(1)
                # Ensure the path is a directory
                if not os.path.isdir(scan_path):
                    print_error(f"Path is not a directory: {scan_path}", 2)
                    sys.exit(1)
            else:
                # Use current directory by default, unless --find-root is specified
                if getattr(args, 'find_root', False):
                    scan_path = find_repo_root()
                    if getattr(args, 'verbose', False):
                        print_debug(f"Detected repository root: {scan_path}", 2)
                else:
                    scan_path = os.getcwd()
                    if getattr(args, 'verbose', False):
                        print_debug(f"Scanning current directory: {scan_path}", 2)

            if getattr(args, 'find_root', False):
                repo_root = find_repo_root(scan_path)
            else:
                repo_root = _find_repo_root_if_truth(scan_path) or scan_path
            if not getattr(args, 'json', False):
                branch_guard_error = check_branch_guard(repo_root)
                if branch_guard_error:
                    print_error(branch_guard_error, 2)
                    sys.exit(1)

            # Perform the repo scan
            fast_json = getattr(args, 'json', False)
            repo_result = scan_upp_repo_v2(
                scan_path,
                verbose=getattr(args, 'verbose', False),
                include_user_config=getattr(args, 'include_user_config', False),
                collect_files=not fast_json,
                scan_unknown_paths=not fast_json,
            )

            # Write artifacts unless --no-write is specified
            if not getattr(args, 'no_write', False):
                write_repo_artifacts(repo_root, repo_result, verbose=getattr(args, 'verbose', False))

                # Update hub index with scanned packages (optional)
                if not getattr(args, 'no_hub_update', False):
                    try:
                        from maestro.repo.hub.scanner import HubScanner
                        scanner = HubScanner()
                        repo_record = scanner.scan_repository(repo_root, verbose=getattr(args, 'verbose', False))
                        scanner.update_hub_index(repo_record, verbose=getattr(args, 'verbose', False))
                    except Exception as e:
                        # Hub update is non-critical, don't fail the whole operation
                        print_warning(f"Hub index update failed: {e}", 2)

            # Output format varies based on the flag
            if getattr(args, 'json', False):
                # Output in JSON format
                result = {
                    "assemblies_detected": [
                        {
                            "name": asm.name,
                            "root_path": asm.root_path,
                            "package_folders": getattr(asm, 'package_folders', [])
                        } for asm in repo_result.assemblies_detected
                    ],
                    "packages_detected": [
                        {
                            "name": pkg.name,
                            "dir": pkg.dir,
                            "upp_path": getattr(pkg, 'upp_path', None),
                            "files": pkg.files,
                            "build_system": pkg.build_system
                        } for pkg in repo_result.packages_detected
                    ],
                    "internal_packages": [
                        {
                            "name": ipkg.name,
                            "root_path": ipkg.root_path,
                            "guessed_type": getattr(ipkg, 'guessed_type', None),
                            "members": getattr(ipkg, 'members', [])
                        } for ipkg in repo_result.internal_packages
                    ],
                    "unknown_paths": [
                        {
                            "path": unknown.path,
                            "type": getattr(unknown, 'type', None),
                            "guessed_kind": getattr(unknown, 'guessed_kind', None)
                        } for unknown in repo_result.unknown_paths
                    ]
                }
                print(json.dumps(result, indent=2))
            else:
                # Output in human-readable format
                print_header(f"REPOSITORY SCAN COMPLETE")

                print(f"\nRepository: {scan_path}")
                print(f"Packages: {len(repo_result.packages_detected)}")
                print(f"Assemblies: {len(repo_result.assemblies_detected)}")
                print(f"Internal packages: {len(repo_result.internal_packages)}")
                print(f"Unknown paths: {len(repo_result.unknown_paths)}")

                if not getattr(args, 'no_write', False):
                    model_path = repo_model_path(repo_root, require=False)
                    print(f"\nRepo model written to: {model_path}")

                # Print next steps
                print("\n" + "─" * 60)
                print_info("NEXT STEPS", 2)
                print_info("View detailed results:", 2)
                print_info("  maestro repo show", 3)
                print_info("\nExplore packages:", 2)
                print_info("  maestro repo show --json", 3)
                print_info("\nContinue with build planning or conversion setup", 2)

        elif args.repo_subcommand in ['show', 'sh']:
            # Show repository scan results from docs/maestro/
            repo_root = getattr(args, 'path', None) if hasattr(args, 'path') else None
            index_data = load_repo_index(repo_root)

            if getattr(args, 'json', False):
                # Output in JSON format
                print(json.dumps(index_data, indent=2))
            else:
                # Output in human-readable format
                print_header("REPOSITORY MODEL")
                print(f"\nRepository: {index_data.get('repo_root', repo_root or 'unknown')}")
                print(f"Scan time: {index_data.get('scan_timestamp', 'unknown')}")

                packages = index_data.get('packages_detected', [])
                print(f"\nPackages ({len(packages)}):")
                for pkg in packages[:10]:
                    print(f"  - {pkg.get('name', 'unknown')} ({pkg.get('build_system', 'unknown')})")
                if len(packages) > 10:
                    print(f"  ... and {len(packages) - 10} more")

                assemblies = index_data.get('assemblies', [])
                packages_v2 = index_data.get('packages', [])
                if assemblies:
                    package_counts = {}
                    for pkg in packages_v2:
                        asm_id = pkg.get('assembly_id')
                        if not asm_id:
                            continue
                        package_counts[asm_id] = package_counts.get(asm_id, 0) + 1
                    sorted_assemblies = sorted(assemblies, key=lambda a: a.get('root_relpath', ''))
                    print(f"\nAssemblies ({len(sorted_assemblies)}):")
                    for asm in sorted_assemblies[:10]:
                        asm_name = asm.get('name', 'unknown')
                        asm_id = asm.get('assembly_id')
                        asm_count = package_counts.get(asm_id, 0)
                        print(f"  - {asm_name} ({asm_count} packages)")
                    if len(sorted_assemblies) > 10:
                        print(f"  ... and {len(sorted_assemblies) - 10} more")
                else:
                    assemblies_detected = index_data.get('assemblies_detected', [])
                    if assemblies_detected:
                        print(f"\nAssemblies ({len(assemblies_detected)}):")
                        for asm in assemblies_detected[:10]:
                            asm_name = asm.get('name', 'unknown')
                            pkg_count = len(asm.get('package_folders', []))
                            print(f"  - {asm_name} ({pkg_count} packages)")
                    if len(assemblies_detected) > 10:
                        print(f"  ... and {len(assemblies_detected) - 10} more")

        elif args.repo_subcommand == 'import-roadmap':
            return handle_repo_import_roadmap(args)

        elif args.repo_subcommand == 'pkg':
            # Package inspection and management commands
            pkg_subcommand = getattr(args, 'pkg_subcommand', None)

            if pkg_subcommand == 'add':
                return handle_repo_pkg_add(args)
            
            repo_root = getattr(args, 'path', None) if hasattr(args, 'path') else None
            index_data = load_repo_index(repo_root)
            if not repo_root:
                repo_root = index_data.get("repo_root") or find_repo_root()
            packages = index_data.get('packages_detected', [])

            # Get package name (optional, only for specific subcommands)
            pkg_name = getattr(args, 'package_name', None)

            if pkg_subcommand == 'list':
                handle_repo_pkg_list(packages, getattr(args, 'json', False), repo_root)
            elif pkg_name: # For commands that require a package name
                # Find matching package (exact match including case)
                matching_pkgs = [p for p in packages if pkg_name == p.get('name', '')]

                if not matching_pkgs:
                    print_error(f"No package found matching: {pkg_name}", 2)
                    sys.exit(1)
                elif len(matching_pkgs) > 1:
                    print_warning(f"Multiple packages match '{pkg_name}':", 2)
                    for p in matching_pkgs:
                        print(f"  - {p.get('name')}")
                    print_info("\nPlease be more specific", 2)
                    sys.exit(1)

                pkg = matching_pkgs[0]

                # Dispatch to appropriate handler based on pkg_subcommand
                if pkg_subcommand == 'info':
                    handle_repo_pkg_info(pkg, packages, getattr(args, 'json', False), repo_root)
                elif pkg_subcommand == 'list': # Redundant if handled above, but keep for clarity
                    handle_repo_pkg_files(pkg, getattr(args, 'json', False))
                elif pkg_subcommand == 'groups':
                    handle_repo_pkg_groups(pkg, getattr(args, 'json', False),
                                          getattr(args, 'show_groups', False),
                                          getattr(args, 'group', None))
                elif pkg_subcommand == 'search':
                    query = getattr(args, 'query', None)
                    if not query:
                        print_error("Search query is required for search action", 2)
                        sys.exit(1)
                    handle_repo_pkg_search(pkg, query, getattr(args, 'json', False))
                elif pkg_subcommand == 'tree':
                    config_flags = None
                    # For tree, 'query' argument from old structure is now 'config'
                    if hasattr(args, 'config') and args.config:
                        try:
                            config_num = int(args.config)
                            from maestro.repo.build_config import get_package_config
                            pkg_config = get_package_config(pkg)
                            if pkg_config and 0 <= config_num < len(pkg_config.configurations):
                                config_flags = pkg_config.configurations[config_num].flags
                        except (ValueError, AttributeError):
                            pass
                    handle_repo_pkg_tree(pkg, packages, getattr(args, 'json', False),
                                        getattr(args, 'deep', False), config_flags)
                elif pkg_subcommand == 'conf':
                    handle_repo_pkg_conf(pkg, getattr(args, 'json', False))
            else:
                # If no pkg_name and not 'list', or unknown subcommand
                print_error(f"Unknown package subcommand or missing package name: {pkg_subcommand}", 2)
                sys.exit(1)

        elif args.repo_subcommand == 'conf':
            from maestro.repo.storage import load_repoconf, save_repoconf

            repo_root = getattr(args, 'path', None) if hasattr(args, 'path') else None
            if not repo_root:
                repo_root = find_repo_root()

            conf_sub = getattr(args, 'conf_subcommand', None)
            if conf_sub == 'show':
                repoconf = load_repoconf(repo_root)
                if getattr(args, 'json', False):
                    print(json.dumps(repoconf, indent=2))
                else:
                    print_header("REPO CONFIGURATION")
                    print(json.dumps(repoconf, indent=2))
            elif conf_sub == 'list':
                repoconf = load_repoconf(repo_root)
                targets = repoconf.get("targets", [])
                if repoconf.get("selected_target") and repoconf.get("selected_target") not in targets:
                    targets.append(repoconf["selected_target"])
                if getattr(args, 'json', False):
                    print(json.dumps({
                        "selected_target": repoconf.get("selected_target"),
                        "targets": targets,
                    }, indent=2))
                else:
                    print_header("REPO TARGETS")
                    selected = repoconf.get("selected_target") or "(not set)"
                    print(f"Selected target: {selected}")
                    if targets:
                        for target in targets:
                            selected_marker = " (selected)" if target == repoconf.get("selected_target") else ""
                            print(f"- {target}{selected_marker}")
                    else:
                        print("No targets configured.")
            elif conf_sub == 'select-default':
                branch_guard_error = check_branch_guard(repo_root)
                if branch_guard_error:
                    print_error(branch_guard_error, 2)
                    sys.exit(1)

                if getattr(args, "entity", None) != "target":
                    print_error("Only target selection is supported.", 2)
                    sys.exit(1)
                target = getattr(args, "value", None)
                if not target:
                    print_error("Target value is required.", 2)
                    sys.exit(1)
                repoconf = {
                    "selected_target": target,
                    "targets": [target],
                    "updated_at": datetime.now().isoformat()
                }
                try:
                    existing = load_repoconf(repo_root)
                    targets = existing.get("targets", [])
                    if target not in targets:
                        targets.append(target)
                    repoconf["targets"] = targets
                except SystemExit:
                    pass
                save_repoconf(repo_root, repoconf)
                print_success(f"Selected default target: {target}", 2)
            else:
                print_info("Use 'maestro repo conf --help' for available subcommands.", 2)

        elif args.repo_subcommand == 'asm':
            # Assembly management commands
            handle_asm_command(args)

        elif args.repo_subcommand == 'refresh':
            refresh_sub = getattr(args, 'refresh_subcommand', None)
            if refresh_sub == 'all':
                repo_root = getattr(args, 'path', None)
                if not repo_root:
                    repo_root = find_repo_root()
                handle_repo_refresh_all(repo_root, getattr(args, 'verbose', False))
            elif refresh_sub in ['help', 'h']:
                handle_repo_refresh_help()
            else:
                print_error(f"Unknown refresh subcommand: {refresh_sub}", 2)
                sys.exit(1)

        elif args.repo_subcommand == 'hier':
            hier_sub = getattr(args, 'hier_subcommand', None)
            repo_root = getattr(args, 'path', None)
            if not repo_root:
                repo_root = find_repo_root()

            if hier_sub == 'edit':
                handle_repo_hier_edit(repo_root)
            else:
                # Default to show
                handle_repo_hier(repo_root,
                               getattr(args, 'json', False),
                               getattr(args, 'show_files', False),
                               getattr(args, 'rebuild', False))

        elif args.repo_subcommand == 'conventions':
            conv_sub = getattr(args, 'conventions_subcommand', None)
            repo_root = getattr(args, 'path', None)
            if not repo_root:
                repo_root = find_repo_root()

            if conv_sub == 'detect':
                handle_repo_conventions_detect(repo_root, getattr(args, 'verbose', False))
            else:
                # Default to show
                handle_repo_conventions_show(repo_root)

        elif args.repo_subcommand == 'rules':
            rules_sub = getattr(args, 'rules_subcommand', None)
            repo_root = getattr(args, 'path', None)
            if not repo_root:
                repo_root = find_repo_root()

            if rules_sub == 'edit':
                handle_repo_rules_edit(repo_root)
            elif rules_sub == 'inject':
                context = getattr(args, 'context', 'general')
                handle_repo_rules_inject(repo_root, context)
            else:
                # Default to show
                handle_repo_rules_show(repo_root)

        elif args.repo_subcommand == 'profile':
            profile_sub = getattr(args, 'profile_subcommand', None)
            repo_root = Path(getattr(args, 'path', None) or os.getcwd())

            if profile_sub == 'init':
                handle_repo_profile_init(args, repo_root)
            else:
                # Default to show
                handle_repo_profile_show(args, repo_root)

        elif args.repo_subcommand == 'evidence':
            evidence_sub = getattr(args, 'evidence_subcommand', None)
            repo_root = Path(getattr(args, 'path', None) or os.getcwd())

            if evidence_sub == 'pack':
                handle_repo_evidence_pack(args, repo_root)
            elif evidence_sub == 'list':
                handle_repo_evidence_list(args, repo_root)
            elif evidence_sub == 'show':
                handle_repo_evidence_show(args, repo_root)
            else:
                print_error("Unknown evidence subcommand", 2)
                sys.exit(1)

        elif args.repo_subcommand == 'hub':
            # Hub command for cross-repo package discovery and linking
            from maestro.commands.hub import handle_hub_command
            return handle_hub_command(args)

        elif args.repo_subcommand in ['help', 'h']:
            # Print help for repo subcommands (parser should handle this)
            print_info("Use 'maestro repo --help' to see available commands", 2)
        else:
            print_error(f"Unknown repo subcommand: {args.repo_subcommand}", 2)
            sys.exit(1)
    else:
        # If no subcommand specified, show help
        print_info("Use 'maestro repo --help' to see available commands", 2)
