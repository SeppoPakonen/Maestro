from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from maestro.builders.config import MethodManager
from maestro.issues.issue_store import IssueDetails, write_issue
from maestro.repo.upp_parser import UppParser


class RunCommand:
    """Execute built binaries with optional profiling and issue capture."""

    def __init__(self) -> None:
        self.method_manager = MethodManager()

    def execute(self, args: argparse.Namespace) -> int:
        if args.list or not args.package:
            return self.list_packages(args)
        return self.run_package(args)

    def list_packages(self, args: argparse.Namespace) -> int:
        repo_root = self._find_repo_root() or os.getcwd()
        packages = self._load_repo_packages(repo_root)
        if not packages:
            print("No packages found. Run `maestro repo resolve` first.")
            return 1

        print("Packages:")
        for pkg in packages:
            mainconfigs = self._get_mainconfigs(pkg)
            status = self._build_status(pkg, args)
            mainconfigs_display = ", ".join(mainconfigs) if mainconfigs else "default"
            print(f"- {pkg['name']} [{pkg.get('build_system', 'unknown')}] ({status})")
            print(f"  mainconfigs: {mainconfigs_display}")
        return 0

    def run_package(self, args: argparse.Namespace) -> int:
        repo_root = self._find_repo_root() or os.getcwd()
        packages = self._load_repo_packages(repo_root)
        package = self._find_package(packages, args.package)
        if not package:
            print(f"Error: Package '{args.package}' not found in repo.")
            return 1

        mainconfig = args.mainconfig or ""
        if mainconfig and not self._is_mainconfig_known(package, mainconfig):
            print(f"Warning: mainconfig '{mainconfig}' not found in .upp; continuing anyway.")

        binary_path = self._locate_binary(repo_root, package, args)
        if not binary_path:
            print("Error: No executable output found. Build first with `maestro make build`.")
            return 1

        run_args = list(args.args or [])
        if run_args and run_args[0] == "--":
            run_args = run_args[1:]

        exit_code, stdout, stderr = self._run_with_profile(binary_path, run_args, args, package, repo_root)

        if stdout:
            print(stdout, end="" if stdout.endswith("\n") else "\n")
        if stderr:
            print(stderr, end="" if stderr.endswith("\n") else "\n")
        print(f"Exit code: {exit_code}")

        if exit_code != 0:
            self._create_runtime_issue(repo_root, package, mainconfig, binary_path, exit_code, stdout, stderr)
            return exit_code if exit_code > 0 else 1

        return 0

    def _run_with_profile(
        self,
        binary_path: str,
        run_args: List[str],
        args: argparse.Namespace,
        package: Dict[str, Any],
        repo_root: str,
    ) -> Tuple[int, str, str]:
        profile = args.profile
        if not profile:
            return self._execute(binary_path, run_args, args)

        if profile == "gprof":
            if not shutil.which("gprof"):
                print("Warning: gprof not found; running without profiling.")
                return self._execute(binary_path, run_args, args)
            exit_code, stdout, stderr = self._execute(binary_path, run_args, args, extra_env={"GMON_OUT_PREFIX": "gmon"})
            gprof_output = self._run_tool(["gprof", binary_path], repo_root)
            self._write_profile_report(package["name"], profile, gprof_output, repo_root)
            return exit_code, stdout, stderr

        if profile == "valgrind":
            if not shutil.which("valgrind"):
                print("Warning: valgrind not found; running without profiling.")
                return self._execute(binary_path, run_args, args)
            cmd = ["valgrind", "--tool=callgrind", "--callgrind-out-file=callgrind.out", binary_path] + run_args
            exit_code, stdout, stderr = self._execute_command(cmd, args)
            self._write_profile_report(package["name"], profile, stdout + stderr, repo_root)
            return exit_code, stdout, stderr

        if profile == "perf":
            if not shutil.which("perf"):
                print("Warning: perf not found; running without profiling.")
                return self._execute(binary_path, run_args, args)
            record_cmd = ["perf", "record", "-o", "perf.data", "--", binary_path] + run_args
            exit_code, stdout, stderr = self._execute_command(record_cmd, args)
            report_output = self._run_tool(["perf", "report", "--stdio", "-i", "perf.data"], repo_root)
            self._write_profile_report(package["name"], profile, report_output, repo_root)
            return exit_code, stdout, stderr

        if profile == "cprofile":
            if binary_path.endswith(".py"):
                cmd = ["python", "-m", "cProfile", binary_path] + run_args
                exit_code, stdout, stderr = self._execute_command(cmd, args)
                self._write_profile_report(package["name"], profile, stdout + stderr, repo_root)
                return exit_code, stdout, stderr
            print("Warning: cprofile requires a Python script target.")
            return self._execute(binary_path, run_args, args)

        if profile in ("visualvm", "yourkit"):
            note = (
                f"{profile} profiling requested. Launch the profiler and attach to the process "
                "if auto-attach is not configured."
            )
            print(note)
            exit_code, stdout, stderr = self._execute(binary_path, run_args, args)
            self._write_profile_report(package["name"], profile, note, repo_root)
            return exit_code, stdout, stderr

        print(f"Warning: Unsupported profiler '{profile}', running without profiling.")
        return self._execute(binary_path, run_args, args)

    def _execute(self, binary_path: str, run_args: List[str], args: argparse.Namespace,
                 extra_env: Optional[Dict[str, str]] = None) -> Tuple[int, str, str]:
        cmd = [binary_path] + run_args
        return self._execute_command(cmd, args, extra_env=extra_env)

    def _execute_command(
        self,
        cmd: List[str],
        args: argparse.Namespace,
        extra_env: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, str, str]:
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=args.cwd)
        return result.returncode, result.stdout or "", result.stderr or ""

    def _run_tool(self, cmd: List[str], repo_root: str) -> str:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=repo_root)
        output = (result.stdout or "") + (result.stderr or "")
        return output.strip()

    def _write_profile_report(self, package_name: str, profile: str, output: str, repo_root: str) -> None:
        profiling_dir = os.path.join(repo_root, "docs", "profiling")
        os.makedirs(profiling_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        report_path = os.path.join(profiling_dir, f"{package_name}-{profile}-{timestamp}.md")
        content = "\n".join(
            [
                f"# Profiling Report: {package_name}",
                "",
                f"\"tool\": \"{profile}\"",
                f"\"generated_at\": \"{time.strftime('%Y-%m-%dT%H:%M:%S')}\"",
                "",
                "## Output",
                "```",
                output.strip(),
                "```",
                "",
            ]
        )
        with open(report_path, "w", encoding="utf-8") as handle:
            handle.write(content)
        print(f"Profiling report saved to {report_path}")

    def _create_runtime_issue(
        self,
        repo_root: str,
        package: Dict[str, Any],
        mainconfig: str,
        binary_path: str,
        exit_code: int,
        stdout: str,
        stderr: str,
    ) -> None:
        details = IssueDetails(
            issue_type="runtime",
            title=f"Runtime failure in {package['name']}",
            description=f"Exit code {exit_code} while running {binary_path}",
            source="run",
            tool="runtime",
        )
        issue_id = write_issue(details, repo_root)
        print(f"Runtime issue logged: {issue_id}")
        if stdout or stderr:
            log_path = os.path.join(repo_root, "docs", "issues", f"{issue_id}.log")
            with open(log_path, "w", encoding="utf-8") as handle:
                handle.write(stdout)
                if stderr:
                    handle.write("\n--- stderr ---\n")
                    handle.write(stderr)

    def _load_repo_packages(self, repo_root: str) -> List[Dict[str, Any]]:
        index_path = os.path.join(repo_root, ".maestro", "repo", "index.json")
        if not os.path.exists(index_path):
            return []
        import json

        with open(index_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        packages = data.get("packages_detected", []) + data.get("internal_packages", [])
        return packages

    def _find_package(self, packages: List[Dict[str, Any]], package_name: str) -> Optional[Dict[str, Any]]:
        for pkg in packages:
            if pkg.get("name") == package_name:
                return pkg
        return None

    def _get_mainconfigs(self, package: Dict[str, Any]) -> List[str]:
        upp_path = package.get("upp_path")
        if not upp_path or not os.path.exists(upp_path):
            return []
        parser = UppParser()
        parsed = parser.parse_file(upp_path)
        return [entry.get("name", "") for entry in parsed.get("mainconfigs", [])] or []

    def _is_mainconfig_known(self, package: Dict[str, Any], mainconfig: str) -> bool:
        return mainconfig in self._get_mainconfigs(package)

    def _build_status(self, package: Dict[str, Any], args: argparse.Namespace) -> str:
        binary = self._locate_binary(self._find_repo_root() or os.getcwd(), package, args)
        if not binary:
            return "not built"
        if self._is_out_of_date(package, binary):
            return "out of date"
        return "built"

    def _is_out_of_date(self, package: Dict[str, Any], binary_path: str) -> bool:
        try:
            binary_mtime = os.path.getmtime(binary_path)
        except OSError:
            return False

        pkg_dir = package.get("dir")
        files = package.get("files") or []
        for file_path in files:
            source_path = os.path.join(pkg_dir, file_path)
            try:
                if os.path.getmtime(source_path) > binary_mtime:
                    return True
            except OSError:
                continue
        return False

    def _locate_binary(self, repo_root: str, package: Dict[str, Any], args: argparse.Namespace) -> Optional[str]:
        method_name = args.method or self.method_manager.detect_default_method() or "default"
        target_dir = args.target_dir or ".maestro/build"
        candidates = []
        base_dir = os.path.join(repo_root, target_dir.strip("/"), method_name, package["name"])
        candidates.extend(self._find_executables(base_dir, package["name"]))
        if candidates:
            return candidates[0]

        # Try default target dir if method-specific layout not found.
        default_dir = os.path.join(repo_root, target_dir.strip("/"), package["name"])
        candidates.extend(self._find_executables(default_dir, package["name"]))

        if candidates:
            return candidates[0]
        return None

    def _find_executables(self, base_dir: str, package_name: str) -> List[str]:
        if not os.path.exists(base_dir):
            return []
        matches = []
        preferred = {package_name, f"{package_name}.exe"}
        for root, _, files in os.walk(base_dir):
            for file_name in files:
                if file_name in preferred:
                    matches.append(os.path.join(root, file_name))
                else:
                    path = os.path.join(root, file_name)
                    if os.access(path, os.X_OK) and not file_name.endswith((".a", ".lib", ".so", ".dll")):
                        matches.append(path)
        return matches

    def _find_repo_root(self) -> Optional[str]:
        current_dir = os.getcwd()
        while current_dir != "/":
            if os.path.exists(os.path.join(current_dir, ".maestro")):
                return current_dir
            parent_dir = os.path.dirname(current_dir)
            if parent_dir == current_dir:
                break
            current_dir = parent_dir
        return None


def add_run_parser(subparsers) -> argparse.ArgumentParser:
    run_parser = subparsers.add_parser("run", help="Run built binaries")
    run_parser.add_argument("package", nargs="?", help="Package to run")
    run_parser.add_argument("mainconfig", nargs="?", help="Mainconfig name (U++ only)")
    run_parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments passed to the binary")
    run_parser.add_argument("--list", action="store_true", help="List packages and available mainconfigs")
    run_parser.add_argument("--method", help="Build method name to locate outputs")
    run_parser.add_argument("--target-dir", help="Build output base dir (default: .maestro/build)")
    run_parser.add_argument("--cwd", help="Working directory for the run")
    run_parser.add_argument(
        "--profile",
        choices=["gprof", "valgrind", "perf", "cprofile", "visualvm", "yourkit"],
        help="Run with profiler and write report to docs/profiling/",
    )
    return run_parser
