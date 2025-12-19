"""
Make command for Maestro - Universal Build Orchestration
Implements Phase 7 of the UMK Integration Roadmap
"""
import argparse
import sys
import os
import shutil
import subprocess
from typing import List, Optional, Dict, Any
from pathlib import Path

# Import builders and configuration system from maestro
from maestro.builders.config import MethodManager, MethodConfig
from maestro.builders import (
    UppBuilder, GccBuilder, MsvcBuilder, CMakeBuilder,
    AutotoolsBuilder, MsBuildBuilder, MavenBuilder, AndroidBuilder, JavaBuilder
)


class MakeCommand:
    """Main make command controller for universal build orchestration."""
    
    def __init__(self):
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
        else:
            print(f"Error: Unknown make subcommand: {args.make_subcommand}")
            return 1
    
    def build(self, args: argparse.Namespace) -> int:
        """Build one or more packages."""
        from maestro.builders.console import reset_command_output_log, get_command_output_log
        from maestro.issues.parsers import parse_build_logs
        from maestro.issues.issue_store import write_issue

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

        if args.verbose:
            print(f"Building packages with method: {method_name}")
            print(f"Configuration: {args.config}")
            print(f"Parallel jobs: {args.jobs or method_config.config.jobs}")

        # Determine package to build
        package_names = []
        if args.package:
            package_names.append(args.package)
        else:
            # Try to detect current package
            current_dir = os.getcwd()
            package_name = self._detect_current_package(current_dir)
            if not package_name:
                print("Error: No package specified and none detected in current directory")
                return 1
            package_names.append(package_name)

        # Process each package
        for package_name in package_names:
            # Find package info
            package_info = self._find_package_info(package_name)
            if not package_info:
                print(f"Error: Package '{package_name}' not found in repo")
                return 1
            if getattr(args, "group", None):
                group_info = self._apply_group_filter(package_info, args.group)
                if not group_info:
                    print(f"Error: Group '{args.group}' not found for package '{package_name}'")
                    return 1
                package_info = group_info

            # Apply config-specific options for U++ packages
            if args.config and package_info.get('build_system') == 'upp':
                # For U++ packages, we might want to apply specific config options
                if args.verbose:
                    print(f"Using config '{args.config}' for U++ package '{package_name}'")

            # Create appropriate builder based on package type
            builder = self._create_builder_for_package(package_info, method_config)
            if not builder:
                print(f"Error: Could not create builder for package '{package_name}'")
                return 1

            if args.verbose:
                print(f"Building package: {package_name}")
                print(f"Using builder: {type(builder).__name__}")
                print(f"Build system: {package_info.get('build_system', 'unknown')}")

            # Clean first if requested
            if hasattr(args, 'clean_first') and args.clean_first:
                if args.verbose:
                    print(f"Cleaning package: {package_name}")
                builder.clean_package(package_info)

            reset_command_output_log()

            # Build the package
            success = builder.build_package(package_info, method_config)
            if success:
                if args.verbose:
                    print(f"Successfully built package: {package_name}")
                else:
                    print(f"Built: {package_name}")
            else:
                print(f"Failed to build package: {package_name}")
                log_entries = get_command_output_log()
                parsed_issues = parse_build_logs(log_entries)
                if parsed_issues:
                    repo_root = self._find_repo_root() or os.getcwd()
                    issue_ids = []
                    print("Build errors detected:")
                    for issue in parsed_issues:
                        issue_ids.append(write_issue(issue.to_issue_details("make"), repo_root))
                        location = f"{issue.file}:{issue.line}:{issue.column}".rstrip(":0")
                        print(f"- {location or 'N/A'}: {issue.description}")
                    self._prompt_issue_fix(repo_root, issue_ids)
                return 1

        return 0
    
    def clean(self, args: argparse.Namespace) -> int:
        """Clean build artifacts for package(s)."""
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

        # Determine package to clean
        package_names = []
        if args.package:
            package_names.append(args.package)
        else:
            # Try to detect current package
            current_dir = os.getcwd()
            package_name = self._detect_current_package(current_dir)
            if not package_name:
                print("Error: No package specified and none detected in current directory")
                return 1
            package_names.append(package_name)

        # Process each package
        for package_name in package_names:
            # Find package info
            package_info = self._find_package_info(package_name)
            if not package_info:
                print(f"Error: Package '{package_name}' not found in repo")
                return 1

            # Create appropriate builder
            builder = self._create_builder_for_package(package_info, method_config)
            if not builder:
                print(f"Error: Could not create builder for package '{package_name}'")
                return 1

            if args.verbose:
                print(f"Cleaning package: {package_name}")
            builder.clean_package(package_info)
            if args.verbose:
                print(f"Successfully cleaned package: {package_name}")
            else:
                print(f"Cleaned: {package_name}")
        return 0
    
    def rebuild(self, args: argparse.Namespace) -> int:
        """Clean and build package(s)."""
        if args.verbose:
            print("Rebuilding package(s)...")

        # Temporarily disable verbose for clean step to avoid duplication
        original_verbose = getattr(args, 'verbose', False)
        args.verbose = args.verbose  # Keep original value

        clean_result = self.clean(args)
        if clean_result != 0:
            print("Clean step failed, aborting rebuild")
            return clean_result

        # Temporarily store clean-first flag so build doesn't clean again
        original_clean_first = getattr(args, 'clean_first', False)
        args.clean_first = False  # Already cleaned

        # Call build directly with current package name but clean_first disabled
        build_result = self.build(args)

        # Restore original flag
        args.clean_first = original_clean_first
        return build_result

    def analyze(self, args: argparse.Namespace) -> int:
        """Run static analyzers and create issues from findings."""
        from maestro.issues.parsers import parse_analyzer_output
        from maestro.issues.issue_store import write_issue

        repo_root = self._find_repo_root() or os.getcwd()
        target_path = args.path or repo_root
        tools = self._resolve_analyzers(args.tools)
        if not tools:
            print("No analyzers available (install clang-tidy, cppcheck, pylint, or checkstyle).")
            return 1

        all_issues = []
        for tool in tools:
            exit_code, output = self._run_analyzer(tool, target_path, args, repo_root)
            if output:
                issues = parse_analyzer_output(tool, output)
                all_issues.extend(issues)
            if exit_code not in (0, 1):
                print(f"Warning: {tool} exited with status {exit_code}")

        if not all_issues:
            print("No analyzer issues found.")
            return 0

        issue_ids = []
        print("Analyzer findings detected:")
        for issue in all_issues:
            issue_ids.append(write_issue(issue.to_issue_details("make-analyze"), repo_root))
            location = f"{issue.file}:{issue.line}:{issue.column}".rstrip(":0")
            print(f"- {location or 'N/A'}: {issue.description}")

        print(f"Created {len(issue_ids)} issue file(s).")
        return 0
    
    def config(self, args: argparse.Namespace) -> int:
        """Configure build methods and options."""
        if not hasattr(args, 'config_subcommand') or not args.config_subcommand:
            print("Error: config subcommand required (list, show, edit, detect)")
            return 1
            
        if args.config_subcommand == 'list':
            return self.list_methods(args)
        elif args.config_subcommand == 'show':
            return self.show_method(args)
        elif args.config_subcommand == 'edit':
            return self.edit_method(args)
        elif args.config_subcommand == 'detect':
            return self.detect_methods(args)
        else:
            print(f"Error: Unknown config subcommand: {args.config_subcommand}")
            return 1
    
    def show_method(self, args: argparse.Namespace) -> int:
        """Show method configuration."""
        method_name = getattr(args, 'method_name', None)
        if not method_name:
            print("Error: Method name required for show command")
            return 1

        method_config = self.method_manager.load_method(method_name)
        if not method_config:
            print(f"Error: Method '{method_name}' not found")
            return 1

        print(f"Configuration for method '{method_name}':")
        print(f"  Name: {method_config.name}")
        print(f"  Builder: {method_config.builder}")
        if method_config.inherit:
            print(f"  Inherits from: {method_config.inherit}")
        print(f"  Build Type: {method_config.config.build_type}")
        print(f"  Parallel: {method_config.config.parallel}")
        print(f"  Jobs: {method_config.config.jobs}")

        if hasattr(method_config.compiler, 'cc') and method_config.compiler.cc:
            print(f"  C Compiler: {method_config.compiler.cc}")
        if hasattr(method_config.compiler, 'cxx') and method_config.compiler.cxx:
            print(f"  C++ Compiler: {method_config.compiler.cxx}")
        if hasattr(method_config.compiler, 'c') and method_config.compiler.c:
            print(f"  C Compiler: {method_config.compiler.c}")
        if hasattr(method_config.compiler, 'cpp') and method_config.compiler.cpp:
            print(f"  C++ Compiler: {method_config.compiler.cpp}")

        if hasattr(method_config.compiler, 'cflags') and method_config.compiler.cflags:
            print(f"  C Flags: {method_config.compiler.cflags}")
        if hasattr(method_config.compiler, 'cxxflags') and method_config.compiler.cxxflags:
            print(f"  C++ Flags: {method_config.compiler.cxxflags}")
        if hasattr(method_config.compiler, 'ldflags') and method_config.compiler.ldflags:
            print(f"  Linker Flags: {method_config.compiler.ldflags}")

        if hasattr(method_config.platform, 'os') and method_config.platform.os != 'any':
            print(f"  OS: {method_config.platform.os}")
        if hasattr(method_config.platform, 'arch') and method_config.platform.arch != 'any':
            print(f"  Architecture: {method_config.platform.arch}")

        return 0

    def edit_method(self, args: argparse.Namespace) -> int:
        """Edit method configuration."""
        method_name = getattr(args, 'method_name', None)
        if not method_name:
            print("Error: Method name required for edit command")
            return 1

        # Check if method exists
        method_config = self.method_manager.load_method(method_name)
        if not method_config:
            print(f"Error: Method '{method_name}' does not exist. Use 'maestro make config detect' to create default methods.")
            return 1

        print(f"Editing method '{method_name}' (Note: This would normally open an editor)")
        # Get the path to the method file
        method_path = os.path.expanduser(f"~/.maestro/methods/{method_name}.toml")
        print(f"Method file location: {method_path}")
        print("Please edit the method file directly or use detect to recreate.")
        return 0
    
    def list_methods(self, args: argparse.Namespace) -> int:
        """List all available build methods."""
        methods = self.method_manager.get_available_methods()
        if not methods:
            print("No build methods found.")
            return 0

        print("Available build methods:")
        for method in methods:
            # Try to get additional info about the method
            method_config = self.method_manager.load_method(method)
            if method_config:
                builder = method_config.builder
                print(f"  - {method} ({builder})")
            else:
                print(f"  - {method}")
        return 0
    
    def detect_methods(self, args: argparse.Namespace) -> int:
        """Auto-detect and create methods."""
        print("Detecting available build tools and creating default methods...")
        created_methods = self.method_manager.create_default_methods()
        if created_methods:
            print("Created the following methods:")
            for method in created_methods:
                print(f"  - {method}")
        else:
            print("No build tools detected on the system")
        return 0
    
    def export(self, args: argparse.Namespace) -> int:
        """Export package to other build system format."""
        package_name = args.package
        if not package_name:
            current_dir = os.getcwd()
            package_name = self._detect_current_package(current_dir)
            if not package_name:
                print("Error: No package specified and none detected in current directory")
                return 1

        format_type = args.format
        if not format_type:
            print("Error: Export format required (makefile, cmake, msbuild, ninja)")
            return 1

        # Determine output directory
        output_dir = args.output or os.path.join(os.getcwd(), f"exported_{package_name}")
        os.makedirs(output_dir, exist_ok=True)

        # Find package info
        package_info = self._find_package_info(package_name)
        if not package_info:
            print(f"Error: Package '{package_name}' not found in repo")
            return 1

        # Import appropriate exporter
        try:
            from maestro.builders.export import Exporter, NinjaExporter
            exporter = Exporter()

            # Select the right export method based on format
            if format_type == 'cmake':
                success = exporter.export_to_cmake(package_info, output_dir)
            elif format_type == 'makefile':
                success = exporter.export_to_makefile(package_info, output_dir)
            elif format_type == 'ninja':
                success = exporter.export_to_ninja(package_info, output_dir)
            elif format_type == 'msbuild':
                success = exporter.export_to_msbuild(package_info, output_dir)
            else:
                print(f"Error: Unsupported export format: {format_type}")
                return 1

            if success:
                print(f"Successfully exported '{package_name}' to {format_type} format in: {output_dir}")
                return 0
            else:
                print(f"Failed to export '{package_name}' to {format_type} format")
                return 1
        except ImportError:
            print(f"Export functionality not available for {format_type} format")
            print("Please install required dependencies or use repo-based export")
            return 1
        except Exception as e:
            print(f"Error during export: {str(e)}")
            return 1
    
    def build_android(self, args: argparse.Namespace) -> int:
        """Build Android APK."""
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

        # Update method config with Android-specific settings from args
        if args.sdk_path:
            method_config.config.android_sdk_path = args.sdk_path
        if args.ndk_path:
            method_config.config.android_ndk_path = args.ndk_path
        if args.platform:
            method_config.config.android_platform = args.platform
        if args.arch:
            method_config.config.android_arch = args.arch
        if args.keystore:
            method_config.config.android_keystore = args.keystore
        if args.verbose:
            method_config.config.verbose = True

        # Determine package to build
        package_names = []
        if args.package:
            package_names.append(args.package)
        else:
            # Try to detect current package
            current_dir = os.getcwd()
            package_name = self._detect_current_package(current_dir)
            if not package_name:
                print("Error: No package specified and none detected in current directory")
                return 1
            package_names.append(package_name)

        for package_name in package_names:
            # Find package info
            package_info = self._find_package_info(package_name)
            if not package_info:
                print(f"Error: Package '{package_name}' not found in repo")
                return 1

            # Make sure package is an Android package
            if package_info.get('build_system') != 'android':
                # Try to detect if it has Android characteristics
                upp_path = package_info.get('upp_path', f"{package_name}.upp")
                if os.path.exists(upp_path):
                    try:
                        with open(upp_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        # Check if it has Android-related flags
                        android_flags = ['ANDROID', 'ANDROID_RESOURCES_PACKAGE', 'JNI']
                        has_android_flag = any(f in content.upper() for f in android_flags)
                        if not has_android_flag:
                            print(f"Warning: Package '{package_name}' doesn't appear to be an Android package")
                    except:
                        pass

            # Create Android builder
            builder = AndroidBuilder(method_config)

            if args.verbose:
                print(f"Building Android package: {package_name}")
            else:
                print(f"Building: {package_name}")

            success = builder.build_package(package_info, method_config)
            if success:
                if args.verbose:
                    print(f"Successfully built Android package: {package_name}")
                else:
                    print(f"Built APK: {package_name}")

                # Install if requested
                if args.install or args.run:
                    apk_path = os.path.join(package_info['dir'], f"{package_name}.apk")
                    if os.path.exists(apk_path):
                        if args.install:
                            install_cmd = ["adb", "install", "-r", apk_path]
                            import subprocess
                            try:
                                result = subprocess.run(install_cmd, capture_output=True, text=True)
                                if result.returncode == 0:
                                    print(f"Installed APK to device: {apk_path}")
                                    if args.run:
                                        # Run the app
                                        package_id = f"com.maestro.{package_name}"  # Default package ID
                                        run_cmd = ["adb", "shell", "am", "start", "-n", f"{package_id}/.MainActivity"]
                                        subprocess.run(run_cmd)
                                        print(f"Started app: {package_id}")
                                else:
                                    print(f"Failed to install APK: {result.stderr}")
                            except FileNotFoundError:
                                print("adb not found. Please install Android SDK tools.")
                        elif args.run:
                            print("Warning: --run specified but --install not specified. APK must be installed first.")
                    else:
                        print(f"Warning: APK not found at expected location: {apk_path}")
            else:
                print(f"Failed to build Android package: {package_name}")
                return 1

        return 0

    def build_jar(self, args: argparse.Namespace) -> int:
        """Build Java JAR."""
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

        # Update method config with JAR-specific settings from args
        if args.main_class:
            method_config.config.java_main_class = args.main_class
        if args.manifest:
            method_config.config.java_manifest_file = args.manifest
        if args.sign:
            method_config.config.java_sign_jar = args.sign
        if args.verbose:
            method_config.config.verbose = True

        # Determine package to build
        package_names = []
        if args.package:
            package_names.append(args.package)
        else:
            # Try to detect current package
            current_dir = os.getcwd()
            package_name = self._detect_current_package(current_dir)
            if not package_name:
                print("Error: No package specified and none detected in current directory")
                return 1
            package_names.append(package_name)

        for package_name in package_names:
            # Find package info
            package_info = self._find_package_info(package_name)
            if not package_info:
                print(f"Error: Package '{package_name}' not found in repo")
                return 1

            # Make sure package is a Java package
            if package_info.get('build_system') not in ['java', 'maven']:
                # Try to detect if it has Java characteristics
                upp_path = package_info.get('upp_path', f"{package_name}.upp")
                if os.path.exists(upp_path):
                    try:
                        with open(upp_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        # Check if it has Java-related flags
                        java_flags = ['JAVA', 'JAR', 'JNI']
                        has_java_flag = any(f in content.upper() for f in java_flags)
                        if not has_java_flag:
                            print(f"Warning: Package '{package_name}' doesn't appear to be a Java package")
                    except:
                        pass

            # Create Java builder
            builder = JavaBuilder(method_config)

            if args.verbose:
                print(f"Building Java JAR: {package_name}")
            else:
                print(f"Building JAR: {package_name}")

            success = builder.build_package(package_info, method_config)
            if success:
                if args.verbose:
                    print(f"Successfully built Java JAR: {package_name}")
                else:
                    print(f"Built JAR: {package_name}")

                # Sign the JAR if requested
                if args.sign:
                    jar_path = os.path.join(package_info['dir'], f"{package_name}.jar")
                    if os.path.exists(jar_path):
                        import subprocess
                        # Use jarsigner to sign the JAR (requires keystore)
                        # This assumes a default keystore exists or needs to be created
                        try:
                            # Check if jarsigner is available
                            result = subprocess.run(["jarsigner", "-help"], capture_output=True, text=True)
                            if result.returncode != 0:
                                print("Warning: jarsigner not available. Java signing skipped.")
                            else:
                                # For now, just indicate that signing would happen
                                print(f"JAR signing requested for: {jar_path}")
                                print("Note: Actual signing requires valid keystore configuration.")
                        except FileNotFoundError:
                            print("Warning: jarsigner not found. Please install Java Development Kit (JDK) for signing.")
            else:
                print(f"Failed to build Java JAR: {package_name}")
                return 1

        return 0
    
    def _detect_current_package(self, directory: str) -> Optional[str]:
        """Try to detect package name from current directory."""
        # Look for .upp file or other package markers
        for filename in os.listdir(directory):
            if filename.endswith('.upp'):
                package_name = filename[:-4]  # Remove .upp extension
                return package_name
        return None
    
    def _find_package_info(self, package_name: str) -> Optional[Dict]:
        """Find package information using repo scanning."""
        # Try to find the repository root
        repo_root = self._find_repo_root()
        if not repo_root:
            # If no .maestro directory found, use current directory
            repo_root = os.getcwd()
        
        # First, look for the package in the current directory
        if os.path.exists(f"{package_name}.upp"):
            upp_path = f"{package_name}.upp"
            build_system = 'upp'
            
            # Parse the .upp file to get more information
            try:
                # Read and parse the .upp file directly to determine build system
                with open(upp_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for keywords that indicate the build system
                content_lower = content.lower()
                if 'cmake' in content_lower:
                    build_system = 'cmake'
                elif 'autotools' in content_lower or 'autoconf' in content_lower:
                    build_system = 'autotools'
                elif 'maven' in content_lower:
                    build_system = 'maven'
                elif 'android' in content_lower:
                    build_system = 'android'
                elif 'msbuild' in content_lower or 'msvc' in content_lower or 'visual studio' in content_lower:
                    build_system = 'msbuild'
                elif 'java' in content_lower:
                    build_system = 'java'
            except:
                # If parsing fails, use default
                pass
            
            return {
                'name': package_name,
                'dir': os.getcwd(),
                'upp_path': upp_path,
                'build_system': build_system,
                'files': []  # Basic files list
            }
        
        # If not in current directory, try to find in repo
        try:
            # Look for .maestro/repo/index.json to find the package
            index_path = os.path.join(repo_root, '.maestro', 'repo', 'index.json')
            if os.path.exists(index_path):
                import json
                with open(index_path, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                
                # Search in packages
                for pkg in index_data.get('packages_detected', []):
                    if pkg['name'] == package_name:
                        return pkg
                
                # Search in internal packages
                for pkg in index_data.get('internal_packages', []):
                    if pkg['name'] == package_name:
                        return pkg
        except:
            pass
        
        # If not found in index, try to find .upp file in common locations
        possible_paths = [
            os.path.join(repo_root, f"{package_name}.upp"),
            os.path.join(repo_root, package_name, f"{package_name}.upp"),
            os.path.join(repo_root, "uppsrc", package_name, f"{package_name}.upp"),
            os.path.join(repo_root, "packages", package_name, f"{package_name}.upp")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                pkg_dir = os.path.dirname(path)
                return {
                    'name': package_name,
                    'dir': pkg_dir,
                    'upp_path': path,
                    'build_system': 'upp',
                    'files': []
                }
        
        return None

    def _find_repo_root(self) -> Optional[str]:
        """Find the repository root by looking for .maestro directory."""
        current_dir = os.getcwd()
        original_dir = current_dir

        while current_dir != '/':
            if os.path.exists(os.path.join(current_dir, '.maestro')):
                return current_dir
            parent_dir = os.path.dirname(current_dir)
            if parent_dir == current_dir:  # We've reached the root
                break
            current_dir = parent_dir

        # If not found, try common project root locations
        for path in [original_dir, os.path.dirname(original_dir)]:
            if os.path.exists(os.path.join(path, '.maestro')):
                return path

        return None

    def _apply_group_filter(self, package_info: Dict[str, Any], group_name: str) -> Optional[Dict[str, Any]]:
        """Filter package files to the specified internal group."""
        groups = package_info.get("groups", [])
        if not groups:
            return None

        for group in groups:
            name = group.get("name") if isinstance(group, dict) else getattr(group, "name", None)
            if name == group_name:
                files = group.get("files") if isinstance(group, dict) else getattr(group, "files", [])
                filtered = dict(package_info)
                filtered["files"] = list(files)
                return filtered
        return None

    def _prompt_issue_fix(self, repo_root: str, issue_ids: List[str]) -> None:
        """Prompt user to trigger automatic fixes for build issues."""
        if not issue_ids:
            return
        try:
            choice = input("Fix build errors automatically? (y/n): ").strip().lower()
        except EOFError:
            return
        if choice != "y":
            return
        for issue_id in issue_ids:
            cmd = self._work_issue_command(repo_root, issue_id)
            try:
                result = subprocess.run(cmd, check=False)
                if result.returncode != 0:
                    print(f"Warning: work command failed for issue {issue_id}")
            except Exception as exc:
                print(f"Warning: unable to run work command for issue {issue_id}: {exc}")

    def _work_issue_command(self, repo_root: str, issue_id: str) -> List[str]:
        """Build the command to invoke work issue."""
        if shutil.which("maestro"):
            return ["maestro", "work", "issue", issue_id]
        return [sys.executable, os.path.join(repo_root, "maestro.py"), "work", "issue", issue_id]

    def _resolve_analyzers(self, tools_arg: Optional[str]) -> List[str]:
        """Resolve requested analyzers, filtering by availability."""
        known = ["clang-tidy", "cppcheck", "pylint", "checkstyle"]
        if tools_arg:
            requested = [tool.strip() for tool in tools_arg.split(",") if tool.strip()]
        else:
            requested = known

        available = []
        for tool in requested:
            if tool not in known:
                print(f"Warning: Unknown analyzer '{tool}'")
                continue
            if shutil.which(tool):
                available.append(tool)
            else:
                print(f"Warning: Analyzer '{tool}' not found on PATH")
        return available

    def _run_analyzer(
        self,
        tool: str,
        target_path: str,
        args: argparse.Namespace,
        repo_root: str,
    ) -> tuple[int, str]:
        """Run a single analyzer and capture output."""
        if tool == "clang-tidy":
            files = self._collect_source_files(target_path, [".c", ".cc", ".cpp", ".cxx", ".h", ".hpp"])
            build_path = self._find_compile_commands(repo_root)
            output_parts = []
            exit_code = 0
            for file_path in files:
                cmd = ["clang-tidy", file_path]
                if build_path:
                    cmd.extend(["-p", build_path])
                result = subprocess.run(cmd, capture_output=True, text=True)
                exit_code = max(exit_code, result.returncode)
                output_parts.append(result.stdout or "")
                output_parts.append(result.stderr or "")
            return exit_code, "\n".join(output_parts).strip()

        if tool == "cppcheck":
            cmd = [
                "cppcheck",
                "--enable=warning,style,performance,portability",
                "--inline-suppr",
                "--template=gcc",
                target_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            output = "\n".join([result.stdout or "", result.stderr or ""]).strip()
            return result.returncode, output

        if tool == "pylint":
            cmd = ["pylint", "--output-format=text"]
            if args.pylint_rcfile:
                cmd.extend(["--rcfile", args.pylint_rcfile])
            cmd.append(target_path)
            result = subprocess.run(cmd, capture_output=True, text=True)
            output = "\n".join([result.stdout or "", result.stderr or ""]).strip()
            return result.returncode, output

        if tool == "checkstyle":
            if not args.checkstyle_config:
                print("Warning: checkstyle requires --checkstyle-config")
                return 0, ""
            cmd = ["checkstyle", "-c", args.checkstyle_config, "-f", "plain", target_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            output = "\n".join([result.stdout or "", result.stderr or ""]).strip()
            return result.returncode, output

        return 0, ""

    def _collect_source_files(self, base_path: str, extensions: List[str]) -> List[str]:
        """Collect source files under base_path matching extensions."""
        files = []
        path = Path(base_path)
        if path.is_file():
            if path.suffix in extensions:
                return [str(path)]
            return []
        for ext in extensions:
            files.extend(str(p) for p in path.rglob(f"*{ext}"))
        return files

    def _find_compile_commands(self, repo_root: str) -> Optional[str]:
        """Locate compile_commands.json for clang-tidy."""
        candidates = [
            os.path.join(repo_root, "compile_commands.json"),
            os.path.join(repo_root, "build", "compile_commands.json"),
            os.path.join(repo_root, ".maestro", "build", "compile_commands.json"),
        ]
        for path in candidates:
            if os.path.exists(path):
                return os.path.dirname(path)
        return None
    
    def _create_builder_for_package(self, package_info: Dict, method_config: MethodConfig):
        """Create appropriate builder for the package type."""
        # Use the builder selector to determine the appropriate builder
        from maestro.builders import select_builder
        builder = select_builder(package_info, method_config)
        return builder


def add_make_parser(subparsers):
    """Add make command parsers to the main parser."""
    make_parser = subparsers.add_parser('make', aliases=['m'], help='Universal build orchestration')
    
    # Create subparsers for make command
    make_subparsers = make_parser.add_subparsers(dest='make_subcommand', help='Make subcommands')
    
    # make build subcommand
    build_parser = make_subparsers.add_parser('build', aliases=['b'], help='Build one or more packages')
    build_parser.add_argument('package', nargs='?', help='Package name to build')
    build_parser.add_argument('--method', '-m', help='Build method to use (default: auto)')
    build_parser.add_argument('--config', help='Build configuration for U++ packages')
    build_parser.add_argument('--jobs', '-j', type=int, help='Parallel jobs (default: CPU count)')
    build_parser.add_argument('--target', help='Override output target path')
    build_parser.add_argument('--verbose', '-v', action='store_true', help='Show full build commands')
    build_parser.add_argument('--clean-first', action='store_true', help='Clean before building')
    build_parser.add_argument('--group', help='Build a specific internal group for the package')
    
    # make clean subcommand
    clean_parser = make_subparsers.add_parser('clean', aliases=['c'], help='Clean build artifacts for package(s)')
    clean_parser.add_argument('package', nargs='?', help='Package name to clean')
    clean_parser.add_argument('--method', '-m', help='Build method to use (default: auto)')
    
    # make rebuild subcommand
    rebuild_parser = make_subparsers.add_parser('rebuild', aliases=['r'], help='Clean and build package(s)')
    rebuild_parser.add_argument('package', nargs='?', help='Package name to rebuild')
    rebuild_parser.add_argument('--method', '-m', help='Build method to use (default: auto)')
    rebuild_parser.add_argument('--config', help='Build configuration for U++ packages')
    rebuild_parser.add_argument('--jobs', '-j', type=int, help='Parallel jobs (default: CPU count)')
    rebuild_parser.add_argument('--verbose', '-v', action='store_true', help='Show full build commands')
    
    # make config subcommand
    config_parser = make_subparsers.add_parser('config', aliases=['cfg'], help='Configure build methods and options')
    config_subparsers = config_parser.add_subparsers(dest='config_subcommand', help='Config subcommands')
    
    # make config list
    config_list_parser = config_subparsers.add_parser('list', aliases=['ls', 'l'], help='List available methods')
    
    # make config show
    config_show_parser = config_subparsers.add_parser('show', aliases=['sh', 's'], help='Show method configuration')
    config_show_parser.add_argument('method_name', help='Method name to show')
    
    # make config edit
    config_edit_parser = config_subparsers.add_parser('edit', aliases=['e'], help='Edit method configuration')
    config_edit_parser.add_argument('method_name', help='Method name to edit')
    
    # make config detect
    config_detect_parser = config_subparsers.add_parser('detect', aliases=['d'], help='Auto-detect and create methods')
    
    # make methods subcommand
    methods_parser = make_subparsers.add_parser('methods', aliases=['mth'], help='List all available build methods')

    # make analyze subcommand
    analyze_parser = make_subparsers.add_parser('analyze', aliases=['an'], help='Run static analyzers')
    analyze_parser.add_argument('--tools', help='Comma-separated analyzers (clang-tidy, cppcheck, pylint, checkstyle)')
    analyze_parser.add_argument('--path', help='Target file or directory (default: repo root)')
    analyze_parser.add_argument('--pylint-rcfile', help='Optional pylint rcfile path')
    analyze_parser.add_argument('--checkstyle-config', help='Checkstyle XML configuration path')
    
    # make export subcommand
    export_parser = make_subparsers.add_parser('export', aliases=['exp'], help='Export package to other build system format')
    export_parser.add_argument('package', nargs='?', help='Package name to export')
    export_parser.add_argument('format', nargs='?', choices=['makefile', 'cmake', 'msbuild', 'ninja'], 
                              help='Export format: makefile, cmake, msbuild, ninja')
    export_parser.add_argument('--output', '-o', help='Output directory for exported files')
    
    # make android subcommand
    android_parser = make_subparsers.add_parser('android', aliases=['a'], help='Build Android APK')
    android_parser.add_argument('package', nargs='?', help='Android package name to build')
    android_parser.add_argument('--sdk-path', help='Android SDK path (default: auto-detect)')
    android_parser.add_argument('--ndk-path', help='Android NDK path (default: auto-detect)')
    android_parser.add_argument('--platform', help='Android platform (e.g., android-30)')
    android_parser.add_argument('--arch', help='Target architecture(s) (armeabi-v7a, arm64-v8a, x86, x86_64)')
    android_parser.add_argument('--keystore', help='Keystore for signing')
    android_parser.add_argument('--install', action='store_true', help='Install to device after building')
    android_parser.add_argument('--run', action='store_true', help='Run app after installing')
    android_parser.add_argument('--method', '-m', help='Build method to use (default: auto)')
    
    # make jar subcommand
    jar_parser = make_subparsers.add_parser('jar', aliases=['j'], help='Build Java JAR')
    jar_parser.add_argument('package', nargs='?', help='Java package name to build')
    jar_parser.add_argument('--main-class', help='Main class for executable JAR')
    jar_parser.add_argument('--manifest', help='Custom manifest file')
    jar_parser.add_argument('--sign', action='store_true', help='Sign JAR with jarsigner')
    jar_parser.add_argument('--method', '-m', help='Build method to use (default: auto)')
    
    return make_parser
