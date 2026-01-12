"""
GCC/Clang Builder Implementation

This builder implements the GCC/Clang build system following U++ GccBuilder logic.
"""

from .base import Builder, Package
from .config import MethodConfig, OSFamily
from .console import execute_command, parallel_execute
from typing import List, Dict, Any, Optional
import os


class GccBuilder(Builder):
    """GCC/Clang builder implementation."""

    def __init__(self, config: MethodConfig = None):
        super().__init__("gcc", config)

    def build_package(self, package: Package, method_config: Optional[MethodConfig] = None, verbose: bool = False) -> bool:
        if isinstance(package, dict):
            package = Package(
                name=package.get('name', 'unknown'),
                directory=package.get('dir', package.get('directory', '')),
                build_system=package.get('build_system', 'gcc'),
                source_files=package.get('files', package.get('source_files', [])),
                dependencies=package.get('dependencies', []),
                metadata=package.get('metadata', {})
            )

        if method_config is not None:
            self.config = method_config

        build_config = self.config.config
        target_dir = build_config.target_dir or ".maestro/build"
        build_root = os.path.join(target_dir, package.name)
        os.makedirs(build_root, exist_ok=True)

        cxx = self.config.compiler.cxx or "g++"
        cxxflags = self.config.compiler.cxxflags[:]
        ldflags = self.config.compiler.ldflags[:]

        metadata = package.metadata or {}
        repo_root = metadata.get('repo_root')
        cxxflags.extend(metadata.get('cxxflags', []))
        include_flags = metadata.get('includes', [])
        if include_flags:
            cxxflags.extend(include_flags)
        ldflags.extend(metadata.get('ldflags', []))

        sources = package.source_files
        if not sources:
            if verbose:
                print(f"[gcc] No source files found for package '{package.name}'")
            return True

        obj_files: List[str] = []
        compile_cmds: List[List[str]] = []
        compile_sources: List[str] = []
        for src in sources:
            if os.path.isabs(src):
                abs_src = src
            else:
                abs_src = os.path.join(package.dir, src)
                if repo_root and not os.path.exists(abs_src):
                    abs_src = os.path.join(repo_root, src)
            rel_obj = os.path.splitext(src)[0] + ".o"
            obj_path = os.path.join(build_root, rel_obj.replace('/', os.sep))
            os.makedirs(os.path.dirname(obj_path), exist_ok=True)
            cmd = [cxx] + cxxflags + ["-c", abs_src, "-o", obj_path]
            compile_cmds.append(cmd)
            obj_files.append(obj_path)
            compile_sources.append(abs_src)

        for abs_src in compile_sources:
            if repo_root:
                display_src = os.path.relpath(abs_src, repo_root)
            else:
                display_src = os.path.relpath(abs_src, package.dir)
            print(display_src)

        if build_config.parallel and len(compile_cmds) > 1:
            max_jobs = build_config.jobs or os.cpu_count() or 4
            results = parallel_execute(compile_cmds, max_jobs=max_jobs, cwd=package.dir)
            if not all(results):
                return False
        else:
            for cmd in compile_cmds:
                if not execute_command(cmd, cwd=package.dir, verbose=verbose):
                    return False

        output_name = metadata.get('output', package.name)
        if self.config.platform.os == OSFamily.WINDOWS and not output_name.endswith('.exe'):
            output_name += '.exe'
        output_path = os.path.join(build_root, output_name)

        link_cmd = [cxx] + obj_files + ldflags + ["-o", output_path]
        if not execute_command(link_cmd, cwd=package.dir, verbose=verbose):
            return False
        print(output_path)
        return True

    def link(self, linkfiles: List[str], linkoptions: Dict[str, Any]) -> bool:
        return True

    def clean_package(self, package: Package) -> bool:
        target_dir = self.config.config.target_dir or ".maestro/build"
        build_root = os.path.join(target_dir, package.name)
        if os.path.isdir(build_root):
            for root, dirs, files in os.walk(build_root):
                for filename in files:
                    os.remove(os.path.join(root, filename))
        return True

    def get_target_ext(self) -> str:
        return ".exe" if self.config.platform.os == OSFamily.WINDOWS else ""
