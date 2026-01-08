import os
import subprocess
import re
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
        # Check for gradlew (Gradle wrapper) starting from current directory and walking up
        current = Path(os.getcwd()).resolve()
        
        while True:
            gradlew_local = current / "gradlew"
            gradlew_local_sh = current / "gradlew.sh"
            gradlew_local_bat = current / "gradlew.bat"
            
            if gradlew_local.exists() or gradlew_local_sh.exists():
                path = gradlew_local if gradlew_local.exists() else gradlew_local_sh
                # Make gradlew executable if needed
                try:
                    os.chmod(str(path), 0o755)
                except:
                    pass
                return str(path)
            elif gradlew_local_bat.exists():
                return str(gradlew_local_bat)
            
            if current == current.parent:
                break
            current = current.parent
        
        # If no wrapper, try system gradle command
        try:
            result = subprocess.run(["gradle", "--version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return "gradle"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Default to gradle if nothing found
        return "gradle"

    def build_package(self, package: Package) -> bool:
        """Build a Gradle package by reverse engineering its build steps.

        Args:
            package: Package to build

        Returns:
            True if build/extraction succeeded, False otherwise
        """
        # Check if we already have reverse-engineered data
        # We re-extract only if missing or if specifically forced (not implemented yet)
        if 'java_build_info' in package.metadata:
            return self._build_directly(package)

        print(f"Reverse engineering Gradle build for: {package.name}")
        
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
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=original_dir)
            
            if result.returncode != 0:
                print(f"Warning: Gradle extraction failed for {package.name}. Error: {result.stderr}")
                # Fallback: maybe the task name was wrong, try generic build
                cmd = [self.gradle_cmd, "clean", "build", "--info", "--console=plain"]
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=original_dir)

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
                            build_info['classpath'] = args[j].split(os.pathsep)
                    elif arg == "-d":
                        j += 1
                        if j < len(args):
                            build_info['destination'] = args[j]
                    elif arg in ["--release", "-encoding", "-source", "-target", "-h", "-s"]:
                        # Keep these flags and their values together
                        build_info['options'].append(arg)
                        j += 1
                        if j < len(args):
                            build_info['options'].append(args[j])
                    elif arg.startswith("-"):
                        build_info['options'].append(arg)
                    elif arg.endswith(".java"):
                        build_info['source_files'].append(arg)
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
                match = re.search(r"/([^/]+)/build/classes/java/main", entry)
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
            
        print(f"Building {package.name} directly using javac...")
        
        from .jdk import find_system_jdk
        jdk = find_system_jdk()
        if not jdk:
            print("Error: No JDK found for direct compilation")
            return False
            
        javac = jdk.get_tool_path("javac")
        
        # Ensure destination directory exists
        dest = build_info.get('destination')
        if dest:
            os.makedirs(dest, exist_ok=True)
            
        cmd = [javac]
        if build_info.get('options'):
            cmd.extend(build_info['options'])
            
        if build_info.get('classpath'):
            sep = os.pathsep
            cmd.extend(["-cp", sep.join(build_info['classpath'])])
            
        if dest:
            cmd.extend(["-d", dest])
            
        # Find source files if not explicitly listed in build_info
        sources = build_info.get('source_files', [])
        if not sources:
            # Fallback: scan source directory
            src_dir = os.path.join(package.directory, "src", "main", "java")
            if os.path.exists(src_dir):
                for root, dirs, files in os.walk(src_dir):
                    for f in files:
                        if f.endswith(".java"):
                            sources.append(os.path.join(root, f))
        
        cmd.extend(sources)
        
        print(f"Executing direct javac build for {package.name}")
        return execute_command(cmd)

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