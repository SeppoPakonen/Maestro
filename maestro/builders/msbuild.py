"""
MSBuild Builder Implementation

This builder implements the MSBuild (Visual Studio) build system.
Supports building .vcxproj, .csproj, .vbproj, and .sln files.
"""

import os
import sys
import subprocess
import shutil
import re
import shlex
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Optional

from .base import Builder, Package
from .config import MethodConfig, BuildConfig


class MsBuildBuilder(Builder):
    """
    MSBuild builder implementation for Visual Studio projects.

    Supports:
    - Configuration selection (Debug, Release)
    - Platform selection (Win32, x64, ARM, ARM64)
    - Solution builds (.sln files)
    - Project dependency resolution
    - Modern (.vcxproj) and legacy (.vcproj) project formats
    """

    _DEFAULT_MSVC_LIBS = [
        "kernel32.lib",
        "user32.lib",
        "gdi32.lib",
        "winspool.lib",
        "comdlg32.lib",
        "advapi32.lib",
        "shell32.lib",
        "ole32.lib",
        "oleaut32.lib",
        "uuid.lib",
        "odbc32.lib",
        "odbccp32.lib",
    ]

    def __init__(self, config: MethodConfig = None):
        super().__init__("msbuild", config)
        self.msbuild_cmd = self._find_msbuild()
        self._vsdevcmd_env: Optional[Dict[str, str]] = None
        self._vsdevcmd_path: Optional[str] = None

    def _find_vsdevcmd(self) -> Optional[str]:
        compiler = None
        if self.config:
            compiler = self.config.compiler.cxx or self.config.compiler.cc
        if compiler:
            try:
                compiler_path = Path(compiler)
                for parent in compiler_path.parents:
                    candidate = parent / "Common7" / "Tools" / "VsDevCmd.bat"
                    if candidate.exists():
                        return str(candidate)
            except Exception:
                pass
        if self.msbuild_cmd:
            try:
                msbuild_path = Path(self.msbuild_cmd)
                for parent in msbuild_path.parents:
                    candidate = parent / "Common7" / "Tools" / "VsDevCmd.bat"
                    if candidate.exists():
                        return str(candidate)
            except Exception:
                pass

        candidates = [
            r"C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\Tools\VsDevCmd.bat",
            r"C:\Program Files\Microsoft Visual Studio\2022\Professional\Common7\Tools\VsDevCmd.bat",
            r"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\Common7\Tools\VsDevCmd.bat",
            r"C:\Program Files\Microsoft Visual Studio\2019\Community\Common7\Tools\VsDevCmd.bat",
            r"C:\Program Files\Microsoft Visual Studio\2019\Professional\Common7\Tools\VsDevCmd.bat",
            r"C:\Program Files\Microsoft Visual Studio\2019\Enterprise\Common7\Tools\VsDevCmd.bat",
            r"C:\Program Files\Microsoft Visual Studio\2017\Community\Common7\Tools\VsDevCmd.bat",
            r"C:\Program Files\Microsoft Visual Studio\2017\Professional\Common7\Tools\VsDevCmd.bat",
            r"C:\Program Files\Microsoft Visual Studio\2017\Enterprise\Common7\Tools\VsDevCmd.bat",
            r"C:\Program Files\Microsoft Visual Studio\18\Community\Common7\Tools\VsDevCmd.bat",
            r"C:\Program Files\Microsoft Visual Studio\18\Professional\Common7\Tools\VsDevCmd.bat",
            r"C:\Program Files\Microsoft Visual Studio\18\Enterprise\Common7\Tools\VsDevCmd.bat",
        ]

        for path in candidates:
            if os.path.exists(path):
                return path

        vswhere = r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
        if os.path.exists(vswhere):
            try:
                result = subprocess.run(
                    [vswhere, "-latest", "-products", "*", "-property", "installationPath"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True,
                )
                install_path = result.stdout.strip()
                if install_path:
                    candidate = os.path.join(install_path, "Common7", "Tools", "VsDevCmd.bat")
                    if os.path.exists(candidate):
                        return candidate
            except Exception:
                pass
        return None

    def _load_vsdevcmd_env(self, platform: str) -> Optional[Dict[str, str]]:
        if self._vsdevcmd_env is not None:
            return self._vsdevcmd_env

        vsdevcmd = self._find_vsdevcmd()
        if not vsdevcmd:
            self._vsdevcmd_env = None
            return None
        self._vsdevcmd_path = vsdevcmd

        arch = "x64"
        if platform.lower() in ("win32", "x86"):
            arch = "x86"

        cmd = f'cmd.exe /s /c ""{vsdevcmd}" -no_logo -arch={arch} -host_arch=x64 >nul && set"'
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                shell=True,
            )
            env = os.environ.copy()
            for line in result.stdout.splitlines():
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                env[key] = value
            if result.returncode == 0 and (env.get("VCToolsInstallDir") or env.get("VCINSTALLDIR")):
                self._vsdevcmd_env = env
                return env
        except Exception:
            pass
        self._vsdevcmd_env = None
        return None

    def _find_msbuild(self) -> Optional[str]:
        """
        Find the MSBuild executable on the system.
        On Windows: Look for MSBuild in Visual Studio installation
        On other platforms: Check for xbuild or msbuild in PATH
        """
        # Define possible MSBuild paths on Windows
        possible_paths = [
            shutil.which("msbuild"),  # Standard PATH lookup
            shutil.which("dotnet")    # dotnet build command
        ]

        # Check for Visual Studio installations on Windows
        if sys.platform.startswith("win"):
            # Common VS installation paths
            vs_paths = [
                r"C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Current\Bin\MSBuild.exe",
                r"C:\Program Files\Microsoft Visual Studio\18\Professional\MSBuild\Current\Bin\MSBuild.exe",
                r"C:\Program Files\Microsoft Visual Studio\18\Enterprise\MSBuild\Current\Bin\MSBuild.exe",
                r"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\MSBuild\Current\Bin\MSBuild.exe",
                r"C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\MSBuild.exe",
                r"C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe",
                r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Enterprise\MSBuild\Current\Bin\MSBuild.exe",
                r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Professional\MSBuild\Current\Bin\MSBuild.exe",
                r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\MSBuild\Current\Bin\MSBuild.exe",
                r"C:\Program Files (x86)\Microsoft Visual Studio\2017\Enterprise\MSBuild\15.0\Bin\MSBuild.exe",
                r"C:\Program Files (x86)\Microsoft Visual Studio\2017\Professional\MSBuild\15.0\Bin\MSBuild.exe",
                r"C:\Program Files (x86)\Microsoft Visual Studio\2017\Community\MSBuild\15.0\Bin\MSBuild.exe",
            ]

            for vs_path in vs_paths:
                if os.path.exists(vs_path):
                    return vs_path

        # Check standard paths found
        for path in possible_paths:
            if path:
                return path

        # Return None if no MSBuild found
        return None

    def _find_vc_targets_path(self) -> Optional[str]:
        if not self.msbuild_cmd:
            return None

        msbuild_path = Path(self.msbuild_cmd)
        try:
            msbuild_root = msbuild_path.parents[2]
        except IndexError:
            return None

        vc_root = msbuild_root / "Microsoft" / "VC"
        if not vc_root.exists():
            return None

        for candidate in sorted(vc_root.glob("v*"), reverse=True):
            props = candidate / "Microsoft.Cpp.Default.props"
            if props.exists():
                return str(candidate) + os.sep

        return None

    def _find_platform_toolset(self, vc_targets_path: str, platform: str) -> Optional[str]:
        platform_dir = platform
        if platform.lower() in ("win32", "x86"):
            platform_dir = "Win32"
        elif platform.lower() in ("x64", "amd64", "x86_64"):
            platform_dir = "x64"

        toolset_root = Path(vc_targets_path) / "Platforms" / platform_dir / "PlatformToolsets"
        if not toolset_root.exists():
            return None

        toolsets = [d.name for d in toolset_root.iterdir() if d.is_dir()]
        if not toolsets:
            return None
        if "v143" in toolsets:
            return "v143"

        def toolset_key(name: str) -> int:
            match = re.match(r"v(\d+)", name)
            if match:
                return int(match.group(1))
            return 0

        toolsets.sort(key=toolset_key)
        return toolsets[-1]

    def _find_project_file(self, package_dir: str) -> Optional[str]:
        """
        Find the appropriate project or solution file in the package directory.

        Looks for:
        - .sln files (solutions)
        - .vcxproj files (C++ projects)
        - .csproj files (C# projects)
        - .vbproj files (VB.NET projects)
        - .vcproj files (legacy C++ projects)
        """
        package_path = Path(package_dir)

        # Define priority order for project files
        project_extensions = ['.sln', '.vcxproj', '.csproj', '.vbproj', '.vcproj']

        for ext in project_extensions:
            project_files = list(package_path.glob(f'*{ext}'))
            if project_files:
                # If multiple files exist, prefer files named after the package
                for proj_file in project_files:
                    if package_path.name.lower() in proj_file.name.lower():
                        return str(proj_file)

                # Otherwise, return the first file found
                return str(project_files[0])

        return self._find_project_file_recursive(package_path, project_extensions)

    def _find_project_file_recursive(self, package_path: Path, project_extensions: List[str]) -> Optional[str]:
        candidates = []
        for ext in project_extensions:
            candidates.extend(package_path.rglob(f'*{ext}'))
        if not candidates:
            return None

        def score_candidate(path: Path) -> int:
            path_lower = str(path).lower()
            score = 0
            if "vcpp" in path_lower:
                score += 3
            if "msvs" in path_lower or "visualstudio" in path_lower:
                score += 2
            if package_path.name.lower() in path_lower:
                score += 1
            return score

        candidates.sort(key=score_candidate, reverse=True)
        return str(candidates[0])

    def _condition_matches(self, condition: Optional[str], configuration: str, platform: str) -> bool:
        if not condition:
            return True
        normalized = condition.replace('"', "'").replace(" ", "")
        config_platform = f"{configuration}|{platform}"
        match = re.search(r"'?\$\((?:Configuration)\)\|\$\((?:Platform)\)'?\s*==\s*'([^']+)'", normalized)
        if match:
            return match.group(1).lower() == config_platform.lower()
        match = re.search(r"'?\$\((?:Configuration)\)'?\s*==\s*'([^']+)'", normalized)
        if match:
            return match.group(1).lower() == configuration.lower()
        match = re.search(r"'?\$\((?:Platform)\)'?\s*==\s*'([^']+)'", normalized)
        if match:
            return match.group(1).lower() == platform.lower()
        return config_platform.lower() in normalized.lower()

    def _split_msbuild_list(self, value: str) -> List[str]:
        parts = [item.strip() for item in value.split(';') if item.strip()]
        return [item for item in parts if not item.startswith('%(')]

    def _ns_tag(self, ns_uri: str, tag: str) -> str:
        return f"{{{ns_uri}}}{tag}" if ns_uri else tag

    def _expand_msbuild_vars(self, value: str, variables: Dict[str, str]) -> str:
        def replace(match: re.Match) -> str:
            key = match.group(1)
            if key in variables:
                return variables[key]
            env_value = os.environ.get(key)
            if env_value is not None:
                return env_value
            return match.group(0)
        return re.sub(r"\$\(([^)]+)\)", replace, value)

    def _is_valid_vcpkg_root(self, path: Optional[str]) -> bool:
        if not path:
            return False
        return os.path.isdir(path) and os.path.isdir(os.path.join(path, "installed"))

    def _infer_vcpkg_root_from_path(self, path: str) -> Optional[str]:
        try:
            parts = Path(os.path.normpath(path)).parts
            lower_parts = [part.lower() for part in parts]
            if "vcpkg" in lower_parts:
                idx = lower_parts.index("vcpkg")
                return str(Path(*parts[:idx + 1]))
        except Exception:
            pass
        return None

    def _resolve_vcpkg_root(self, repo_root: Optional[str] = None) -> Optional[str]:
        env_override = os.environ.get("TESS_VCPKG_ROOT")
        if self._is_valid_vcpkg_root(env_override):
            return env_override

        env_root = os.environ.get("VCPKG_ROOT")
        if self._is_valid_vcpkg_root(env_root):
            return env_root

        env_install = os.environ.get("VCPKG_INSTALLATION_ROOT")
        if self._is_valid_vcpkg_root(env_install):
            return env_install

        custom_root = self.config.custom.get("vcpkg_root")
        if self._is_valid_vcpkg_root(custom_root):
            return custom_root

        if repo_root:
            sibling_root = os.path.join(os.path.dirname(repo_root), "vcpkg")
            if self._is_valid_vcpkg_root(sibling_root):
                return sibling_root

        for inc in (self.config.compiler.includes or []):
            inferred = self._infer_vcpkg_root_from_path(inc)
            if self._is_valid_vcpkg_root(inferred):
                return inferred

        for flag in (self.config.compiler.ldflags or []):
            if flag.startswith("/LIBPATH:"):
                inferred = self._infer_vcpkg_root_from_path(flag.split(":", 1)[1])
                if self._is_valid_vcpkg_root(inferred):
                    return inferred

        home_root = os.path.join(str(Path.home()), "vcpkg")
        if self._is_valid_vcpkg_root(home_root):
            return home_root

        return None

    def _compiler_on_path(self, compiler: str, env: Dict[str, str]) -> bool:
        if not compiler:
            return False
        if os.path.isabs(compiler):
            return os.path.exists(compiler)
        path_value = env.get("PATH") or env.get("Path") or ""
        return shutil.which(compiler, path=path_value) is not None

    def _collect_msbuild_property(self, root: ET.Element, ns_uri: str, tag: str,
                                  configuration: str, platform: str) -> Optional[str]:
        value = None
        for prop_group in root.findall(self._ns_tag(ns_uri, 'PropertyGroup')):
            condition = prop_group.get('Condition')
            if not self._condition_matches(condition, configuration, platform):
                continue
            for elem in prop_group.findall(self._ns_tag(ns_uri, tag)):
                if not self._condition_matches(elem.get('Condition'), configuration, platform):
                    continue
                if elem.text:
                    value = elem.text.strip()
        return value

    def _strip_ns(self, tag: str) -> str:
        if tag.startswith("{"):
            return tag[tag.index("}") + 1:]
        return tag

    def _split_msbuild_options(self, value: str) -> List[str]:
        if not value:
            return []
        parts = shlex.split(value, posix=False)
        return [part for part in parts if "%(" not in part]

    def _normalize_dir(self, value: Optional[str], project_dir: str, variables: Dict[str, str]) -> Optional[str]:
        if not value:
            return None
        expanded = self._expand_msbuild_vars(value, variables)
        if "$(" in expanded:
            return expanded
        if os.path.isabs(expanded):
            normed = os.path.normpath(expanded)
        else:
            normed = os.path.normpath(os.path.join(project_dir, expanded))
        if not normed.endswith(os.sep):
            normed += os.sep
        return normed

    def _expand_item_macros(self, value: str, source_path: str, source_raw: str, project_dir: str,
                            variables: Dict[str, str]) -> str:
        if not value:
            return value
        expanded = self._expand_msbuild_vars(value, variables)
        raw_path = source_raw or source_path
        filename = os.path.splitext(os.path.basename(raw_path))[0]
        extension = os.path.splitext(raw_path)[1]
        rel_dir = ""
        if raw_path and not os.path.isabs(raw_path):
            rel_dir = os.path.dirname(raw_path).replace("/", os.sep).replace("\\", os.sep)
            if rel_dir and not rel_dir.endswith(os.sep):
                rel_dir += os.sep
        expanded = expanded.replace("%(Filename)", filename)
        expanded = expanded.replace("%(Extension)", extension)
        expanded = expanded.replace("%(Identity)", raw_path)
        expanded = expanded.replace("%(RelativeDir)", rel_dir)
        if "$(" not in expanded and not os.path.isabs(expanded):
            expanded = os.path.normpath(os.path.join(project_dir, expanded))
        return expanded

    def _parse_vcxproj(self, project_file: str, configuration: str, platform: str) -> Dict[str, Any]:
        tree = ET.parse(project_file)
        root = tree.getroot()
        ns_uri = ''
        if root.tag.startswith('{'):
            ns_uri = root.tag[1:root.tag.index('}')]

        project_dir = str(Path(project_file).parent)
        project_name = Path(project_file).stem

        configuration_type = self._collect_msbuild_property(root, ns_uri, "ConfigurationType", configuration, platform)
        target_name = self._collect_msbuild_property(root, ns_uri, "TargetName", configuration, platform) or project_name
        target_ext = self._collect_msbuild_property(root, ns_uri, "TargetExt", configuration, platform)
        out_dir = self._collect_msbuild_property(root, ns_uri, "OutDir", configuration, platform)
        int_dir = self._collect_msbuild_property(root, ns_uri, "IntDir", configuration, platform)

        if not target_ext:
            if configuration_type == "StaticLibrary":
                target_ext = ".lib"
            elif configuration_type == "DynamicLibrary":
                target_ext = ".dll"
            else:
                target_ext = ".exe"

        variables = {
            "Configuration": configuration,
            "Platform": platform,
            "ProjectDir": project_dir + os.sep,
            "ProjectName": project_name,
            "TargetName": target_name,
            "TargetExt": target_ext,
            "OutDir": out_dir or "",
            "IntDir": int_dir or "",
        }
        if out_dir:
            variables["OutDir"] = self._expand_msbuild_vars(out_dir, variables)
        if int_dir:
            variables["IntDir"] = self._expand_msbuild_vars(int_dir, variables)

        normalized_out_dir = self._normalize_dir(out_dir, project_dir, variables)
        normalized_int_dir = self._normalize_dir(int_dir, project_dir, variables)

        include_dirs: List[str] = []
        defines: List[str] = []
        libs: List[str] = []
        lib_dirs: List[str] = []
        output_file = None
        uses_default_libs = False
        cl_settings: Dict[str, str] = {}
        link_settings: Dict[str, str] = {}
        rc_settings: Dict[str, str] = {}

        for item_def_group in root.findall(self._ns_tag(ns_uri, 'ItemDefinitionGroup')):
            condition = item_def_group.get('Condition')
            if not self._condition_matches(condition, configuration, platform):
                continue

            cl_compile = item_def_group.find(self._ns_tag(ns_uri, 'ClCompile'))
            if cl_compile is not None:
                for child in list(cl_compile):
                    if child.text and self._condition_matches(child.get("Condition"), configuration, platform):
                        cl_settings[self._strip_ns(child.tag)] = child.text.strip()
                includes_elem = cl_compile.find(self._ns_tag(ns_uri, 'AdditionalIncludeDirectories'))
                if includes_elem is not None and includes_elem.text:
                    include_dirs.extend(self._split_msbuild_list(includes_elem.text))
                defines_elem = cl_compile.find(self._ns_tag(ns_uri, 'PreprocessorDefinitions'))
                if defines_elem is not None and defines_elem.text:
                    defines.extend(self._split_msbuild_list(defines_elem.text))

            link = item_def_group.find(self._ns_tag(ns_uri, 'Link'))
            if link is not None:
                for child in list(link):
                    if child.text and self._condition_matches(child.get("Condition"), configuration, platform):
                        link_settings[self._strip_ns(child.tag)] = child.text.strip()
                deps_elem = link.find(self._ns_tag(ns_uri, 'AdditionalDependencies'))
                if deps_elem is not None and deps_elem.text:
                    if "%(AdditionalDependencies)" in deps_elem.text:
                        uses_default_libs = True
                    libs.extend(self._split_msbuild_list(deps_elem.text))
                libdir_elem = link.find(self._ns_tag(ns_uri, 'AdditionalLibraryDirectories'))
                if libdir_elem is not None and libdir_elem.text:
                    lib_dirs.extend(self._split_msbuild_list(libdir_elem.text))
                output_elem = link.find(self._ns_tag(ns_uri, 'OutputFile'))
                if output_elem is not None and output_elem.text:
                    output_file = output_elem.text.strip()
            resource = item_def_group.find(self._ns_tag(ns_uri, 'ResourceCompile'))
            if resource is not None:
                for child in list(resource):
                    if child.text and self._condition_matches(child.get("Condition"), configuration, platform):
                        rc_settings[self._strip_ns(child.tag)] = child.text.strip()

        source_files: List[str] = []
        compile_items: List[Dict[str, str]] = []
        resource_items: List[Dict[str, str]] = []
        for item_group in root.findall(self._ns_tag(ns_uri, 'ItemGroup')):
            for elem in item_group.findall(self._ns_tag(ns_uri, "ClCompile")):
                include = elem.get("Include")
                if not include:
                    continue
                source_files.append(include)
                item = {"Include": include}
                for child in list(elem):
                    if child.text and self._condition_matches(child.get("Condition"), configuration, platform):
                        item[self._strip_ns(child.tag)] = child.text.strip()
                compile_items.append(item)
            for elem in item_group.findall(self._ns_tag(ns_uri, "ResourceCompile")):
                include = elem.get("Include")
                if not include:
                    continue
                source_files.append(include)
                item = {"Include": include}
                for child in list(elem):
                    if child.text and self._condition_matches(child.get("Condition"), configuration, platform):
                        item[self._strip_ns(child.tag)] = child.text.strip()
                resource_items.append(item)

        expanded_includes = [self._expand_msbuild_vars(value, variables) for value in include_dirs]
        expanded_defines = [self._expand_msbuild_vars(value, variables) for value in defines]
        expanded_libs = [self._expand_msbuild_vars(value, variables) for value in libs]
        expanded_lib_dirs = [self._expand_msbuild_vars(value, variables) for value in lib_dirs]

        if output_file:
            output_file = self._expand_msbuild_vars(output_file, variables)
        else:
            if normalized_out_dir:
                output_file = os.path.join(normalized_out_dir, f"{target_name}{target_ext}")
            elif out_dir:
                output_file = os.path.join(out_dir, f"{target_name}{target_ext}")
            else:
                output_file = f"{target_name}{target_ext}"

        output_file = self._expand_msbuild_vars(output_file, variables)
        if "$(" not in output_file and not os.path.isabs(output_file):
            output_file = os.path.normpath(os.path.join(project_dir, output_file))

        resolved_sources = []
        for src in source_files:
            expanded = self._expand_msbuild_vars(src, variables)
            if "$(" in expanded:
                resolved_sources.append(expanded)
            elif os.path.isabs(expanded):
                resolved_sources.append(os.path.normpath(expanded))
            else:
                resolved_sources.append(os.path.normpath(os.path.join(project_dir, expanded)))

        return {
            "project_file": project_file,
            "sources": resolved_sources,
            "include_dirs": expanded_includes,
            "defines": expanded_defines,
            "libraries": expanded_libs,
            "library_dirs": expanded_lib_dirs,
            "output": output_file,
            "uses_default_libs": uses_default_libs,
            "int_dir": normalized_int_dir,
            "out_dir": normalized_out_dir,
            "cl_settings": cl_settings,
            "link_settings": link_settings,
            "rc_settings": rc_settings,
            "compile_items": compile_items,
            "resource_items": resource_items,
            "project_dir": project_dir,
            "variables": variables,
        }

    def _find_repo_root(self, start_dir: str) -> Optional[str]:
        current = Path(start_dir)
        while True:
            if (current / ".git").exists():
                return str(current)
            if current.parent == current:
                break
            current = current.parent
        return None

    def _print_dry_run_plan(self, plan: Dict[str, Any], repo_root: Optional[str]) -> None:
        include_dirs = plan.get("include_dirs", [])
        defines = plan.get("defines", [])
        libraries = plan.get("libraries", [])
        library_dirs = plan.get("library_dirs", [])
        output_file = plan.get("output")
        sources = plan.get("sources", [])

        if include_dirs:
            print(f"[msbuild] includes: {';'.join(include_dirs)}")
        if defines:
            print(f"[msbuild] defines: {';'.join(defines)}")
        if library_dirs:
            print(f"[msbuild] libdirs: {';'.join(library_dirs)}")
        if libraries:
            print(f"[msbuild] libs: {';'.join(libraries)}")

        for src in sources:
            if repo_root and os.path.isabs(src):
                try:
                    print(os.path.relpath(src, repo_root))
                    continue
                except ValueError:
                    pass
            print(src)

        if output_file:
            print(output_file)

    def _extract_solution_projects(self, solution_file: str) -> List[str]:
        """
        Extract project information from a solution file (.sln).
        This helps with dependency resolution in multi-project solutions.

        Args:
            solution_file: Path to the solution file

        Returns:
            List of project file paths referenced in the solution
        """
        project_paths = []
        try:
            with open(solution_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Look for Project entries in the solution file
            import re
            # Split the content by 'EndProject' and then look for the project line in each section
            sections = content.split('EndProject')

            for section in sections:
                # Look for the project path in each section
                project_match = re.search(r'Project\([^)]*\)\s*=\s*"[^"]*"\s*,\s*"([^"]+)"\s*,\s*"[^"]*"', section)
                if project_match:
                    project_ref = project_match.group(1)
                    # Resolve the relative path from solution directory
                    project_path = (Path(solution_file).parent / project_ref).resolve()
                    # Always add the resolved path, but warn if it doesn't exist
                    resolved_path = str(project_path)
                    if not project_path.exists():
                        print(f"[msbuild] Warning: Project file {resolved_path} referenced in solution does not exist")
                    project_paths.append(resolved_path)

        except Exception as e:
            print(f"[msbuild] Warning: Could not parse solution file {solution_file}: {str(e)}")

        return project_paths

    def _get_configuration_from_build_type(self, build_type: str) -> str:
        """Map build_type to Visual Studio configuration."""
        mapping = {
            'debug': 'Debug',
            'release': 'Release',
            'relwithdebinfo': 'RelWithDebInfo',
            'minsizerel': 'MinSizeRel'
        }
        return mapping.get(build_type.lower(), 'Debug')

    def _get_platform_from_config(self, config: Optional["BuildConfig"] = None) -> str:
        """Get platform from build config, with defaults."""
        platform_map = {
            'x86': 'Win32',
            'x64': 'x64',
            'amd64': 'x64',
            'x86_64': 'x64',
            'arm': 'ARM',
            'arm64': 'ARM64'
        }

        platform = None
        if config and getattr(config, "flags", None):
            platform = config.flags.get('platform')

        if platform is None:
            # Check if platform is specified in config custom properties
            platform = self.config.custom.get('platform', 'x64')

            # Check if platform is in platform config
            if hasattr(self.config.platform, 'arch') and self.config.platform.arch:
                platform = self.config.platform.arch

        # Return mapped platform or platform as-is if not in map
        return platform_map.get(platform.lower(), platform)

    def _is_msc(self, compiler_path: str) -> bool:
        if not compiler_path:
            return False
        base_name = os.path.basename(compiler_path).lower()
        return base_name in ("cl.exe", "cl")

    def _get_msc_linker(self, compiler_path: str) -> str:
        if not compiler_path:
            return "link.exe"
        base_name = os.path.basename(compiler_path)
        dir_name = os.path.dirname(compiler_path)
        if base_name.lower() == "cl.exe":
            return os.path.join(dir_name, "link.exe")
        if base_name.lower() == "cl":
            return os.path.join(dir_name, "link")
        return compiler_path.replace("cl.exe", "link.exe").replace("cl", "link")

    def _find_rc(self) -> str:
        return shutil.which("rc.exe") or shutil.which("rc") or "rc.exe"

    def _find_rc_in_env(self, env: Dict[str, str]) -> str:
        sdk_dir = env.get("WindowsSdkDir")
        sdk_ver = env.get("WindowsSdkVersion")
        if sdk_dir and sdk_ver:
            candidate = Path(sdk_dir) / "bin" / sdk_ver / "x64" / "rc.exe"
            if candidate.exists():
                return str(candidate)
        if sdk_dir:
            candidate = Path(sdk_dir) / "bin" / "x64" / "rc.exe"
            if candidate.exists():
                return str(candidate)

        kits_root = Path(r"C:\Program Files (x86)\Windows Kits\10\bin")
        if kits_root.exists():
            candidates = sorted(kits_root.glob("*\\x64\\rc.exe"), reverse=True)
            if candidates:
                return str(candidates[0])
        kits_81 = Path(r"C:\Program Files (x86)\Windows Kits\8.1\bin\x64\rc.exe")
        if kits_81.exists():
            return str(kits_81)

        for entry in env.get("PATH", "").split(os.pathsep):
            entry = entry.strip().strip('"')
            if not entry:
                continue
            candidate = Path(entry) / "rc.exe"
            if candidate.exists():
                return str(candidate)
        return self._find_rc()

    def _msvc_flags_from_cl_settings(self, settings: Dict[str, str]) -> List[str]:
        flags: List[str] = []
        optimization = settings.get("Optimization", "").lower()
        if optimization == "disabled":
            flags.append("/Od")
        elif optimization == "maxspeed":
            flags.append("/O2")
        elif optimization == "minspace":
            flags.append("/O1")

        inline_expansion = settings.get("InlineFunctionExpansion", "").lower()
        if inline_expansion == "anysuitable":
            flags.append("/Ob2")
        elif inline_expansion == "default":
            flags.append("/Ob1")

        favor = settings.get("FavorSizeOrSpeed", "").lower()
        if favor == "speed":
            flags.append("/Ot")
        elif favor == "size":
            flags.append("/Os")

        if settings.get("OmitFramePointers", "").lower() == "true":
            flags.append("/Oy")
        if settings.get("StringPooling", "").lower() == "true":
            flags.append("/GF")

        exception_handling = settings.get("ExceptionHandling", "").lower()
        if exception_handling == "async":
            flags.append("/EHa")
        elif exception_handling == "sync":
            flags.append("/EHsc")

        runtime = settings.get("RuntimeLibrary", "")
        runtime_map = {
            "MultiThreaded": "/MT",
            "MultiThreadedDebug": "/MTd",
            "MultiThreadedDLL": "/MD",
            "MultiThreadedDebugDLL": "/MDd",
        }
        if runtime in runtime_map:
            flags.append(runtime_map[runtime])

        if settings.get("BufferSecurityCheck", "").lower() == "false":
            flags.append("/GS-")
        elif settings.get("BufferSecurityCheck", "").lower() == "true":
            flags.append("/GS")

        if settings.get("FunctionLevelLinking", "").lower() == "true":
            flags.append("/Gy")

        fp_model = settings.get("FloatingPointModel", "").lower()
        if fp_model == "fast":
            flags.append("/fp:fast")
        elif fp_model == "strict":
            flags.append("/fp:strict")
        elif fp_model == "precise":
            flags.append("/fp:precise")

        if settings.get("ForceConformanceInForLoopScope", "").lower() == "true":
            flags.append("/Zc:forScope")

        warning = settings.get("WarningLevel", "").lower()
        warning_map = {
            "level0": "/W0",
            "level1": "/W1",
            "level2": "/W2",
            "level3": "/W3",
            "level4": "/W4",
        }
        if warning in warning_map:
            flags.append(warning_map[warning])

        if settings.get("SuppressStartupBanner", "").lower() == "true":
            flags.append("/nologo")

        debug_format = settings.get("DebugInformationFormat", "").lower()
        if debug_format == "programdatabase":
            flags.append("/Zi")
        elif debug_format == "oldstyle":
            flags.append("/Z7")

        additional = self._split_msbuild_options(settings.get("AdditionalOptions", ""))
        flags.extend(additional)
        return flags

    def _msvc_flags_from_link_settings(self, settings: Dict[str, str], variables: Dict[str, str],
                                       project_dir: str) -> List[str]:
        flags: List[str] = []
        if settings.get("GenerateDebugInformation", "").lower() == "true":
            flags.append("/DEBUG")
        subsystem = settings.get("SubSystem")
        if subsystem:
            flags.append(f"/SUBSYSTEM:{subsystem}")
        if settings.get("OptimizeReferences", "").lower() == "true":
            flags.append("/OPT:REF")
        if settings.get("EnableCOMDATFolding", "").lower() == "true":
            flags.append("/OPT:ICF")
        if settings.get("IgnoreAllDefaultLibraries", "").lower() == "true":
            flags.append("/NODEFAULTLIB")
        if settings.get("GenerateMapFile", "").lower() == "true":
            flags.append("/MAP")
        map_file = settings.get("MapFileName")
        if map_file:
            expanded = self._expand_msbuild_vars(map_file, variables)
            if "$(" not in expanded and not os.path.isabs(expanded):
                expanded = os.path.normpath(os.path.join(project_dir, expanded))
            flags.append(f"/MAP:{expanded}")

        if settings.get("SuppressStartupBanner", "").lower() == "true":
            flags.append("/nologo")

        additional = self._split_msbuild_options(settings.get("AdditionalOptions", ""))
        flags.extend(additional)
        return flags

    def _normalize_msvc_flags_for_cl(self, flags: List[str]) -> List[str]:
        normalized: List[str] = []
        for flag in flags:
            if flag.startswith("-I"):
                normalized.append("/I" + flag[2:])
            elif flag.startswith("-D"):
                normalized.append("/D" + flag[2:])
            else:
                normalized.append(flag)
        return normalized

    def _normalize_msvc_flags_for_link(self, flags: List[str]) -> List[str]:
        normalized: List[str] = []
        for flag in flags:
            if flag.startswith("-L"):
                normalized.append("/LIBPATH:" + flag[2:])
            else:
                normalized.append(flag)
        return normalized

    def _format_msvc_path_arg(self, flag: str, path: str) -> str:
        return f"{flag}{path}"

    def _run_command(self, cmd: List[str], cwd: str, verbose: bool, env: Optional[Dict[str, str]] = None) -> bool:
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if verbose and result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            if result.returncode != 0 and result.stdout and not verbose:
                print(result.stdout)
            return result.returncode == 0
        except Exception as e:
            print(f"[msbuild] Error executing command {cmd}: {e}")
            return False

    def configure(self, package: Package, config: Optional["BuildConfig"] = None) -> bool:
        """
        Configure the MSBuild project.
        Creates or updates project settings based on config.
        """
        # For MSBuild, configuration is typically handled via command line args
        # So we just verify we can find the project file
        project_file = self._find_project_file(package.path)
        if not project_file:
            print(f"[msbuild] No project or solution file found in {package.path}")
            return False

        # Store the project file in the package metadata for later use
        package.metadata['project_file'] = project_file
        return True

    def build_package(self, package: Package, config: Optional["BuildConfig"] = None) -> bool:
        """
        Build the Visual Studio project using MSBuild.

        Args:
            package: Package to build

        Returns:
            True if build succeeded, False otherwise
        """
        # Find project file
        project_file = package.metadata.get('project_file', self._find_project_file(package.path))
        if not project_file:
            print(f"[msbuild] No project or solution file found in {package.path}")
            return False

        # Determine configuration and platform
        build_type = config.build_type if config else self.config.config.build_type
        build_type_value = build_type.value if hasattr(build_type, "value") else str(build_type)
        build_config = self._get_configuration_from_build_type(build_type_value)
        platform = self._get_platform_from_config(config)

        dry_run = bool(self.config.custom.get("dry_run"))
        if dry_run:
            return self._dry_run_project(project_file, build_config, platform, package)

        use_msbuild = bool(self.config.custom.get("use_msbuild"))
        if project_file.lower().endswith('.vcxproj') and not use_msbuild:
            return self._build_vcxproj_direct(project_file, build_config, platform, package)
        if project_file.lower().endswith('.sln') and not use_msbuild:
            return self._build_solution_direct_msvc(project_file, build_config, platform, package)

        plans = []
        if not self.config.config.verbose:
            if project_file.lower().endswith('.sln'):
                projects = self._extract_solution_projects(project_file)
                for proj in projects:
                    if proj.lower().endswith('.vcxproj'):
                        plans.append(self._parse_vcxproj(proj, build_config, platform))
            elif project_file.lower().endswith('.vcxproj'):
                plans.append(self._parse_vcxproj(project_file, build_config, platform))

            for plan in plans:
                for src in plan.get("sources", []):
                    print(os.path.basename(src))

        if not self.msbuild_cmd:
            print("[msbuild] MSBuild executable not found. Please install Visual Studio or build tools.")
            return False

        # Build command arguments
        jobs = 0
        if config and getattr(config, "jobs", 0) > 0:
            jobs = config.jobs
        elif self.config.config.jobs > 0:
            jobs = self.config.config.jobs
        else:
            jobs = os.cpu_count() or 4
        msbuild_args = [
            self.msbuild_cmd,
            project_file,
            f'/p:Configuration={build_config}',
            f'/p:Platform={platform}',
            f'/m:{jobs}',  # equivalent to -j for parallel builds
        ]

        # Add verbosity if requested
        if self.config.config.verbose:
            msbuild_args.append('/v:detailed')
        else:
            msbuild_args.append('/v:minimal')

        # Add any custom properties from config
        custom_props = self.config.custom.get('msbuild_properties', [])
        for prop in custom_props:
            msbuild_args.append(f'/p:{prop}')

        vc_targets = self._find_vc_targets_path()
        if vc_targets:
            msbuild_args.append(f'/p:VCTargetsPath={vc_targets}')

        has_toolset = any(prop.lower().startswith("platformtoolset=") for prop in custom_props)
        toolset_override = self.config.custom.get('platform_toolset')
        if toolset_override:
            msbuild_args.append(f'/p:PlatformToolset={toolset_override}')
            has_toolset = True

        if vc_targets and not has_toolset:
            toolset = self._find_platform_toolset(vc_targets, platform)
            if toolset:
                msbuild_args.append(f'/p:PlatformToolset={toolset}')

        # Execute the build
        if self.config.config.verbose:
            print(f"[msbuild] Building {package.name} with command: {' '.join(msbuild_args)}")
        try:
            result = subprocess.run(
                msbuild_args,
                cwd=os.path.dirname(project_file),
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            output_paths = []
            for plan in plans:
                output = plan.get("output")
                if output and "$(" not in output:
                    output_paths.append(output)

            existing_outputs = [out for out in output_paths if os.path.exists(out)]
            if output_paths and not existing_outputs:
                print(f"[msbuild] Build finished but outputs not found for {package.name}")
                return False

            if not self.config.config.verbose:
                for output in existing_outputs:
                    print(output)
            else:
                if output_paths and not existing_outputs:
                    print(f"[msbuild] Warning: expected outputs missing for {package.name}")
                print(f"[msbuild] Build succeeded for {package.name}")
            return True
        except subprocess.CalledProcessError as e:
            stderr = e.stderr or ""
            stdout = e.stdout or ""
            if stdout.strip():
                print(stdout)
            if stderr.strip():
                print(stderr)
            if not stdout.strip() and not stderr.strip():
                print(f"[msbuild] Build failed for {package.name}: return code {e.returncode}")
            return False
        except Exception as e:
            print(f"[msbuild] Unexpected error building {package.name}: {str(e)}")
            return False

    def _resolve_source_path(self, raw_path: str, project_dir: str, variables: Dict[str, str]) -> str:
        expanded = self._expand_msbuild_vars(raw_path, variables)
        if "$(" in expanded:
            return expanded
        if os.path.isabs(expanded):
            return os.path.normpath(expanded)
        return os.path.normpath(os.path.join(project_dir, expanded))

    def _merge_list_setting(self, base_value: str, override_value: str, variables: Dict[str, str],
                            project_dir: str, as_paths: bool) -> List[str]:
        combined: List[str] = []
        if base_value:
            combined.extend(self._split_msbuild_list(self._expand_msbuild_vars(base_value, variables)))
        if override_value:
            combined.extend(self._split_msbuild_list(self._expand_msbuild_vars(override_value, variables)))

        expanded: List[str] = []
        for value in combined:
            if not as_paths:
                expanded.append(value)
                continue
            if "$(" in value:
                expanded.append(value)
            elif os.path.isabs(value):
                expanded.append(os.path.normpath(value))
            else:
                expanded.append(os.path.normpath(os.path.join(project_dir, value)))
        return expanded

    def _build_vcxproj_direct(self, project_file: str, build_config: str, platform: str,
                              package: Package) -> bool:
        repo_root = self._find_repo_root(package.path)
        vcpkg_root = self._resolve_vcpkg_root(repo_root)
        if vcpkg_root and not self._is_valid_vcpkg_root(os.environ.get("VCPKG_ROOT")):
            os.environ["VCPKG_ROOT"] = vcpkg_root

        plan = self._parse_vcxproj(project_file, build_config, platform)
        project_dir = plan["project_dir"]
        variables = plan["variables"]

        compiler = self.config.compiler.cxx or self.config.compiler.cc or "cl.exe"
        if not self._is_msc(compiler):
            print("[msbuild] MSVC compiler not configured; expected cl.exe for direct build.")
            return False
        linker = self._get_msc_linker(compiler)

        int_dir = plan.get("int_dir")
        if not int_dir or "$(" in int_dir:
            int_dir = os.path.join(project_dir, f"{build_config}{os.sep}")
        out_dir = plan.get("out_dir")
        if not out_dir or "$(" in out_dir:
            out_dir = os.path.dirname(plan.get("output") or "") or project_dir

        os.makedirs(int_dir, exist_ok=True)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        cl_settings = plan.get("cl_settings", {})
        link_settings = plan.get("link_settings", {})
        rc_settings = plan.get("rc_settings", {})

        default_includes = plan.get("include_dirs", [])
        default_defines = plan.get("defines", [])
        default_lib_dirs = plan.get("library_dirs", [])
        default_libs = plan.get("libraries", [])

        base_cl_flags = self._msvc_flags_from_cl_settings(cl_settings)
        base_link_flags = self._msvc_flags_from_link_settings(link_settings, variables, project_dir)

        method_includes = list(self.config.compiler.includes or [])
        method_defines = list(self.config.compiler.defines or [])
        method_cxxflags = self._normalize_msvc_flags_for_cl(self.config.compiler.cxxflags or [])
        method_cflags = self._normalize_msvc_flags_for_cl(self.config.compiler.cflags or [])
        method_ldflags = self._normalize_msvc_flags_for_link(self.config.compiler.ldflags or [])

        if build_config.lower() != "debug":
            method_defines = [
                define for define in method_defines
                if define not in ("_DEBUG", "DEBUG", "flagDEBUG", "flagDEBUG_FULL")
            ]

        compile_items = plan.get("compile_items", [])
        resource_items = plan.get("resource_items", [])

        pch_create_items = []
        other_items = []

        for item in compile_items:
            pch_mode = item.get("PrecompiledHeader", cl_settings.get("PrecompiledHeader", ""))
            if pch_mode.lower() == "create":
                pch_create_items.append(item)
            else:
                other_items.append(item)

        obj_files: List[str] = []
        res_files: List[str] = []

        env = os.environ.copy()
        need_vsdevcmd = self.config.custom.get("use_vsdevcmd")
        if need_vsdevcmd is None:
            need_vsdevcmd = not (env.get("INCLUDE") and env.get("LIB"))
            if not need_vsdevcmd and not self._compiler_on_path(compiler, env):
                need_vsdevcmd = True
        if need_vsdevcmd:
            vs_env = self._load_vsdevcmd_env(platform)
            if vs_env:
                env = vs_env
                if self.config.config.verbose:
                    print(f"[msbuild] Using VSDevCmd: {self._vsdevcmd_path}")
            elif self.config.config.verbose:
                print("[msbuild] VSDevCmd not found or failed to load.")

        if not os.path.isabs(compiler):
            resolved_compiler = shutil.which(compiler, path=env.get("PATH") or env.get("Path") or "")
            if resolved_compiler:
                compiler = resolved_compiler
                linker = self._get_msc_linker(compiler)

        vs_include_paths = [p for p in env.get("INCLUDE", "").split(";") if p]
        vs_lib_paths = [p for p in env.get("LIB", "").split(";") if p]
        for inc in vs_include_paths:
            if inc not in method_includes:
                method_includes.append(inc)
        for lib in vs_lib_paths:
            flag = f"/LIBPATH:{lib}"
            if flag not in method_ldflags:
                method_ldflags.append(flag)

        rc_exe = self._find_rc_in_env(env)

        def compile_item(item: Dict[str, str]) -> bool:
            source_raw = item.get("Include", "")
            source_path = self._resolve_source_path(source_raw, project_dir, variables)
            if not self.config.config.verbose:
                print(os.path.basename(source_path))

            file_includes = self._merge_list_setting(
                ";".join(default_includes + method_includes),
                item.get("AdditionalIncludeDirectories", ""),
                variables,
                project_dir,
                True
            )
            file_defines = self._merge_list_setting(
                ";".join(default_defines + method_defines),
                item.get("PreprocessorDefinitions", ""),
                variables,
                project_dir,
                False
            )
            additional_options = self._split_msbuild_options(
                self._expand_msbuild_vars(item.get("AdditionalOptions", ""), variables)
            )

            obj_name = item.get("ObjectFileName")
            if obj_name:
                obj_path = self._expand_item_macros(obj_name, source_path, source_raw, project_dir, variables)
            else:
                obj_path = os.path.normpath(os.path.join(int_dir, f"{Path(source_path).stem}.obj"))
            os.makedirs(os.path.dirname(obj_path), exist_ok=True)

            pch_mode = item.get("PrecompiledHeader", cl_settings.get("PrecompiledHeader", ""))
            pch_header = item.get("PrecompiledHeaderFile", cl_settings.get("PrecompiledHeaderFile", ""))
            pch_output_raw = item.get("PrecompiledHeaderOutputFile", cl_settings.get("PrecompiledHeaderOutputFile", ""))
            pch_output = ""
            if pch_output_raw:
                pch_output = self._expand_item_macros(pch_output_raw, source_path, source_raw, project_dir, variables)

            cmd = [compiler]
            cmd.extend(base_cl_flags)
            if os.path.splitext(source_path)[1].lower() == ".c":
                cmd.extend(method_cflags)
            else:
                cmd.extend(method_cxxflags)
            for inc in file_includes:
                cmd.append(self._format_msvc_path_arg("/I", inc))
            for define in file_defines:
                cmd.append(f"/D{define}")
            cmd.extend(additional_options)
            if pch_header:
                if pch_mode.lower() == "create":
                    cmd.append(f"/Yc{pch_header}")
                elif pch_mode.lower() == "use":
                    cmd.append(f"/Yu{pch_header}")
            if pch_output:
                cmd.append(self._format_msvc_path_arg("/Fp", pch_output))
            cmd.append("/c")
            cmd.append(source_path)
            cmd.append(self._format_msvc_path_arg("/Fo", obj_path))

            if self.config.config.verbose:
                print(" ".join(cmd))
            if not self._run_command(cmd, cwd=project_dir, verbose=self.config.config.verbose, env=env):
                return False

            obj_files.append(obj_path)
            return True

        for item in pch_create_items:
            if not compile_item(item):
                return False

        for item in other_items:
            if not compile_item(item):
                return False

        for item in resource_items:
            source_raw = item.get("Include", "")
            source_path = self._resolve_source_path(source_raw, project_dir, variables)
            if not self.config.config.verbose:
                print(os.path.basename(source_path))

            res_name = os.path.splitext(os.path.basename(source_path))[0] + ".res"
            res_path = os.path.normpath(os.path.join(int_dir, res_name))
            os.makedirs(os.path.dirname(res_path), exist_ok=True)

            res_defines = self._merge_list_setting(
                ";".join(default_defines + method_defines + self._split_msbuild_list(rc_settings.get("PreprocessorDefinitions", ""))),
                item.get("PreprocessorDefinitions", ""),
                variables,
                project_dir,
                False
            )
            res_includes = self._merge_list_setting(
                ";".join(default_includes + method_includes + self._split_msbuild_list(rc_settings.get("AdditionalIncludeDirectories", ""))),
                item.get("AdditionalIncludeDirectories", ""),
                variables,
                project_dir,
                True
            )
            cmd = [rc_exe, self._format_msvc_path_arg("/fo", res_path)]
            for inc in res_includes:
                cmd.append(self._format_msvc_path_arg("/i", inc))
            for define in res_defines:
                cmd.append(f"/d{define}")
            cmd.append(source_path)

            if self.config.config.verbose:
                print(" ".join(cmd))
            if not self._run_command(cmd, cwd=project_dir, verbose=self.config.config.verbose, env=env):
                return False
            res_files.append(res_path)

        output_path = plan.get("output")
        if not output_path:
            print("[msbuild] No output file resolved for direct build.")
            return False
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        link_args = [linker]
        link_args.extend(obj_files)
        link_args.extend(res_files)
        link_args.append(self._format_msvc_path_arg("/OUT:", output_path))
        link_args.extend(base_link_flags)
        link_args.extend(method_ldflags)

        for lib_dir in default_lib_dirs:
            link_args.append(self._format_msvc_path_arg("/LIBPATH:", lib_dir))
        libs_to_link = list(default_libs)
        if plan.get("uses_default_libs"):
            for lib in self._DEFAULT_MSVC_LIBS:
                if lib not in libs_to_link:
                    libs_to_link.append(lib)
        link_args.extend(libs_to_link)

        if self.config.config.verbose:
            print(" ".join(link_args))
        if not self._run_command(link_args, cwd=project_dir, verbose=self.config.config.verbose, env=env):
            return False

        if not os.path.exists(output_path):
            print(f"[msbuild] Build finished but output not found: {output_path}")
            return False
        if self.config.config.verbose:
            print(f"[msbuild] Build succeeded for {package.name}")
            print(output_path)
        else:
            print(output_path)
        return True

    def _build_solution_direct_msvc(self, solution_file: str, build_config: str, platform: str,
                                    package: Package) -> bool:
        projects = self._extract_solution_projects(solution_file)
        if not projects:
            print(f"[msbuild] No projects found in solution {solution_file}")
            return False
        for project_file in projects:
            if not project_file.lower().endswith(".vcxproj"):
                continue
            if not self._build_vcxproj_direct(project_file, build_config, platform, package):
                return False
        return True

    def _dry_run_project(self, project_file: str, build_config: str, platform: str, package: Package) -> bool:
        repo_root = None
        if package.metadata:
            repo_root = package.metadata.get('repo_root')
        if not repo_root:
            repo_root = self._find_repo_root(package.path)

        print(f"[msbuild] Dry-run {os.path.basename(project_file)} ({build_config}|{platform})")
        if project_file.lower().endswith('.sln'):
            projects = self._extract_solution_projects(project_file)
            if not projects:
                print(f"[msbuild] No projects found in solution {project_file}")
                return False
            for proj in projects:
                if not proj.lower().endswith('.vcxproj'):
                    continue
                print(f"[msbuild] project: {os.path.basename(proj)}")
                plan = self._parse_vcxproj(proj, build_config, platform)
                self._print_dry_run_plan(plan, repo_root)
            return True

        if project_file.lower().endswith('.vcxproj'):
            plan = self._parse_vcxproj(project_file, build_config, platform)
            self._print_dry_run_plan(plan, repo_root)
            return True

        print(f"[msbuild] Dry-run not supported for project file: {project_file}")
        return False

    def build_solution(self, solution_file: str) -> bool:
        """
        Build all projects in a Visual Studio solution with proper dependency ordering.

        Args:
            solution_file: Path to the solution file (.sln)

        Returns:
            True if build succeeded, False otherwise
        """
        if not self.msbuild_cmd:
            print("[msbuild] MSBuild executable not found. Cannot build solution.")
            return False

        # Extract project dependencies from solution
        solution_projects = self._extract_solution_projects(solution_file)

        if not solution_projects:
            print(f"[msbuild] No projects found in solution {solution_file}")
            # Fall back to building the solution directly
            return self._build_solution_direct(solution_file)

        print(f"[msbuild] Building solution {solution_file} with {len(solution_projects)} projects")

        # Build each project in the solution
        for project_file in solution_projects:
            print(f"[msbuild] Building project: {project_file}")
            # Create a temporary package for this project
            project_package = Package(
                name=Path(project_file).stem,
                path=str(Path(project_file).parent),
                metadata={'project_file': project_file}
            )

            if not self.build_package(project_package):
                print(f"[msbuild] Failed to build project {project_file}")
                return False

        print(f"[msbuild] Solution build completed successfully")
        return True

    def _build_solution_direct(self, solution_file: str) -> bool:
        """
        Build a solution file directly using MSBuild.

        Args:
            solution_file: Path to the solution file (.sln)

        Returns:
            True if build succeeded, False otherwise
        """
        if not self.msbuild_cmd:
            return False

        build_config = self._get_configuration_from_build_type(self.config.config.build_type.value)
        platform = self._get_platform_from_config()

        # Build command arguments for solution
        jobs = self.config.config.jobs if self.config.config.jobs > 0 else os.cpu_count() or 4
        msbuild_args = [
            self.msbuild_cmd,
            solution_file,
            f'/p:Configuration={build_config}',
            f'/p:Platform={platform}',
            f'/m:{jobs}',
        ]

        if self.config.config.verbose:
            msbuild_args.append('/v:minimal')

        try:
            result = subprocess.run(
                msbuild_args,
                cwd=os.path.dirname(solution_file),
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def link(self, linkfiles: List[str], linkoptions: Dict[str, Any]) -> bool:
        """
        Link final executable/library using MSBuild.

        Args:
            linkfiles: List of files to link
            linkoptions: Linker options

        Returns:
            True if linking succeeded, False otherwise
        """
        # For MSBuild, linking is part of the build process
        # This method exists for interface compatibility
        print("[msbuild] Linking is handled during build process")
        return True

    def clean_package(self, package: Package, config: Optional["BuildConfig"] = None) -> bool:
        """
        Clean package build artifacts using MSBuild.

        Args:
            package: Package to clean

        Returns:
            True if clean succeeded, False otherwise
        """
        use_msbuild = bool(self.config.custom.get("use_msbuild"))

        # Find project file
        project_file = package.metadata.get('project_file', self._find_project_file(package.path))
        if not project_file:
            print(f"[msbuild] No project or solution file found in {package.path}")
            return False

        build_type = config.build_type if config else BuildConfig().build_type
        build_type_value = build_type.value if hasattr(build_type, "value") else str(build_type)
        build_config = self._get_configuration_from_build_type(build_type_value)
        platform = self._get_platform_from_config(config or BuildConfig())

        if project_file.lower().endswith(".vcxproj") and not use_msbuild:
            return self._clean_vcxproj_direct(project_file, build_config, platform)
        if project_file.lower().endswith(".sln") and not use_msbuild:
            projects = self._extract_solution_projects(project_file)
            ok = True
            for proj in projects:
                if proj.lower().endswith(".vcxproj"):
                    ok = self._clean_vcxproj_direct(proj, build_config, platform) and ok
            return ok

        if not self.msbuild_cmd:
            print("[msbuild] MSBuild executable not found. Cannot clean.")
            return False

        # Clean command arguments
        msbuild_args = [
            self.msbuild_cmd,
            project_file,
            '/t:Clean',  # Clean target
            f'/p:Configuration={build_config}',
            f'/p:Platform={platform}',
        ]

        print(f"[msbuild] Cleaning {package.name} with command: {' '.join(msbuild_args)}")
        try:
            result = subprocess.run(
                msbuild_args,
                cwd=os.path.dirname(project_file),
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print(f"[msbuild] Clean succeeded for {package.name}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[msbuild] Clean failed for {package.name}: {e.stderr}")
            return False
        except Exception as e:
            print(f"[msbuild] Unexpected error cleaning {package.name}: {str(e)}")
            return False

    def _clean_vcxproj_direct(self, project_file: str, build_config: str, platform: str) -> bool:
        plan = self._parse_vcxproj(project_file, build_config, platform)
        int_dir = plan.get("int_dir")
        output_path = plan.get("output")
        removed_any = False

        if int_dir and "$(" not in int_dir and os.path.isdir(int_dir):
            import shutil
            shutil.rmtree(int_dir, ignore_errors=True)
            removed_any = True

        if output_path and "$(" not in output_path and os.path.exists(output_path):
            try:
                os.remove(output_path)
                removed_any = True
            except OSError:
                pass

        return True

    def get_target_ext(self) -> str:
        """
        Return target file extension based on platform.

        Returns:
            String with appropriate file extension
        """
        # On Windows, executables end with .exe, libraries with .dll or .lib
        # For simplicity, return .exe as the primary executable extension
        return ".exe"

    def install(self, package: Package, config: Optional["BuildConfig"] = None) -> bool:
        """
        Install the built package by copying output files to destination.
        For MSBuild projects, this typically involves copying built binaries
        from the output directory to the configured install prefix.

        Args:
            package: Package to install

        Returns:
            True if install succeeded, False otherwise
        """
        if not self.msbuild_cmd:
            print("[msbuild] MSBuild executable not found. Cannot install.")
            return False

        # Find project file
        project_file = package.metadata.get('project_file', self._find_project_file(package.path))
        if not project_file:
            print(f"[msbuild] No project file found for {package.name}")
            return False

        # Determine configuration and platform for output path
        build_type = config.build_type if config else self.config.config.build_type
        build_type_value = build_type.value if hasattr(build_type, "value") else str(build_type)
        build_config = self._get_configuration_from_build_type(build_type_value)
        platform = self._get_platform_from_config(config)

        # Determine the output directory based on project type and config
        project_dir = Path(project_file).parent
        output_patterns = [
            project_dir / build_config,  # Classic MSBuild output format
            project_dir / f"{platform}/{build_config}",  # Platform-specific output
            project_dir / f"bin/{build_config}",  # Alternative bin structure
            project_dir / f"bin/{platform}/{build_config}"  # Full path structure
        ]

        # Find the output directory that exists
        output_dir = None
        for pattern in output_patterns:
            if pattern.exists():
                output_dir = pattern
                break

        if not output_dir:
            print(f"[msbuild] Output directory not found for {package.name}, attempting to build first...")
            # Try to run a build to generate the outputs
            if not self.build_package(package, config):
                print(f"[msbuild] Build failed, cannot proceed with install for {package.name}")
                return False
            # Re-check for output directory after build
            for pattern in output_patterns:
                if pattern.exists():
                    output_dir = pattern
                    break
            if not output_dir:
                print(f"[msbuild] Output directory still not found after build for {package.name}")
                return False

        # Destination directory
        install_prefix = config.install_prefix if config else self.config.config.install_prefix
        install_dir = Path(install_prefix) / package.name
        install_dir.mkdir(parents=True, exist_ok=True)

        # Copy built files to install location
        import shutil

        print(f"[msbuild] Installing {package.name} from {output_dir} to {install_dir}")

        # Copy all relevant output files (executables, DLLs, etc.)
        for file_path in output_dir.iterdir():
            if file_path.is_file():
                # Only copy certain file types that are typically output files
                if file_path.suffix.lower() in ['.exe', '.dll', '.lib', '.pdb', '.ilk', '.exp']:
                    dest_path = install_dir / file_path.name
                    shutil.copy2(file_path, dest_path)
                    print(f"[msbuild] Copied {file_path.name} to {dest_path}")

        print(f"[msbuild] Install completed for {package.name}")
        return True

    def rebuild_package(self, package: Package, config: Optional["BuildConfig"] = None) -> bool:
        """
        Rebuild the package (clean + build).

        Args:
            package: Package to rebuild

        Returns:
            True if rebuild succeeded, False otherwise
        """
        print(f"[msbuild] Rebuilding {package.name}...")
        if not self.clean_package(package, config):
            print(f"[msbuild] Clean failed during rebuild for {package.name}")
            return False
        return self.build_package(package, config)
