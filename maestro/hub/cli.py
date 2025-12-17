"""
Hub CLI implementation for MaestroHub - Command-line interface
for hub management operations.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import List

from .client import MaestroHub
from .resolver import HubResolver


def create_hub_parser():
    """Create the argument parser for hub commands."""
    parser = argparse.ArgumentParser(
        prog="maestro hub",
        description="Manage package hubs and dependencies"
    )
    
    subparsers = parser.add_subparsers(dest="hub_command", help="Hub commands")
    
    # hub list
    list_parser = subparsers.add_parser("list", help="List all registered hubs and nests")
    list_parser.add_argument("--format", choices=["table", "json"], default="table", 
                            help="Output format (default: table)")
    
    # hub search
    search_parser = subparsers.add_parser("search", help="Search for package in registered hubs")
    search_parser.add_argument("package", help="Package name to search for")
    
    # hub install
    install_parser = subparsers.add_parser("install", help="Install repository nest from hub")
    install_parser.add_argument("nest", help="Nest name to install")
    install_parser.add_argument("--update", "-u", action="store_true", 
                               help="Update if nest already exists")
    
    # hub update
    update_parser = subparsers.add_parser("update", help="Update repository nest to latest version")
    update_parser.add_argument("nest", help="Nest name to update")
    
    # hub add
    add_parser = subparsers.add_parser("add", help="Add custom hub registry")
    add_parser.add_argument("url", help="URL to hub registry JSON file")
    
    # hub sync
    sync_parser = subparsers.add_parser("sync", help="Sync all hub metadata")
    
    # hub info
    info_parser = subparsers.add_parser("info", help="Show detailed information about nest")
    info_parser.add_argument("nest", help="Nest name to show info for")
    
    return parser


def cmd_hub_list(hub: MaestroHub, args: argparse.Namespace):
    """Handle the 'hub list' command."""
    registries = hub.list_registries()
    
    if args.format == "json":
        output = {
            "registries": {}
        }
        for name, registry in registries.items():
            reg_data = {
                "name": registry.name,
                "description": registry.description,
                "nests": [],
                "links": registry.links
            }
            for nest in registry.nests:
                nest_data = {
                    "name": nest.name,
                    "description": nest.description,
                    "repository": nest.repository,
                    "branch": nest.branch,
                    "packages": nest.packages,
                    "category": nest.category,
                    "status": nest.status,
                    "website": nest.website,
                    "build_system": nest.build_system
                }
                reg_data["nests"].append(nest_data)
            output["registries"][name] = reg_data
        
        print(json.dumps(output, indent=2))
        return
    
    # Table format
    print("=" * 80)
    print(f"{'REGISTERED HUBS':^80}")
    print("=" * 80)
    
    if not registries:
        print("No hubs registered. Add a hub with 'maestro hub add <URL>'.")
        return
    
    for reg_name, registry in registries.items():
        print(f"\nHub: {reg_name}")
        print(f"Description: {registry.description}")
        print(f"Nests: {len(registry.nests)}")
        
        if registry.links:
            print(f"Links: {', '.join(registry.links)}")
        
        if registry.nests:
            print("\n  NESTS:")
            print(f"  {'Name':<20} {'Description':<30} {'Build System':<15}")
            print(f"  {'-'*20} {'-'*30} {'-'*15}")
            
            for nest in registry.nests:
                desc = nest.description[:27] + "..." if len(nest.description) > 30 else nest.description
                print(f"  {nest.name:<20} {desc:<30} {nest.build_system:<15}")
        
        print()


def cmd_hub_search(hub: MaestroHub, args: argparse.Namespace):
    """Handle the 'hub search' command."""
    results = hub.search_package(args.package)
    
    if not results:
        print(f"No packages found matching '{args.package}'")
        return
    
    print(f"Search results for '{args.package}':")
    print("-" * 60)
    
    for registry, nest in results:
        print(f"Registry: {registry.name}")
        print(f"Nest: {nest.name}")
        print(f"Description: {nest.description}")
        print(f"Repository: {nest.repository}")
        print(f"Build System: {nest.build_system}")
        print(f"Status: {nest.status}")
        print("-" * 60)


def cmd_hub_install(hub: MaestroHub, args: argparse.Namespace):
    """Handle the 'hub install' command."""
    success = hub.install_nest(args.nest, update=args.update)
    
    if success:
        print(f"Successfully {'updated' if args.update else 'installed'} nest '{args.nest}'")
    else:
        print(f"Failed to {'update' if args.update else 'install'} nest '{args.nest}'")
        sys.exit(1)


def cmd_hub_update(hub: MaestroHub, args: argparse.Namespace):
    """Handle the 'hub update' command."""
    success = hub.install_nest(args.nest, update=True)
    
    if success:
        print(f"Successfully updated nest '{args.nest}'")
    else:
        print(f"Failed to update nest '{args.nest}'")
        sys.exit(1)


def cmd_hub_add(hub: MaestroHub, args: argparse.Namespace):
    """Handle the 'hub add' command."""
    registry = hub.load_hub(args.url)
    
    if registry:
        print(f"Successfully added hub '{registry.name}': {registry.description}")
        print(f"Found {len(registry.nests)} nests in this hub")
    else:
        print(f"Failed to add hub from '{args.url}'")
        sys.exit(1)


def cmd_hub_sync(hub: MaestroHub, args: argparse.Namespace):
    """Handle the 'hub sync' command."""
    print("Syncing hub metadata...")
    
    # For now, just reload the cache to refresh
    hub._load_cache()
    
    registries = hub.list_registries()
    total_nests = sum(len(reg.nests) for reg in registries.values())
    
    print(f"Sync completed. Loaded {len(registries)} registries with {total_nests} nests.")


def cmd_hub_info(hub: MaestroHub, args: argparse.Namespace):
    """Handle the 'hub info' command."""
    # Search for the nest across all registries
    target_nest = None
    target_registry = None
    
    for registry in hub.list_registries().values():
        for nest in registry.nests:
            if nest.name.lower() == args.nest.lower():
                target_nest = nest
                target_registry = registry
                break
        if target_nest:
            break
    
    if not target_nest:
        print(f"Nest '{args.nest}' not found in any registered hub.")
        sys.exit(1)
    
    print("=" * 80)
    print(f"{'NEST INFORMATION':^80}")
    print("=" * 80)
    
    print(f"Name: {target_nest.name}")
    print(f"Description: {target_nest.description}")
    print(f"Registry: {target_registry.name}")
    print(f"Repository: {target_nest.repository}")
    print(f"Branch: {target_nest.branch}")
    print(f"Category: {target_nest.category}")
    print(f"Status: {target_nest.status}")
    print(f"Build System: {target_nest.build_system}")
    print(f"Website: {target_nest.website}")
    
    if target_nest.packages:
        print(f"Packages ({len(target_nest.packages)}):")
        for i, pkg in enumerate(target_nest.packages[:10]):  # Show first 10 packages
            print(f"  - {pkg}")
        if len(target_nest.packages) > 10:
            print(f"  ... and {len(target_nest.packages) - 10} more")
    
    print("\n" + "=" * 80)


def main_hub_command(args: argparse.Namespace = None):
    """Main entry point for hub commands."""
    if args is None:
        parser = create_hub_parser()
        args = parser.parse_args()
    
    # Initialize hub system
    hub = MaestroHub()
    resolver = HubResolver(hub)
    
    # Route to appropriate command handler
    command_map = {
        "list": cmd_hub_list,
        "search": cmd_hub_search,
        "install": cmd_hub_install,
        "update": cmd_hub_update,
        "add": cmd_hub_add,
        "sync": cmd_hub_sync,
        "info": cmd_hub_info,
    }
    
    if args.hub_command is None:
        # If no subcommand provided, show help
        parser.print_help()
        sys.exit(1)
    
    if args.hub_command in command_map:
        command_map[args.hub_command](hub, args)
    else:
        print(f"Unknown command: {args.hub_command}")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main_hub_command()