"""
Makefile Builder Implementation

Parses Makefile scan metadata and performs an internal build without invoking make.
"""

import os
import subprocess
from typing import List, Dict, Any, Optional
import ctypes.util

from .base import Builder, Package
from .config import MethodConfig, OSFamily
from .console import execute_command, parallel_execute


def _expand_shell_tokens(tokens: List[str], cwd: str, verbose: bool) -> List[str]:
    expanded: List[str] = []
    for token in tokens:
        if token.startswith('`') and token.endswith('`'):
            cmd = token[1:-1].strip()
            try:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if result.returncode != 0:
                    if verbose and result.stderr:
                        print(result.stderr)
                    continue
                expanded.extend(result.stdout.strip().split())
            except Exception as exc:
                if verbose:
                    print(f"Error executing shell token '{cmd}': {exc}")
        else:
            expanded.append(token)
    return expanded


def _select_tokens(variables: Dict[str, List[str]], name: str, cwd: str, verbose: bool) -> List[str]:
    return _expand_shell_tokens(variables.get(name, []), cwd, verbose)


def _resolve_source_path(source: str, package_dir: str, repo_root: Optional[str]) -> str:
    if os.path.isabs(source):
        return source
    candidate = os.path.join(package_dir, source)
    if os.path.exists(candidate):
        return candidate
    if repo_root:
        repo_candidate = os.path.join(repo_root, source)
        if os.path.exists(repo_candidate):
            return repo_candidate
    return candidate


def _is_compiler_token(token: str) -> bool:
    if not token:
        return False
    if token.startswith('-') or token.startswith('$'):
        return False
    return True


def _collect_include_dirs(flags: List[str], package_dir: str, repo_root: Optional[str]) -> List[str]:
    include_dirs: List[str] = []
    idx = 0
    while idx < len(flags):
        token = flags[idx]
        if token in ("-I", "-isystem"):
            if idx + 1 < len(flags):
                include_dirs.append(flags[idx + 1])
                idx += 2
                continue
        elif token.startswith("-I") and len(token) > 2:
            include_dirs.append(token[2:])
        idx += 1

    resolved: List[str] = []
    for path in include_dirs:
        if os.path.isabs(path):
            resolved.append(path)
            continue
        candidate = os.path.normpath(os.path.join(package_dir, path))
        if os.path.exists(candidate):
            resolved.append(candidate)
            continue
        if repo_root:
            repo_candidate = os.path.normpath(os.path.join(repo_root, path))
            if os.path.exists(repo_candidate):
                resolved.append(repo_candidate)
                continue
        resolved.append(path)
    return resolved


def _header_exists(header: str, include_dirs: List[str]) -> bool:
    for inc in include_dirs:
        candidate = os.path.join(inc, header)
        if os.path.exists(candidate):
            return True
    return False


def _build_enet_library(enet_dir: str, build_dir: str, compiler: str, ar_tool: str,
                        cflags: List[str], verbose: bool, platform: OSFamily) -> Optional[str]:
    if not os.path.isdir(enet_dir):
        return None

    sources = [
        "callbacks.c",
        "compress.c",
        "host.c",
        "list.c",
        "packet.c",
        "peer.c",
        "protocol.c",
    ]
    if platform == OSFamily.WINDOWS:
        sources.append("win32.c")
    else:
        sources.append("unix.c")

    build_path = os.path.join(build_dir, "enet")
    os.makedirs(build_path, exist_ok=True)

    obj_files: List[str] = []
    for src in sources:
        src_path = os.path.join(enet_dir, src)
        if not os.path.exists(src_path):
            continue
        obj_path = os.path.join(build_path, os.path.splitext(src)[0] + ".o")
        cmd = [compiler] + cflags + ["-c", src_path, "-o", obj_path]
        if not execute_command(cmd, cwd=enet_dir, verbose=verbose):
            return None
        obj_files.append(obj_path)

    if not obj_files:
        return None

    lib_path = os.path.join(build_path, "libenet.a")
    ar_cmd = [ar_tool, "rcs", lib_path] + obj_files
    if not execute_command(ar_cmd, cwd=enet_dir, verbose=verbose):
        return None

    return lib_path


class MakefileBuilder(Builder):
    """Makefile builder implementation (internal, no make invocation)."""

    def __init__(self, config: MethodConfig = None):
        super().__init__("makefile", config)

    def build_package(self, package: Package, method_config: Optional[MethodConfig] = None, verbose: bool = False) -> bool:
        if method_config is not None:
            self.config = method_config
        dry_run = bool(self.config.custom.get("dry_run"))

        build_config = self.config.config
        variables = package.metadata.get('variables', {}) if package.metadata else {}
        targets = package.metadata.get('targets', []) if package.metadata else []
        repo_root = package.metadata.get('repo_root') if package.metadata else None
        target_dir = build_config.target_dir or ".maestro/build"
        if not os.path.isabs(target_dir):
            if repo_root:
                target_dir = os.path.normpath(os.path.join(repo_root, target_dir))
            else:
                target_dir = os.path.abspath(target_dir)
        build_root = os.path.join(target_dir, package.name)
        os.makedirs(build_root, exist_ok=True)
        if not targets:
            targets = [{
                'name': package.name,
                'sources': package.source_files or [],
                'output': package.name
            }]

        cxx = None
        extra_cxxflags: List[str] = []
        cxx_tokens = variables.get('CXX', [])
        if cxx_tokens and _is_compiler_token(cxx_tokens[0]):
            cxx = cxx_tokens[0]
            extra_cxxflags = cxx_tokens[1:]
        if not cxx:
            cxx = self.config.compiler.cxx or "g++"

        base_cxxflags = _select_tokens(variables, 'CXXFLAGS', package.dir, verbose)
        base_includes = _select_tokens(variables, 'INCLUDES', package.dir, verbose)

        for target in targets:
            target_name = target.get('name', package.name)
            sources = target.get('sources') or package.source_files
            if not sources:
                if verbose:
                    print(f"[makefile] No sources found for target '{target_name}'")
                continue

            if 'client' in target_name:
                include_flags = _select_tokens(variables, 'CLIENT_INCLUDES', package.dir, verbose)
                link_flags = _select_tokens(variables, 'CLIENT_LIBS', package.dir, verbose)
            elif 'master' in target_name:
                include_flags = _select_tokens(variables, 'SERVER_INCLUDES', package.dir, verbose)
                link_flags = _select_tokens(variables, 'MASTER_LIBS', package.dir, verbose)
            elif 'server' in target_name:
                include_flags = _select_tokens(variables, 'SERVER_INCLUDES', package.dir, verbose)
                link_flags = _select_tokens(variables, 'SERVER_LIBS', package.dir, verbose)
            else:
                include_flags = []
                link_flags = []

            cxxflags = extra_cxxflags + base_cxxflags + base_includes + include_flags
            include_dirs = _collect_include_dirs(cxxflags, package.dir, repo_root)

            if target_name == 'tessfont' and not _header_exists('ft2build.h', include_dirs):
                if verbose:
                    print("[makefile] Skipping tessfont target (missing freetype headers).")
                continue

            if 'client' in target_name and not _header_exists('SDL_mixer.h', include_dirs):
                include_hint = os.path.join(package.dir, "include", "SDL_mixer.h")
                if os.path.exists(include_hint):
                    include_flags = include_flags + ["-Iinclude"]
                    cxxflags = extra_cxxflags + base_cxxflags + base_includes + include_flags
                    include_dirs = _collect_include_dirs(cxxflags, package.dir, repo_root)
                if not _header_exists('SDL_mixer.h', include_dirs):
                    if verbose:
                        print("[makefile] Skipping client target (missing SDL_mixer headers).")
                    continue

            obj_files = []
            compile_cmds: List[List[str]] = []
            compile_sources: List[str] = []
            for src in sources:
                abs_src = _resolve_source_path(src, package.dir, repo_root)
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

            output_name = target.get('output') or target_name
            if self.config.platform.os == OSFamily.WINDOWS and not output_name.endswith('.exe'):
                output_name += '.exe'
            output_path = os.path.join(build_root, output_name)

            if dry_run:
                print(output_path)
                continue

            if build_config.parallel and len(compile_cmds) > 1:
                max_jobs = build_config.jobs or os.cpu_count() or 4
                results = parallel_execute(compile_cmds, max_jobs=max_jobs, cwd=package.dir)
                if not all(results):
                    return False
            else:
                for cmd in compile_cmds:
                    if not execute_command(cmd, cwd=package.dir, verbose=verbose):
                        return False

            if 'client' in target_name and any(flag == "-lenet" for flag in link_flags):
                enet_dir = os.path.join(package.dir, "enet")
                enet_cflags = ["-O3", "-fomit-frame-pointer", "-Iinclude"]
                ar_tool = os.environ.get("AR", "ar")
                enet_lib = _build_enet_library(
                    enet_dir,
                    build_root,
                    self.config.compiler.cc or self.config.compiler.cxx or "gcc",
                    ar_tool,
                    enet_cflags,
                    verbose,
                    self.config.platform.os
                )
                if enet_lib:
                    link_flags = [f for f in link_flags if not f.startswith("-L")]
                    link_flags = link_flags + [f"-L{os.path.dirname(enet_lib)}", "-lenet"]
                else:
                    if verbose:
                        print("[makefile] Failed to build enet library; skipping client target.")
                    continue

            if 'client' in target_name:
                needs_sdl_mixer = any(flag == "-lSDL2_mixer" for flag in link_flags)
                if needs_sdl_mixer and not ctypes.util.find_library("SDL2_mixer"):
                    if verbose:
                        print("[makefile] SDL2_mixer not found; linking with unresolved symbols allowed.")
                    link_flags = [f for f in link_flags if f != "-lSDL2_mixer"]
                    link_flags = link_flags + ["-Wl,--unresolved-symbols=ignore-all"]

            link_cmd = [cxx] + obj_files + link_flags + ["-o", output_path]
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
