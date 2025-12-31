import hashlib
import json
import os
from typing import Any, Dict, List, Tuple

from maestro.modules.utils import print_error
from maestro.repo.storage import find_repo_root, load_repo_model


def handle_asm_command(args):
    """
    Handle 'maestro repo asm' commands.

    Subcommands:
    - list: List all assemblies
    - show: Show details for specific assembly
    - help: Show help
    """
    repo_path = args.path if hasattr(args, 'path') and args.path else None

    if args.asm_subcommand in ['list', 'ls', 'l', None]:
        list_assemblies(repo_path, getattr(args, 'json', False))
    elif args.asm_subcommand in ['show', 's', 'sh']:
        assembly_ref = getattr(args, 'assembly_ref', None)
        if assembly_ref:
            show_assembly(repo_path, assembly_ref, getattr(args, 'json', False))
        else:
            print_error("Assembly ID or name required for 'show' command", 2)
            show_asm_help()
    elif args.asm_subcommand in ['help', 'h']:
        show_asm_help()
    else:
        print_error(f"Unknown assembly command: {args.asm_subcommand}", 2)
        show_asm_help()


def _stable_id(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _resolve_repo_root(repo_root: str | None) -> str:
    if repo_root:
        return repo_root
    return find_repo_root()


def _derive_assemblies_and_packages(index_data: Dict[str, Any], repo_root: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    assemblies = index_data.get("assemblies")
    packages = index_data.get("packages")
    if isinstance(assemblies, list) and isinstance(packages, list):
        return assemblies, packages

    assemblies_detected = index_data.get("assemblies_detected", [])
    packages_detected = index_data.get("packages_detected", [])

    derived_assemblies: List[Dict[str, Any]] = []
    assemblies_by_root: Dict[str, Dict[str, Any]] = {}
    for asm in assemblies_detected:
        root_path = asm.get("root_path", "")
        if not root_path:
            continue
        # Normalize the root path to match how package directories will be stored
        norm_root_path = os.path.normpath(root_path)
        root_relpath = os.path.relpath(norm_root_path, repo_root)
        assembly_id = _stable_id(f"assembly:{root_relpath}")
        entry = {
            "assembly_id": assembly_id,
            "name": asm.get("name", os.path.basename(root_path)),
            "root_relpath": root_relpath,
            "kind": asm.get("assembly_type", "upp"),
            "package_ids": [],
        }
        derived_assemblies.append(entry)
        assemblies_by_root[norm_root_path] = entry

    packages_by_assembly: Dict[str, List[Dict[str, Any]]] = {a["assembly_id"]: [] for a in derived_assemblies}
    derived_packages: List[Dict[str, Any]] = []

    for pkg in packages_detected:
        pkg_dir = pkg.get("dir")
        if not pkg_dir:
            continue
        pkg_dir_norm = os.path.normpath(pkg_dir)
        parent_dir = os.path.normpath(os.path.dirname(pkg_dir))

        # Look for assembly that contains this package
        assembly_found = None

        # First check if there's an exact match for the package directory
        if pkg_dir_norm in assemblies_by_root:
            assembly_found = assemblies_by_root[pkg_dir_norm]
        # If not found, check parent directory (for subdirectory packages)
        elif parent_dir in assemblies_by_root:
            assembly_found = assemblies_by_root[parent_dir]
        # If still not found, check if this is a root package that should go into root assembly
        else:
            # Look for root assembly that should contain this package
            for asm_path, asm_entry in assemblies_by_root.items():
                asm_name = asm_entry.get("name", "")
                repo_basename = os.path.basename(repo_root)
                # Check if this is a root assembly that should contain packages from the repo root
                if asm_name == repo_basename and asm_entry.get("kind") == "root":
                    # Check if the package directory is within the assembly path
                    try:
                        # If the assembly path is the same as the package directory (root package case)
                        if asm_path == pkg_dir_norm:
                            assembly_found = asm_entry
                            break
                        # Or if the package is under the assembly directory
                        rel_path = os.path.relpath(pkg_dir_norm, asm_path)
                        if not rel_path.startswith('../') and rel_path != os.path.pardir:
                            assembly_found = asm_entry
                            break
                    except ValueError:
                        # If paths are on different drives (Windows), skip
                        continue

        assembly_id = assembly_found["assembly_id"] if assembly_found else None
        package_relpath = os.path.relpath(pkg_dir, parent_dir) if assembly_found else os.path.relpath(pkg_dir, repo_root)
        package_id = _stable_id(f"package:{assembly_id}:{package_relpath}")
        entry = {
            "package_id": package_id,
            "name": pkg.get("name", ""),
            "dir_relpath": os.path.relpath(pkg_dir, repo_root),
            "package_relpath": package_relpath,
            "assembly_id": assembly_id,
            "build_system": pkg.get("build_system", "upp"),
        }
        if assembly_found and assembly_id:
            packages_by_assembly[assembly_id].append(entry)
        derived_packages.append(entry)

    for asm in derived_assemblies:
        entries = sorted(packages_by_assembly[asm["assembly_id"]], key=lambda p: p["package_relpath"])
        asm["package_ids"] = [pkg["package_id"] for pkg in entries]

    derived_assemblies = sorted(derived_assemblies, key=lambda a: a["root_relpath"])
    derived_packages = sorted(derived_packages, key=lambda p: p["dir_relpath"])
    return derived_assemblies, derived_packages


def load_assemblies_data(repo_root: str | None) -> Dict[str, Any]:
    """Load assemblies data from docs/maestro/repo_model.json."""
    resolved_root = _resolve_repo_root(repo_root)
    index_data = load_repo_model(resolved_root)
    assemblies, packages = _derive_assemblies_and_packages(index_data, resolved_root)
    return {
        "repo_root": index_data.get("repo_root", resolved_root),
        "assemblies": assemblies,
        "packages": packages,
    }


def list_assemblies(repo_root: str | None, json_output: bool = False):
    """List all detected assemblies."""
    assemblies_data = load_assemblies_data(repo_root)
    assemblies = assemblies_data.get('assemblies', [])
    packages = assemblies_data.get('packages', [])

    if json_output:
        payload = {
            "assemblies": [
                {
                    "assembly_id": asm.get("assembly_id"),
                    "name": asm.get("name"),
                    "root_relpath": asm.get("root_relpath"),
                    "kind": asm.get("kind", "upp"),
                    "package_count": len(asm.get("package_ids", [])),
                } for asm in assemblies
            ]
        }
        print(json.dumps(payload, indent=2))
        return

    if not assemblies:
        print("No assemblies found in repository.")
        return

    print("Assemblies in repository:\n")
    package_counts = {}
    for pkg in packages:
        asm_id = pkg.get("assembly_id")
        if asm_id:
            package_counts[asm_id] = package_counts.get(asm_id, 0) + 1

    for i, asm in enumerate(assemblies, 1):
        asm_name = asm.get("name", "unknown")
        asm_kind = asm.get("kind", "upp")
        asm_id = asm.get("assembly_id")
        asm_root = asm.get("root_relpath", "")
        asm_count = package_counts.get(asm_id, 0)
        print(f"  {i}. {asm_name} ({asm_kind})")
        print(f"     ID: {asm_id}")
        print(f"     Root: {asm_root}")
        print(f"     Packages: {asm_count}")
        print()


def show_assembly(repo_root: str | None, assembly_ref: str, json_output: bool = False):
    """Show detailed information about a specific assembly."""
    assemblies_data = load_assemblies_data(repo_root)
    assemblies = assemblies_data.get('assemblies', [])
    packages = assemblies_data.get('packages', [])

    target_assembly = None
    for asm in assemblies:
        if asm.get("assembly_id") == assembly_ref:
            target_assembly = asm
            break
    if not target_assembly:
        matches = [asm for asm in assemblies if asm.get("name") == assembly_ref]
        if len(matches) == 1:
            target_assembly = matches[0]
        elif len(matches) > 1:
            print_error(f"Multiple assemblies named '{assembly_ref}', use assembly_id.", 2)
            return

    if not target_assembly:
        print_error(f"Assembly '{assembly_ref}' not found in repository.", 2)
        return

    asm_id = target_assembly.get("assembly_id")
    asm_packages = [
        pkg for pkg in packages
        if pkg.get("assembly_id") == asm_id
    ]
    asm_packages = sorted(asm_packages, key=lambda p: p.get("package_relpath", ""))

    if json_output:
        payload = dict(target_assembly)
        payload["packages"] = asm_packages
        payload["package_count"] = len(asm_packages)
        print(json.dumps(payload, indent=2))
        return

    print(f"Assembly: {target_assembly.get('name', 'unknown')}\n")
    print(f"  ID: {asm_id}")
    print(f"  Kind: {target_assembly.get('kind', 'upp')}")
    print(f"  Root: {target_assembly.get('root_relpath', '')}")
    print(f"\n  Packages ({len(asm_packages)}):")
    for pkg in asm_packages:
        pkg_name = pkg.get("name", "unknown")
        pkg_rel = pkg.get("package_relpath", "")
        print(f"    - {pkg_name} ({pkg_rel})")


def show_asm_help():
    """Show help for assembly commands."""
    help_text = """
Maestro Assembly Commands (maestro repo asm)

Usage:
  maestro repo asm list              # List all assemblies in repository
  maestro repo asm show <id|name>    # Show details for specific assembly
  maestro repo asm help              # Show this help message

Options:
  --path <path>                      # Path to repository root (default: auto-detect)
  --json                             # Output results in JSON format

Examples:
  maestro repo asm list              # List all assemblies
  maestro repo asm show uppsrc       # Show details for specific assembly
  maestro repo asm show myproject --json  # Show assembly in JSON format
"""
    print(help_text.strip())
