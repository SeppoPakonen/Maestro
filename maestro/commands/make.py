"""
Make command for Maestro - Universal Build Orchestration
Implements Phase 7 of the UMK Integration Roadmap
"""

__all__ = ["add_make_parser", "handle_make_command"]

import argparse
import sys
import os
import shutil
import subprocess
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from pathlib import Path

from maestro.builders.config import BuildType, OSFamily
from maestro.modules.utils import (
    print_header,
    print_success,
    print_warning,
    print_error,
    print_info,
    print_debug,
)

if TYPE_CHECKING:
    from maestro.builders.config import MethodConfig


def add_make_parser(subparsers: Any) -> argparse.ArgumentParser:
    """Add make command parser."""
    make_parser = subparsers.add_parser(
        'make',
        aliases=['b'],
        help='Build, clean, and manage packages',
        description='Build orchestration commands for managing package builds, cleaning, and configuration.'
    )

    make_subparsers = make_parser.add_subparsers(
        dest='make_subcommand',
        help='Make subcommands'
    )

    # Build subcommand
    build_parser = make_subparsers.add_parser(
        'build',
        aliases=['b'],
        help='Build one or more packages',
        description='Build packages using specified build method and configuration.'
    )
    build_parser.add_argument(
        'package',
        nargs='?',
        help='Package name to build (optional if in package directory or default target set)'
    )
    build_parser.add_argument(
        '-m', '--method',
        help='Build method to use (e.g., clang-debug, gcc-release)'
    )
    build_parser.add_argument(
        '-c', '--config',
        help='Configuration file to use'
    )
    build_parser.add_argument(
        '-j', '--jobs',
        type=int,
        help='Number of parallel jobs to run'
    )
    build_parser.add_argument(
        '--clean-first',
        action='store_true',
        help='Clean build artifacts before building'
    )
    build_parser.add_argument(
        '-a', '--all',
        action='store_true',
        help='Build all packages in the project'
    )
    build_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show verbose output'
    )
    build_parser.add_argument(
        '-t', '--target',
        help='Target directory override for output'
    )

    # Clean subcommand
    clean_parser = make_subparsers.add_parser(
        'clean',
        aliases=['c'],
        help='Clean build artifacts',
        description='Remove build artifacts and temporary files for packages.'
    )
    clean_parser.add_argument(
        'package',
        nargs='?',
        help='Package name to clean (optional, defaults to current package)'
    )
    clean_parser.add_argument(
        '-m', '--method',
        help='Build method to clean for'
    )
    clean_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show verbose output'
    )

    # Rebuild subcommand
    rebuild_parser = make_subparsers.add_parser(
        'rebuild',
        aliases=['r'],
        help='Clean and rebuild packages',
        description='Clean build artifacts and rebuild packages.'
    )
    rebuild_parser.add_argument(
        'package',
        nargs='?',
        help='Package name to rebuild (optional, defaults to current package)'
    )
    rebuild_parser.add_argument(
        '-m', '--method',
        help='Build method to use'
    )
    rebuild_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show verbose output'
    )

    # Analyze subcommand
    analyze_parser = make_subparsers.add_parser(
        'analyze',
        aliases=['an'],
        help='Analyze build dependencies and structure',
        description='Analyze build dependencies, structure, and and potential issues.'
    )
    analyze_parser.add_argument(
        'package',
        nargs='?',
        help='Package name to analyze (optional, defaults to current package)'
    )
    analyze_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show verbose output'
    )

    # Config subcommand
    config_parser = make_subparsers.add_parser(
        'config',
        aliases=['cfg'],
        help='Manage build configuration',
        description='Manage build configuration settings and methods.'
    )
    config_subparsers = config_parser.add_subparsers(
        dest='config_subcommand',
        help='Config subcommands'
    )
    config_detect_parser = config_subparsers.add_parser(
        'detect',
        help='Detect available build methods'
    )
    config_detect_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show verbose output'
    )

    # Methods subcommand
    methods_parser = make_subparsers.add_parser(
        'methods',
        aliases=['m'],
        help='List available build methods',
        description='List all available build methods and their configurations.'
    )
    methods_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show verbose output'
    )

    # Export subcommand
    export_parser = make_subparsers.add_parser(
        'export',
        aliases=['e'],
        help='Export build configuration',
        description='Export build configuration for external tools.'
    )
    export_parser.add_argument(
        'format',
        help='Export format (e.g., cmake, makefile, ninja)'
    )
    export_parser.add_argument(
        '-o', '--output',
        help='Output file path'
    )
    export_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show verbose output'
    )

    # Android subcommand
    android_parser = make_subparsers.add_parser(
        'android',
        aliases=['andr'],
        help='Build for Android platform',
        description='Build packages specifically for Android platform.'
    )
    android_parser.add_argument(
        'package',
        nargs='?',
        help='Package name to build for Android'
    )
    android_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show verbose output'
    )

    # JAR subcommand
    jar_parser = make_subparsers.add_parser(
        'jar',
        aliases=['j'],
        help='Build JAR package',
        description='Build Java Archive (JAR) packages.'
    )
    jar_parser.add_argument(
        'package',
        nargs='?',
        help='Package name to build as JAR'
    )
    jar_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show verbose output'
    )

    # Structure subcommand
    structure_parser = make_subparsers.add_parser(
        'structure',
        aliases=['str'],
        help='Show package build structure',
        description='Show the build structure and dependencies of packages.'
    )
    structure_parser.add_argument(
        'package',
        nargs='?',
        help='Package name to show structure for'
    )
    structure_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show verbose output'
    )

    make_parser.set_defaults(func=handle_make_command)
    return make_parser


def handle_make_command(args: argparse.Namespace) -> None:
    """Handle the make command."""
    cmd = MakeCommand()
    exit_code = cmd.execute(args)
    sys.exit(exit_code)


class MakeCommand:
    """Main make command controller for universal build orchestration."""
    
    def __init__(self):
        from maestro.builders.config import MethodManager

        self.method_manager = MethodManager()
        
    def execute(self, args: argparse.Namespace) -> int:
        """Execute the make command based on subcommand."""
        if args.make_subcommand == 'build':
            return self.build(args)
        elif args.make_subcommand == 'clean':
            return self.clean(args)
        elif args.make_subcommand == 'rebuild':
            return self.rebuild(args)
        elif args.make_subcommand == 'analyze':
            return self.analyze(args)
        elif args.make_subcommand == 'config':
            return self.config(args)
        elif args.make_subcommand == 'methods':
            return self.list_methods(args)
        elif args.make_subcommand == 'export':
            return self.export(args)
        elif args.make_subcommand == 'android':
            return self.build_android(args)
        elif args.make_subcommand == 'jar':
            return self.build_jar(args)
        elif args.make_subcommand == 'structure':
            return self.structure(args)
        else:
            print(f"Error: Unknown make subcommand: {args.make_subcommand}")
            return 1
    
    def clean(self, args: argparse.Namespace) -> int:
        """Clean build artifacts for packages."""
        from maestro.repo.storage import load_repo_model
        repo_root = self._find_repo_root()
        repo_model = load_repo_model(repo_root)
        
        package_name = args.package
        if not package_name:
            package_name = self._detect_current_package(os.getcwd(), repo_model)
            
        if not package_name:
            print("Error: No package to clean specified.")
            return 1
            
        package_names = [package_name]
        
        # Auto-detect method
        method_name = args.method or self.method_manager.detect_default_method()
        if not method_name:
            print("Error: No build method specified and none detected automatically")
            return 1
            
        method_config = self.method_manager.load_method(method_name)
        if not method_config:
            print(f"Error: Could not load build method '{method_name}'")
            return 1

        for name in package_names:
            package_info = self._find_package_info(name, repo_model, repo_root)
            if package_info:
                builder = self._create_builder_for_package(package_info, method_config)
                if builder:
                    from maestro.builders.upp import UppPackage
                    pkg_dir = package_info.get('dir') or os.path.join(repo_root, package_info.get('dir_relpath', ''))
                    package_obj = UppPackage(
                        name=package_info.get('name'),
                        dir=pkg_dir,
                        path=package_info.get('path', '')
                    )
                    builder.clean_package(package_obj)
        return 0

    def rebuild(self, args: argparse.Namespace) -> int:
        """Clean and rebuild packages."""
        args.clean_first = True
        return self.build(args)

    def analyze(self, args: argparse.Namespace) -> int:
        """Analyze build dependencies and structure."""
        print("Analyze command not yet fully implemented.")
        return 0

    def config(self, args: argparse.Namespace) -> int:
        """Manage build configuration."""
        print("Config command not yet fully implemented.")
        return 0

    def list_methods(self, args: argparse.Namespace) -> int:
        """List available build methods."""
        methods = self.method_manager.list_methods()
        print("Available build methods:")
        for method in methods:
            print(f"  - {method}")
        return 0

    def export(self, args: argparse.Namespace) -> int:
        """Export build configuration."""
        print("Export command not yet fully implemented.")
        return 0

    def build_android(self, args: argparse.Namespace) -> int:
        """Build for Android platform."""
        print("Android build not yet fully implemented.")
        return 0

    def build_jar(self, args: argparse.Namespace) -> int:
        """Build JAR package."""
        print("JAR build not yet fully implemented.")
        return 0

    def structure(self, args: argparse.Namespace) -> int:
        """Show package build structure."""
        print("Structure command not yet fully implemented.")
        return 0

    def build(self, args: argparse.Namespace) -> int:
        """Build one or more packages."""
        import time
        overall_start_time = time.time()
        from maestro.builders.console import reset_command_output_log, get_command_output_log
        from maestro.issues.parsers import parse_build_logs
        from maestro.issues.issue_store import write_issue
        from maestro.repo.storage import require_repo_model, load_repo_model, load_repoconf
        from maestro.git_guard import check_branch_guard

        repo_root = self._find_repo_root()
        require_repo_model(repo_root)
        repoconf = load_repoconf(repo_root)
        repo_model = load_repo_model(repo_root)
        branch_guard_error = check_branch_guard(repo_root)
        if branch_guard_error:
            print(f"Error: {branch_guard_error}")
            return 1

        # Load hub links for external package dependencies
        try:
            from maestro.repo.hub.resolver import HubResolver
            resolver = HubResolver(repo_root)
            external_roots = resolver.get_all_linked_package_roots()
            if external_roots and getattr(args, 'verbose', False):
                print(f"Found {len(external_roots)} external package(s) from hub links")
        except Exception as e:
            external_roots = []
            if getattr(args, 'verbose', False):
                print(f"Note: Hub links not available: {e}")

        # Extract assembly roots from selected assembly configuration
        from maestro.repo.assembly_config_commands import load_asm_configs
        asm_configs = load_asm_configs(repo_root)
        selected_asm_name = asm_configs.get("selected")
        
        assembly_roots = []
        if selected_asm_name and selected_asm_name in asm_configs.get("configurations", {}):
            config = asm_configs["configurations"][selected_asm_name]
            roots = config.get("roots", [])
            for root in roots:
                # Resolve paths (they could be relative to repo root or absolute)
                abs_path = os.path.normpath(os.path.join(repo_root, root))
                if os.path.exists(abs_path):
                    if abs_path not in assembly_roots:
                        assembly_roots.append(abs_path)
                elif os.path.exists(root):
                    abs_path = os.path.normpath(root)
                    if abs_path not in assembly_roots:
                        assembly_roots.append(abs_path)
            
            if getattr(args, 'verbose', False):
                print_info(f"Using assembly configuration: {selected_asm_name}", 2)
        else:
            print_error("No assembly configuration selected. Build cannot proceed without an active assembly.", 2)
            print_info("Use 'maestro repo asm conf select <name>' or 'maestro repo asm import <var_file>'", 2)
            return 1
        
        # Add project root as well if not already there
        if repo_root not in assembly_roots:
            assembly_roots.append(repo_root)

        if not assembly_roots:
            print_error("No assembly roots found in the selected configuration.", 2)
            return 1

        # Auto-detect method if not specified
        method_name = args.method
        if not method_name:
            method_name = self.method_manager.detect_default_method()
            if not method_name:
                print("Error: No build method specified and none detected automatically")
                return 1

        # Load the build method
        method_config = self.method_manager.load_method(method_name)
        if not method_config:
            print(f"Error: Could not load build method '{method_name}'")
            return 1

        # Update method config with command-line options
        if hasattr(args, 'jobs') and args.jobs:
            method_config.config.jobs = args.jobs
        if hasattr(args, 'verbose') and args.verbose:
            method_config.config.verbose = True
        
        method_config.config.assembly_roots = assembly_roots

        if external_roots:
            if not hasattr(method_config.config, 'external_package_roots'):
                method_config.config.external_package_roots = []
            method_config.config.external_package_roots.extend(external_roots)
            # Add external roots to assembly_roots for inclusion
            for root in external_roots:
                if root not in method_config.config.assembly_roots:
                    method_config.config.assembly_roots.append(root)

        if args.verbose:
            print(f"Building packages with method: {method_name}")
            print(f"Configuration: {args.config}")
            print(f"Parallel jobs: {args.jobs or method_config.config.jobs}")

        # --- HACK: Manual Dependency Resolution for HelloWorldStd ---

        initial_target_name = None
        if args.package:
            initial_target_name = args.package
        elif repoconf and repoconf.get("selected_target"):
            initial_target_name = repoconf["selected_target"]
            if args.verbose:
                print(f"Using default target from repoconf: {initial_target_name}")
        else:
            current_dir = os.getcwd()
            initial_target_name = self._detect_current_package(current_dir, repo_model)

        if not initial_target_name:
            print("Error: No package to build. Specify a package, set a default, or run from a package directory.")
            return 1

        # Resolve dependencies for the initial target
        try:
            from maestro.commands.repo.utils import build_dependency_hierarchy
            all_packages = repo_model.get("packages_detected", [])
            dep_hierarchy = build_dependency_hierarchy([initial_target_name], all_packages)
            
            # Extract all dependencies in order
            resolved_packages = []
            if initial_target_name in dep_hierarchy['dependencies']:
                dep_data = dep_hierarchy['dependencies'][initial_target_name]
                # Dependencies should be built first
                for dep_info in dep_data['dependencies']:
                    dep_name = dep_info['package']['name']
                    if dep_name not in resolved_packages:
                        resolved_packages.append(dep_name)
            
            # The target itself is built last
            if initial_target_name not in resolved_packages:
                resolved_packages.append(initial_target_name)
                
            package_names = resolved_packages
            if args.verbose:
                print(f"Resolved build order: {package_names}")
        except Exception as e:
            if args.verbose:
                print(f"Warning: Dependency resolution failed: {e}. Building only {initial_target_name}")
            package_names = [initial_target_name]

        # -a/--all means rebuild all (don't skip already built ones)
        if hasattr(args, 'all') and args.all:
            args.clean_first = True
            if args.verbose:
                print("Flag -a (all) specified: will clean and rebuild all files.")

        # Process each package in the resolved order
        total_packages = len(package_names)
        for idx, package_name in enumerate(package_names, 1):
            package_info = self._find_package_info(package_name, repo_model, repo_root, assembly_roots)
            if not package_info:
                print(f"Error: Package '{package_name}' not found in repo model or assembly roots.")
                return 1
            
            # Ensure dir and path are correctly resolved
            if not package_info.get('dir') and 'dir_relpath' in package_info:
                package_info['dir'] = os.path.join(repo_root, package_info['dir_relpath'])
            if not package_info.get('path') and 'package_relpath' in package_info:
                package_info['path'] = os.path.join(repo_root, package_info['package_relpath'])
            
            # Determine flags for display
            display_flags = []
            if package_name == initial_target_name:
                display_flags.append("MAIN")
            
            # Add flags from defines (e.g., flagMSC22X64 -> MSC22X64)
            for d in method_config.compiler.defines:
                if d.startswith("flag"):
                    flag_name = d[4:]
                    if flag_name not in display_flags:
                        display_flags.append(flag_name)
            
            # Add builder/compiler flags if not already there
            if "MSC" not in " ".join(display_flags).upper() and (
                "MSC" in method_config.name.upper() or 
                (method_config.compiler.cxx and "cl.exe" in method_config.compiler.cxx.lower())
            ):
                 if "MSC" not in display_flags:
                     display_flags.append("MSC")
            elif "CLANG" not in " ".join(display_flags).upper() and "CLANG" in method_config.name.upper():
                 display_flags.append("CLANG")
            elif "GCC" not in " ".join(display_flags).upper() and "GCC" in method_config.name.upper():
                 display_flags.append("GCC")
            
            if "DEBUG" not in display_flags and "RELEASE" not in display_flags:
                if method_config.config.build_type == BuildType.DEBUG:
                    display_flags.extend(["DEBUG", "DEBUG_FULL"])
                else:
                    display_flags.append("RELEASE")
            
            if "WIN32" not in display_flags and "POSIX" not in display_flags:
                if method_config.platform.os == OSFamily.WINDOWS:
                    if "WIN32" not in display_flags:
                        display_flags.append("WIN32")
                else:
                    display_flags.extend(["POSIX", "LINUX"])
            
            # Print package header similar to umk format
            flags_str = " ".join(display_flags)
            print(f"----- {package_name} ( {flags_str} ) ({idx} / {total_packages})")

            # Set up the correct output directory structure like umk
            home_dir = os.path.expanduser("~")
            
            # Derive flags_part similar to umk
            flags_components = [method_name]
            if method_config.config.build_type == BuildType.DEBUG:
                flags_components.append("Debug")
                flags_components.append("Debug_Full")
            else:
                flags_components.append("Release")
            
            if package_name == initial_target_name:
                flags_components.append("Main")
                
            flags_components.append("Noblitz")
            flags_part = ".".join(flags_components)
            
            target_base_dir = os.path.join(home_dir, ".cache", "upp.out")
            target_pkg_dir = os.path.join(target_base_dir, package_name)
            target_flags_dir = os.path.normpath(os.path.join(target_pkg_dir, flags_part))

            # Create the target directory structure
            os.makedirs(target_flags_dir, exist_ok=True)

            # Modify the method config to use the correct target directory
            original_target_dir = method_config.config.target_dir
            method_config.config.target_dir = target_flags_dir

            # Perform clean if requested
            if hasattr(args, 'clean_first') and args.clean_first:
                if args.verbose:
                    print(f"Cleaning build artifacts for: {package_name}")
                builder = self._create_builder_for_package(package_info, method_config)
                if builder:
                    from maestro.builders.upp import UppPackage
                    package_obj = UppPackage(
                        name=package_info.get('name'),
                        dir=package_info.get('dir', ''),
                        path=package_info.get('path', '')
                    )
                    builder.clean_package(package_obj)

            package_info = self._find_package_info(package_name, repo_model, repo_root)
            if not package_info:
                print(f"Error: Package '{package_name}' not found in repo model.")
                return 1

            # Parse the .upp file to get the actual source files
            upp_file_path = os.path.join(package_info.get('dir', ''), f"{package_name}.upp")
            if os.path.exists(upp_file_path):
                # Parse the .upp file to get source files
                from maestro.builders.upp import UppBuilder
                from maestro.builders.host import LocalHost
                builder_instance = UppBuilder(LocalHost(), method_config)
                parsed_package = builder_instance.parse_upp_file(upp_file_path)
                # Update the package_info with the parsed files
                package_info['files'] = parsed_package.files

            # If this is the main package, we need to set up for executable build
            original_ldflags = None
            original_cxxflags = None
            original_defines = None
            original_name = None
            
            if package_name == initial_target_name:
                original_ldflags = list(method_config.compiler.ldflags) if hasattr(method_config.compiler, 'ldflags') else []
                original_cxxflags = list(method_config.compiler.cxxflags) if hasattr(method_config.compiler, 'cxxflags') else []
                original_defines = list(method_config.compiler.defines) if hasattr(method_config.compiler, 'defines') else []
                original_name = method_config.name

                # Add flagMAIN and other flags from display_flags as defines
                for f in display_flags:
                    def_flag = f"flag{f}"
                    if def_flag not in method_config.compiler.defines:
                        method_config.compiler.defines.append(def_flag)
                
                # Special handling for MSC if detected
                is_msc = "MSC" in display_flags
                
                if not is_msc:
                    # Original clang/gcc specific flags
                    method_config.compiler.cxxflags.extend([
                        "-ggdb", "-g2", "-fexceptions",
                        "-Wno-logical-op-parentheses"
                    ])

                # Determine the executable output path
                if hasattr(args, 'target') and args.target:
                    output_executable_path = os.path.abspath(args.target)
                else:
                    # Default to placing it in the build directory
                    ext = ".exe" if method_config.platform.os == OSFamily.WINDOWS else ""
                    output_executable_path = os.path.join(target_flags_dir, f"{package_name}{ext}")

                # Determine the object files produced by compilation
                obj_files = []
                obj_ext = ".obj" if is_msc else ".o"
                source_extensions = ['.cpp', '.c', '.cxx', '.cc', '.rc']
                for source_file in package_info.get('files', []):
                    _, ext = os.path.splitext(source_file.lower())
                    if ext in source_extensions:
                        if ext == '.rc' and is_msc:
                            obj_name = os.path.splitext(os.path.basename(source_file))[0] + "$rc.obj"
                        else:
                            obj_name = os.path.splitext(os.path.basename(source_file))[0] + obj_ext
                        obj_files.append(os.path.join(target_flags_dir, obj_name))
                
                if is_msc:
                    # MSC link flags
                    ldflags = [
                        "/nologo", "/machine:x64", f"/out:{output_executable_path}",
                        "/subsystem:console"
                    ]
                    if method_config.config.build_type == BuildType.DEBUG:
                        # Use /debug and generate pdb
                        pdb_path = os.path.splitext(output_executable_path)[0] + ".pdb"
                        ldflags.extend(["/debug", f"/pdb:{pdb_path}", "/incremental:no", "/opt:noref"])
                    else:
                        ldflags.extend(["/incremental:no", "/release", "/opt:ref,icf"])
                    
                    # Add existing ldflags (e.g., /LIBPATH from .bm file)
                    ldflags.extend(original_ldflags)
                    
                    # Add object files
                    ldflags.extend(obj_files)
                else:
                    # Original clang/gcc link flags
                    ldflags = [
                        "-static", "-o", output_executable_path, "-ggdb",
                        "-L/usr/lib64", "-L/usr/lib", "-L/usr/lib/llvm/19/lib", "-L/usr/lib/llvm/19/lib64",
                    ]
                    ldflags.extend(original_ldflags)
                    ldflags.extend(obj_files)
                    ldflags.extend(["-Wl,--start-group", "-Wl,--end-group"])

                # Add dependency libraries
                dep_flags_part = flags_part.replace(".Main.", ".")
                for dep_name in package_names:
                    if dep_name == package_name:
                        continue
                        
                    lib_ext = ".lib" if is_msc else ".a"
                    dep_lib_path = os.path.normpath(os.path.join(home_dir, ".cache", "upp.out", dep_name, dep_flags_part, f"{dep_name}{lib_ext}"))
                    
                    if os.path.exists(dep_lib_path):
                        if is_msc:
                            if dep_lib_path not in ldflags:
                                ldflags.append(dep_lib_path)
                        else:
                            if dep_lib_path not in ldflags:
                                # Insert the dependency library between start-group and end-group
                                ldflags.insert(-1, dep_lib_path)

                method_config.compiler.ldflags = ldflags
                method_config.name = f"{method_name}-exe"

            builder = self._create_builder_for_package(package_info, method_config)
            if not builder:
                print(f"Error: Could not create builder for package '{package_name}'")
                return 1

            reset_command_output_log()
            success = builder.build_package(package_info, method_config, verbose=args.verbose)

            # Restore original config if modified
            if package_name == initial_target_name:
                if original_ldflags is not None:
                    method_config.compiler.ldflags = original_ldflags
                if original_cxxflags is not None:
                    method_config.compiler.cxxflags = original_cxxflags
                if original_defines is not None:
                    method_config.compiler.defines = original_defines
                if original_name is not None:
                    method_config.name = original_name
            # Restore original target directory
            method_config.config.target_dir = original_target_dir

            if not success:
                print(f"Failed to build package: {package_name}")
                return 1

        overall_elapsed = time.time() - overall_start_time
        m, s = divmod(overall_elapsed, 60)
        print(f"\nOK. ({int(m)}:{s:05.2f})")
        return 0

    def _find_package_info(self, package_name: str, repo_model: Dict, repo_root: str, assembly_roots: List[str] = None) -> Optional[Dict]:
        """Find package information, prioritizing assembly roots."""
        # 1. Search in the assembly roots first (Manual lookup)
        if assembly_roots:
            for root in assembly_roots:
                pkg_dir = os.path.normpath(os.path.join(root, package_name))
                upp_file = os.path.join(pkg_dir, f"{package_name}.upp")
                if os.path.exists(upp_file):
                    return {
                        'name': package_name,
                        'dir': pkg_dir,
                        'path': upp_file
                    }

        # 2. Fallback to repo model (with assembly root filtering)
        if 'packages' in repo_model:
            matching_pkgs = []
            for pkg in repo_model['packages']:
                if pkg.get('name') == package_name:
                    # Resolve absolute path for checking against assembly roots
                    pkg_path = pkg.get('dir')
                    if not pkg_path and 'dir_relpath' in pkg:
                        pkg_path = os.path.join(repo_root, pkg['dir_relpath'])
                    
                    if not pkg_path:
                        matching_pkgs.append(pkg)
                        continue
                        
                    pkg_path = os.path.normpath(pkg_path)
                    
                    # If we have assembly roots, check if this package is inside one of them
                    if assembly_roots:
                        is_in_asm = False
                        for root in assembly_roots:
                            try:
                                rel = os.path.relpath(pkg_path, root)
                                if not rel.startswith('..'):
                                    is_in_asm = True
                                    break
                            except ValueError:
                                continue
                        if is_in_asm:
                            # Found a match in assembly roots - return immediately
                            if 'dir_relpath' in pkg and not pkg.get('dir'):
                                pkg['dir'] = os.path.join(repo_root, pkg['dir_relpath'])
                            if 'package_relpath' in pkg and not pkg.get('path'):
                                pkg['path'] = os.path.join(repo_root, pkg['package_relpath'])
                            return pkg
                    
                    matching_pkgs.append(pkg)
            
            # If no match in assembly roots but we found some matches in model, return the first one
            if matching_pkgs:
                pkg = matching_pkgs[0]
                if 'dir_relpath' in pkg and not pkg.get('dir'):
                    pkg['dir'] = os.path.join(repo_root, pkg['dir_relpath'])
                if 'package_relpath' in pkg and not pkg.get('path'):
                    pkg['path'] = os.path.join(repo_root, pkg['package_relpath'])
                return pkg
        
        # 3. Last resort: guessed paths
        possible_dirs = [
            os.path.join(repo_root, "uppsrc", package_name),
            os.path.join(repo_root, "upptst", package_name),
            os.path.join(repo_root, package_name),
        ]
        
        for pkg_dir in possible_dirs:
            if os.path.exists(pkg_dir):
                return {
                    'name': package_name,
                    'dir': pkg_dir,
                    'path': os.path.join(pkg_dir, f"{package_name}.upp")
                }

        return None

    def _create_builder_for_package(self, package_info: Dict, method_config: 'MethodConfig'):
        """Create appropriate builder for the package."""
        from maestro.builders.upp import UppBuilder
        from maestro.builders.host import LocalHost

        # Create host instance
        host = LocalHost()

        # Create the appropriate builder based on method_config
        msc_names = ["msc-debug", "msc-release", "msvc-debug", "msvc-release"]
        if (method_config.builder == "upp" or 
            method_config.name in ["clang-debug", "gcc-debug", "clang-release", "gcc-release"] or
            method_config.name in msc_names or
            "msvc" in method_config.name.lower() or
            "msc" in method_config.name.lower()):
            return UppBuilder(host, method_config)
        else:
            # Default to UppBuilder for now for U++ repos
            return UppBuilder(host, method_config)

    def _detect_current_package(self, current_dir: str, repo_model: Dict) -> Optional[str]:
        """Detect the current package based on the current directory."""
        # Check if we're in a package directory by looking for .upp file
        current_package_name = os.path.basename(current_dir)
        upp_file = os.path.join(current_dir, f"{current_package_name}.upp")

        if os.path.exists(upp_file):
            return current_package_name

        return None

    def _get_all_packages(self, repo_model: Dict) -> List[str]:
        """Get all packages from the repo model."""
        # This is a simplified implementation - in a real system, this would extract
        # all packages from the repo model
        if 'packages' in repo_model:
            return [pkg.get('name') for pkg in repo_model['packages'] if pkg.get('name')]

        # If no packages in repo model, try to discover them from the file system
        # This is a fallback for the HelloWorldStd case
        return ['HelloWorld2', 'HelloWorldStd']  # Common U++ test packages

    def _find_repo_root(self) -> Optional[str]:
        """Find the repository root by looking for common U++ project markers."""
        current_dir = os.getcwd()
        original_dir = current_dir

        # Search upward for U++ project markers
        while current_dir != os.path.dirname(current_dir):  # Until we reach root
            # Check for common U++ project indicators
            if (os.path.exists(os.path.join(current_dir, "uppsrc")) or
                os.path.exists(os.path.join(current_dir, ".git")) or
                os.path.exists(os.path.join(current_dir, "uppsrc.tgz")) or
                os.path.exists(os.path.join(current_dir, "README.md")) and
                "upp" in open(os.path.join(current_dir, "README.md"), "r", encoding="utf-8", errors="ignore").read().lower()):
                return current_dir
            current_dir = os.path.dirname(current_dir)

        # If not found by searching up, try common U++ locations
        possible_roots = [
            os.path.expanduser("~/ai-upp"),
            os.path.expanduser("~/upp"),
            os.path.expanduser("~/.upp"),
        ]

        for root in possible_roots:
            if os.path.exists(root):
                return root

        # Default to current directory if nothing else found
        return original_dir
