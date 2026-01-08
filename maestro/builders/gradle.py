import os
import subprocess
import re
import platform
from pathlib import Path
from typing import Dict, Any, List, Optional
from .base import Builder, Package
from .config import MethodConfig
from .console import execute_command


class GradleBuilder(Builder):
    """Gradle builder implementation for building Gradle-based projects."""

    def __init__(self, config: MethodConfig = None):
        super().__init__("gradle", config)
        self.gradle_cmd = self._detect_gradle_command()

    def _detect_gradle_command(self) -> str:
        """Detect the appropriate Gradle command (gradle or gradlew)."""
        import platform
        is_windows = platform.system() == "Windows"
        
        # Check for gradlew (Gradle wrapper) starting from current directory and walking up
        current = Path(os.getcwd()).resolve()
        
        while True:
            # On Windows, prefer gradlew.bat or gradlew.cmd
            if is_windows:
                for ext in [".bat", ".cmd"]:
                    gradlew_win = current / f"gradlew{ext}"
                    if gradlew_win.exists():
                        return str(gradlew_win)
            
            # On both platforms, check for gradlew (shell script)
            gradlew_sh = current / "gradlew"
            if gradlew_sh.exists():
                if not is_windows:
                    # Make gradlew executable if needed
                    try:
                        os.chmod(str(gradlew_sh), 0o755)
                    except:
                        pass
                return str(gradlew_sh)
            
            if current == current.parent:
                break
            current = current.parent
        
        # If no wrapper, try system gradle command
        try:
            # Use shell=True on Windows to find 'gradle' in PATH if it's a batch file
            result = subprocess.run(["gradle", "--version"], 
                                  capture_output=True, text=True, timeout=10, shell=is_windows)
            if result.returncode == 0:
                return "gradle"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Default to gradle if nothing found
        return "gradle"

    def _normalize_gradle_path(self, path: str) -> str:
        """Normalize a path extracted from Gradle output to native format."""
        import platform
        if not path:
            return path
            
        if platform.system() == "Windows":
            # Replace backslashes with forward slashes for consistent regex matching
            temp_path = path.replace('\\', '/')
            
            # Handle /home/sblo -> E:/active/sblo/Dev/RainbowGame/
            # This maps the Linux home directory to the actual location of .gradle on this Windows machine
            if temp_path.startswith('/home/sblo/'):
                path = "E:/active/sblo/Dev/RainbowGame/" + temp_path[11:]
                temp_path = path.replace('\\', '/') # Update for further regex matching if needed
            
            # Handle /e/path -> E:/path (MSYS2/Git Bash style)
            # Also handle /E/path -> E:/path
            match = re.match(r'^/([a-zA-Z])/(.*)$', temp_path)
            if match:
                drive = match.group(1).upper()
                rest = match.group(2)
                path = f"{drive}:/{rest}"
            elif re.match(r'^/[a-zA-Z]$', temp_path):
                # Handle just "/e" -> "E:/"
                drive = temp_path[1].upper()
                path = f"{drive}:/"
            
            # Normalize to native backslashes
            path = os.path.normpath(path)
        return path

    def build_package(self, package: Package) -> bool:
        """Build a Gradle package by reverse engineering its build steps.

        Args:
            package: Package to build

        Returns:
            True if build/extraction succeeded, False otherwise
        """
        # Check if we already have reverse-engineered data
        if 'java_build_info' in package.metadata:
            build_info = package.metadata['java_build_info']
            
            import platform
            is_windows = platform.system() == "Windows"
            
            # If we're on Windows, check if paths need normalization
            # We prefer using existing info if extraction is likely to fail
            should_reextract = False
            
            # Only force re-extraction if we are NOT on Windows or if we think we can succeed.
            # On Windows, if we already have info, we try to use it because gradlew often fails.
            if not is_windows:
                cp = build_info.get('classpath', [])
                if cp:
                    for path in cp[:3]:
                        if not os.path.exists(path):
                            should_reextract = True
                            break
            
            if not should_reextract:
                # Attempt to build directly. If it fails due to missing files, 
                # then we might consider re-extraction if we haven't tried yet.
                return self._build_directly(package)

        print(f"Reverse engineering Gradle build for: {package.name}")
        
        import platform
        is_windows = platform.system() == "Windows"
        
        # Run Gradle with --info to capture build steps
        original_dir = os.getcwd()
        try:
            # Change to the root directory where gradlew is located if needed
            gradlew_path = Path(self.gradle_cmd)
            work_dir = package.directory
            
            # Construct command to get javac parameters
            # We use compileJava task specifically to get javac flags
            task_name = f":{package.name.replace('-', ':')}:compileJava"
            if package.name == os.path.basename(package.directory) and not package.name.startswith(":"):
                # Try simple task name if it's a root-like module
                task_name = f":{package.name}:compileJava"
            
            # If it's the root project
            if package.metadata.get('root_project') == package.name:
                task_name = "compileJava"

            cmd = [self.gradle_cmd, "clean", task_name, "--debug", "--console=plain"]
            
            print(f"Running extraction: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=original_dir, shell=is_windows)
            
            if result.returncode != 0:
                print(f"Warning: Gradle extraction failed for {package.name}. Exit code: {result.returncode}")
                if result.stderr:
                    print(f"Stderr: {result.stderr.strip()}")
                # Fallback: maybe the task name was wrong, try generic build
                print(f"Attempting fallback build for {package.name}...")
                cmd = [self.gradle_cmd, "clean", "build", "--info", "--console=plain"]
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=original_dir, shell=is_windows)

            # Parse the output to find javac parameters
            build_info = self._parse_gradle_info(result.stdout, package.name)
            
            if build_info:
                print(f"Successfully reverse engineered build info for {package.name}")
                package.metadata['java_build_info'] = build_info
                
                # Update the repo model with this new metadata
                self._persist_metadata(package)
                
                return self._build_directly(package)
            else:
                print(f"Failed to extract javac parameters for {package.name}")
                return False
                
        finally:
            os.chdir(original_dir)

    def _parse_gradle_info(self, output: str, package_name: str) -> Optional[Dict[str, Any]]:
        """Parse Gradle --info/--debug output to extract javac command parameters."""
        build_info = {
            'classpath': [],
            'source_files': [],
            'options': [],
            'destination': ''
        }
        
        print(f"Parsing Gradle output for {package_name}...")
        
        # Look for the compiler arguments line in debug output
        # It usually looks like: [DEBUG] [org.gradle.api.internal.tasks.compile.NormalizingJavaCompiler] Compiler arguments: ...
        
        # Normalize the task name for matching (e.g., :desktop:compileJava)
        task_match_pattern = f":{package_name.replace('-', ':')}:compileJava"
        
        current_task = None
        found_for_target = False
        
        lines = output.splitlines()
        for i, line in enumerate(lines):
            # Track which task we are in
            task_start_match = re.search(r"Executing actions for task '(.*)'", line)
            if task_start_match:
                current_task = task_start_match.group(1)
                if current_task == task_match_pattern or current_task.endswith(f":{package_name}:compileJava") or current_task == ":compileJava":
                    found_for_target = True
                else:
                    found_for_target = False
            
            # If we are in the correct task and find compiler arguments
            if found_for_target and "Compiler arguments:" in line:
                args_part = line.split("Compiler arguments:", 1)[1].strip()
                
                # Split arguments, handling tokens
                import shlex
                args = shlex.split(args_part)
                
                j = 0
                while j < len(args):
                    arg = args[j]
                    if arg == "-classpath" or arg == "-cp":
                        j += 1
                        if j < len(args):
                            # Split and normalize each classpath entry
                            raw_cp = args[j].split(os.pathsep)
                            build_info['classpath'] = [self._normalize_gradle_path(p) for p in raw_cp]
                    elif arg == "-d":
                        j += 1
                        if j < len(args):
                            build_info['destination'] = self._normalize_gradle_path(args[j])
                    elif arg in ["--release", "-encoding", "-source", "-target", "-h", "-s"]:
                        # Keep these flags and their values together
                        build_info['options'].append(arg)
                        j += 1
                        if j < len(args):
                            build_info['options'].append(args[j])
                    elif arg.startswith("-"):
                        build_info['options'].append(arg)
                    elif arg.endswith(".java"):
                        build_info['source_files'].append(self._normalize_gradle_path(arg))
                    j += 1
                
                # If we found destination, we consider this task's info captured
                if build_info['destination']:
                    break

        # Final check: if we found destination, we consider it a success
        if build_info['destination']:
            # Clean up classpath: remove empty strings, normalize paths
            build_info['classpath'] = [p for p in build_info['classpath'] if p.strip()]
            
            # Extract internal dependencies from classpath
            # We look for entries that look like build/classes of other modules
            internal_deps = []
            for entry in build_info['classpath']:
                # Example: .../RainbowGame/trash/core/build/classes/java/main
                # Handle both forward and backward slashes
                match = re.search(r"[/\\]([^/\\]+)[/\\]build[/\\]classes[/\\]java[/\\]main", entry)
                if match:
                    dep_name = match.group(1)
                    if dep_name != package_name and dep_name not in internal_deps:
                        internal_deps.append(dep_name)
            
            build_info['internal_dependencies'] = internal_deps
            return build_info
            
        return None

    def _persist_metadata(self, package: Package):
        """Save the updated metadata back to repo_model.json."""
        try:
            from ..repo.storage import find_repo_root, repo_model_path, load_repo_model
            repo_root = find_repo_root()
            model_path = repo_model_path(repo_root)
            model = load_repo_model(repo_root)
            
            build_info = package.metadata.get('java_build_info', {})
            internal_deps = build_info.get('internal_dependencies', [])
            
            updated = False
            # Update 'packages' (serialized for builds)
            for pkg in model.get('packages', []):
                if pkg['name'] == package.name:
                    pkg['metadata'] = package.metadata
                    # Sync top-level dependencies
                    for dep in internal_deps:
                        if dep not in pkg.get('dependencies', []):
                            pkg.setdefault('dependencies', []).append(dep)
                    updated = True
                    break
            
            # Update 'packages_detected' (from scanner)
            for pkg in model.get('packages_detected', []):
                if pkg['name'] == package.name:
                    pkg['metadata'] = package.metadata
                    # Sync top-level dependencies
                    for dep in internal_deps:
                        if dep not in pkg.get('dependencies', []):
                            pkg.setdefault('dependencies', []).append(dep)
                    updated = True
                    break
            
            if updated:
                import json
                with open(model_path, 'w', encoding='utf-8') as f:
                    json.dump(model, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not persist metadata: {e}")

    def _build_directly(self, package: Package) -> bool:
        """Run the build directly using javac using extracted info."""
        build_info = package.metadata.get('java_build_info')
        if not build_info:
            return False
            
        # Normalize paths in build_info if they were stored in POSIX style
        raw_classpath = build_info.get('classpath', [])
        
        # If we have a single string that contains ':' but we're on Windows, 
        # it's likely a POSIX classpath that needs careful splitting
        if len(raw_classpath) == 1 and ':' in raw_classpath[0] and os.pathsep == ';':
             raw_classpath = raw_classpath[0].split(':')
             
        classpath = [self._normalize_gradle_path(p) for p in raw_classpath]
        destination = self._normalize_gradle_path(build_info.get('destination', ''))
        sources = [self._normalize_gradle_path(s) for s in build_info.get('source_files', [])]
        
        # Output control based on configuration
        is_quiet = getattr(self.config.config, 'quiet', False)
        is_verbose = getattr(self.config.config, 'verbose', False)
        
        if not is_quiet:
            print(f"Building {package.name} directly using javac...")
        
        from .jdk import find_system_jdk
        jdk = find_system_jdk()
        if not jdk:
            print("Error: No JDK found for direct compilation")
            return False
            
        javac = jdk.get_tool_path("javac")
        
        # Ensure destination directory exists
        if destination:
            os.makedirs(destination, exist_ok=True)
            
        cmd = [javac]
        if build_info.get('options'):
            cmd.extend(build_info['options'])
            
        if classpath:
            sep = os.pathsep
            cmd.extend(["-cp", sep.join(classpath)])
            
        if destination:
            cmd.extend(["-d", destination])
            
        # Find source files if not explicitly listed in build_info
        if not sources:
            # Fallback: scan source directory
            src_dir = os.path.join(package.directory, "src", "main", "java")
            if os.path.exists(src_dir):
                for root, dirs, files in os.walk(src_dir):
                    for f in files:
                        if f.endswith(".java"):
                            sources.append(os.path.join(root, f))
        
        cmd.extend(sources)
        
        if is_verbose:
            print(f"Executing: {' '.join(cmd)}")
        elif not is_quiet:
            # Normal output: list files being compiled
            # We use relative paths for better readability
            from ..repo.storage import find_repo_root
            try:
                repo_root = find_repo_root()
            except:
                repo_root = os.getcwd()
                
            for s in sources:
                try:
                    # On Windows, relpath might fail if on different drives
                    # Fallback to absolute if it fails
                    rel_path = os.path.relpath(s, repo_root)
                    print(rel_path)
                except (ValueError, Exception):
                    print(s)
        
        # Use execute_command, passing verbose=False to it because we handled our own output
        # unless it's verbose mode where we might want to see additional stdout from javac
        return execute_command(cmd, verbose=is_verbose)

    def link(self, linkfiles: List[str], linkoptions: Dict[str, Any]) -> bool:
        """Linking for Java is often part of compilation or JAR creation."""
        return True

    def clean_package(self, package: Package) -> bool:
        """Clean package build artifacts."""
        print(f"Cleaning Gradle package: {package.name}")
        
        # Just remove the build directory
        build_dir = Path(package.directory) / "build"
        if build_dir.exists():
            import shutil
            shutil.rmtree(str(build_dir))
            return True
        return True

    def get_target_ext(self) -> str:
        return ".jar"

    def get_executable_path(self, package, method_config):
        """Find the executable for Gradle packages.

        For Gradle Application plugin projects, look for:
        1. build/install/{package.name}/bin/{package.name}[.bat] (from installDist)
        2. build/libs/*.jar (fallback, but requires main manifest)
        """
        import platform
        is_windows = platform.system() == "Windows"
        
        # First, try to find installDist output (Gradle Application plugin)
        # Note: we use package.dir or package.directory
        pkg_dir = getattr(package, 'directory', getattr(package, 'dir', ''))
        install_bin_dir = os.path.join(pkg_dir, "build", "install", package.name, "bin")
        
        if os.path.exists(install_bin_dir):
            if is_windows:
                # On Windows, prefer .bat or .cmd
                for ext in [".bat", ".cmd"]:
                    launcher_win = os.path.join(install_bin_dir, f"{package.name}{ext}")
                    if os.path.exists(launcher_win):
                        return launcher_win
            
            # Look for launcher script (Unix or as fallback on Windows)
            launcher_script = os.path.join(install_bin_dir, package.name)
            if os.path.exists(launcher_script):
                if not is_windows:
                    # Make sure it's executable on Unix
                    try:
                        os.chmod(launcher_script, 0o755)
                    except:
                        pass
                return launcher_script

        # Fallback: look for JAR files in build/libs/
        build_libs_dir = os.path.join(pkg_dir, "build", "libs")
        if not os.path.exists(build_libs_dir):
            return None

        # Look for JAR files, prefer ones matching package name
        jar_files = []
        for filename in os.listdir(build_libs_dir):
            if filename.endswith(".jar") and not filename.endswith("-sources.jar") and not filename.endswith("-javadoc.jar"):
                jar_path = os.path.join(build_libs_dir, filename)
                # Prefer JARs with package name
                if package.name in filename:
                    return jar_path
                jar_files.append(jar_path)

        # Return first JAR if no exact match
        if jar_files:
            return jar_files[0]

        return None