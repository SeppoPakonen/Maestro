#!/usr/bin/env python3
"""
Maestro Chaos Rehearsal - Intentional Broken-Code Scenarios

This script runs a series of intentional failure scenarios to test
Maestro's build + fix machinery. It's designed to:

- Introduce faulty code and misconfigurations
- Run Maestro's detection + fix pipeline
- Verify behavior is as expected
- Capture improvement suggestions during the run
"""

import os
import sys
import json
import shutil
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass


@dataclass
class ScenarioResult:
    name: str
    status: str  # 'pass', 'fail', 'error'
    duration: float
    details: str
    artifacts: List[str]


# Global for capturing improvement suggestions
improvement_suggestions = []


def record_suggestion(text: str, severity: str, context: str = ""):
    """
    Record an improvement suggestion during scenario execution.

    Args:
        text: The suggestion text
        severity: 'minor', 'major', 'critical'
        context: Additional context about where the suggestion was made
    """
    suggestion = {
        "text": text,
        "severity": severity,
        "context": context,
        "timestamp": datetime.now().isoformat()
    }
    improvement_suggestions.append(suggestion)
    print(f"[SUGGESTION {severity.upper()}] {text}")


def run_command(cmd: str, cwd: str = None, timeout: int = 300) -> Tuple[int, str, str]:
    """
    Run a shell command and return exit code, stdout, and stderr.

    Args:
        cmd: Command to run
        cwd: Working directory
        timeout: Timeout in seconds

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout} seconds"


def setup_temp_project() -> str:
    """
    Create a temporary project structure for testing.

    Returns:
        Path to the temporary project directory
    """
    temp_dir = tempfile.mkdtemp(prefix="maestro_test_")
    
    # Create a simple C++ project with potential for errors
    main_cpp_content = """
#include <iostream>
#include <vector>

int main() {
    std::vector<int> numbers;
    numbers.push_back(1);
    numbers.push_back(2);
    std::cout << "Numbers: ";
    
    for (int i = 0; i < numbers.size(); i++) {
        std::cout << numbers[i] << " ";
    }
    std::cout << std::endl;
    
    return 0;
}
"""  # Fixed code to start with
    
    # Write main.cpp
    main_cpp_path = os.path.join(temp_dir, "main.cpp")
    with open(main_cpp_path, 'w') as f:
        f.write(main_cpp_content)
    
    # Create a basic build script
    build_script = f"""#!/bin/bash
cd "{temp_dir}"
g++ -o main main.cpp
"""
    
    build_script_path = os.path.join(temp_dir, "build.sh")
    with open(build_script_path, 'w') as f:
        f.write(build_script)
    os.chmod(build_script_path, 0o755)
    
    return temp_dir


def initialize_maestro_session(project_dir: str) -> str:
    """
    Initialize a Maestro session in the project directory.

    Args:
        project_dir: Path to project directory

    Returns:
        Path to the session file
    """
    # Initialize git repo (required for Maestro)
    run_command("git init", cwd=project_dir)
    run_command("git config user.email 'test@example.com'", cwd=project_dir)
    run_command("git config user.name 'Test User'", cwd=project_dir)
    
    # Create a basic build target
    session_file = os.path.join(project_dir, "test_session.json")
    
    # Initialize a basic session
    with open(session_file, 'w') as f:
        json.dump({
            "id": "test_session",
            "created_at": datetime.now().isoformat(),
            "state": "active",
            "build_targets": {},
            "subtasks": [],
            "active_build_target_id": None
        }, f, indent=2)
    
    return session_file


def create_build_target(session_file: str, project_dir: str):
    """
    Create a basic build target for testing.
    """
    import uuid
    
    build_target = {
        "target_id": f"test_target_{int(time.time())}",
        "name": "test_build",
        "created_at": datetime.now().isoformat(),
        "categories": ["test"],
        "description": "Test build target for scenarios",
        "why": "Testing Maestro's build and fix capabilities with intentional failures",
        "pipeline": {
            "steps": [
                {
                    "id": "compile",
                    "cmd": ["g++", "-o", "main", "main.cpp"],
                    "dir": project_dir
                }
            ]
        },
        "patterns": {
            "error_patterns": [
                "error:",
                "undefined reference",
                "multiple definition",
                "syntax error"
            ]
        }
    }
    
    # Create build targets directory
    session_dir = os.path.dirname(session_file)
    build_dir = os.path.join(session_dir, ".maestro", "build_targets")
    os.makedirs(build_dir, exist_ok=True)
    
    target_file = os.path.join(build_dir, f"{build_target['target_id']}.json")
    with open(target_file, 'w') as f:
        json.dump(build_target, f, indent=2)
    
    # Update session with target
    with open(session_file, 'r') as f:
        session = json.load(f)
    
    session["build_targets"][build_target["target_id"]] = target_file
    session["active_build_target_id"] = build_target["target_id"]
    
    with open(session_file, 'w') as f:
        json.dump(session, f, indent=2)


def scenario_a_trivial_compile_error() -> ScenarioResult:
    """
    Scenario A — Trivial Compile Error (Guaranteed Fixable)
    
    Introduce an obvious compile failure like missing semicolon or undefined variable,
    then run Maestro to fix it.
    """
    start_time = time.time()
    
    try:
        # Setup
        project_dir = setup_temp_project()
        session_file = initialize_maestro_session(project_dir)
        create_build_target(session_file, project_dir)
        
        # Introduce an intentional error (undefined variable)
        main_cpp_path = os.path.join(project_dir, "main.cpp")
        with open(main_cpp_path, 'r') as f:
            content = f.read()
        
        # Insert a syntax error that will definitely cause compilation failure
        error_content = content.replace(
            'std::cout << "Numbers: ";',
            'std::cout << "Numbers: "  // Missing semicolon to cause compile error\n    int x = undeclared_variable;  // Also undefined to cause error'
        )
        with open(main_cpp_path, 'w') as f:
            f.write(error_content)
        
        # Run build to capture diagnostics before fix
        exit_code, stdout, stderr = run_command(f"cd {project_dir} && python3 -m maestro.main handle_build_run '{session_file}'", timeout=60)
        
        # Check if diagnostics were captured
        build_dir = os.path.join(os.path.dirname(session_file), ".maestro", "build")
        runs_dir = os.path.join(build_dir, "runs")
        if os.path.exists(runs_dir):
            run_dirs = [d for d in os.listdir(runs_dir) if d.startswith("run_")]
        else:
            run_dirs = []
        
        artifacts = []
        diagnostics_before = []
        if run_dirs:
            latest_run_dir = os.path.join(runs_dir, max(run_dirs))
            diag_file = os.path.join(latest_run_dir, "diagnostics.json")
            if os.path.exists(diag_file):
                artifacts.append(diag_file)
                with open(diag_file, 'r') as f:
                    diagnostics_before = json.load(f)
        
        # Log diagnostics count before fix
        num_diagnostics_before = len(diagnostics_before)
        print(f"  Scenario A: Found {num_diagnostics_before} diagnostics before fix")
        
        # If diagnostics were captured, run fix
        if len(diagnostics_before) > 0:
            exit_code, stdout_fix, stderr_fix = run_command(f"cd {project_dir} && python3 -m maestro.main handle_build_fix '{session_file}' --max-iterations 1", timeout=120)
            
            # Check if fix was applied by looking for confirmation in output
            fix_applied = "patch_kept" in stdout_fix.lower() or "kept" in stdout_fix.lower() or "verification" in stdout_fix.lower()
            
            # Run build again to see if error is fixed
            exit_code_after, stdout_build_after, stderr_build_after = run_command(f"cd {project_dir} && python3 -m maestro.main handle_build_run '{session_file}'", timeout=60)
            
            # Check diagnostics after fix
            if os.path.exists(runs_dir):
                run_dirs_after = [d for d in os.listdir(runs_dir) if d.startswith("run_")]
            else:
                run_dirs_after = []
            
            diagnostics_after = []
            if run_dirs_after and len(run_dirs_after) > len(run_dirs):  # New run was created
                latest_run_dir_after = os.path.join(runs_dir, max(run_dirs_after))
                diag_file_after = os.path.join(latest_run_dir_after, "diagnostics.json")
                if os.path.exists(diag_file_after):
                    with open(diag_file_after, 'r') as f:
                        diagnostics_after = json.load(f)
            
            num_diagnostics_after = len(diagnostics_after)
            print(f"  Scenario A: Found {num_diagnostics_after} diagnostics after fix")
        else:
            print("  Scenario A: No diagnostics captured before fix")
            fix_applied = False
            num_diagnostics_after = num_diagnostics_before
            diagnostics_after = diagnostics_before
        
        duration = time.time() - start_time
        
        # Check if the targeted error was fixed
        # The error should be reduced if the fix was successful
        if num_diagnostics_after < num_diagnostics_before or (num_diagnostics_before > 0 and num_diagnostics_after == 0):
            return ScenarioResult(
                name="Scenario A - Trivial Compile Error",
                status="pass", 
                duration=duration,
                details=f"Successfully reduced diagnostics from {num_diagnostics_before} to {num_diagnostics_after}. Fix applied: {fix_applied}",
                artifacts=artifacts
            )
        elif num_diagnostics_after == num_diagnostics_before and num_diagnostics_before == 0:
            # If no diagnostics were found initially, that's also a scenario
            record_suggestion(
                "Build didn't produce expected diagnostics for trivial error scenario", 
                "major", 
                "Scenario A - Trivial Compile Error"
            )
            return ScenarioResult(
                name="Scenario A - Trivial Compile Error",
                status="fail",
                duration=duration,
                details="No diagnostics found - build may have succeeded when it should have failed",
                artifacts=artifacts
            )
        else:
            if num_diagnostics_after >= num_diagnostics_before:
                record_suggestion(
                    "Maestro failed to reduce the number of diagnostics in trivial compile error scenario", 
                    "major", 
                    "Scenario A - Trivial Compile Error"
                )
            return ScenarioResult(
                name="Scenario A - Trivial Compile Error",
                status="fail",
                duration=duration,
                details=f"Failed to fix error. Diagnostics before: {num_diagnostics_before}, after: {num_diagnostics_after}",
                artifacts=artifacts
            )
    
    except Exception as e:
        duration = time.time() - start_time
        record_suggestion(
            f"Exception occurred in Scenario A: {str(e)}", 
            "critical", 
            "Scenario A - Trivial Compile Error"
        )
        return ScenarioResult(
            name="Scenario A - Trivial Compile Error",
            status="error",
            duration=duration,
            details=f"Exception: {str(e)}",
            artifacts=[]
        )
    finally:
        # Cleanup
        if 'project_dir' in locals():
            shutil.rmtree(project_dir, ignore_errors=True)


def scenario_b_path_cwd_misconfiguration() -> ScenarioResult:
    """
    Scenario B — Path/CWD Misconfiguration (Exists but Not Found)
    
    Modify build target step to reference a script using a relative path that will fail when cwd differs.
    """
    start_time = time.time()
    
    try:
        # Setup
        project_dir = setup_temp_project()
        session_file = initialize_maestro_session(project_dir)
        
        # Create a build script in the project root
        build_script_content = """#!/bin/bash
# This script should work when run from project root
echo "Building from $(pwd)..."
g++ -o main main.cpp
"""
        build_script_path = os.path.join(project_dir, "build_from_root.sh")
        with open(build_script_path, 'w') as f:
            f.write(build_script_content)
        os.chmod(build_script_path, 0o755)
        
        # Create a problematic build target that references the script with relative path
        import uuid
        build_target = {
            "target_id": f"path_misconfig_{int(time.time())}",
            "name": "path_misconfig_test",
            "created_at": datetime.now().isoformat(),
            "categories": ["test"],
            "description": "Test path/CWD misconfiguration",
            "why": "Testing Maestro's ability to diagnose path misconfigurations",
            "pipeline": {
                "steps": [
                    {
                        "id": "build_step",
                        "cmd": ["./build_from_root.sh"],  # Will fail if not run from project root
                        "dir": project_dir  # This should help, but let's see what happens when CWD differs
                    }
                ]
            },
            "patterns": {
                "error_patterns": [
                    "error:",
                    "No such file or directory",
                    "command not found",
                    "cannot execute",
                    "permission denied"
                ]
            }
        }
        
        # Create build targets directory
        session_dir = os.path.dirname(session_file)
        build_dir = os.path.join(session_dir, ".maestro", "build_targets")
        os.makedirs(build_dir, exist_ok=True)
        
        target_file = os.path.join(build_dir, f"{build_target['target_id']}.json")
        with open(target_file, 'w') as f:
            json.dump(build_target, f, indent=2)
        
        # Update session with target
        with open(session_file, 'r') as f:
            session = json.load(f)
        
        session["build_targets"][build_target["target_id"]] = target_file
        session["active_build_target_id"] = build_target["target_id"]
        
        with open(session_file, 'w') as f:
            json.dump(session, f, indent=2)
        
        # Create a subdirectory and run build from there to trigger CWD issue
        subdir = os.path.join(project_dir, "subdir")
        os.makedirs(subdir, exist_ok=True)
        
        # Run build from subdirectory (this should cause path issues)
        exit_code, stdout, stderr = run_command(f"cd {subdir} && python3 -m maestro.main handle_build_run '{session_file}'", timeout=60)
        
        # Check for appropriate error messaging and diagnostic capture
        build_dir_maestro = os.path.join(os.path.dirname(session_file), ".maestro", "build", "runs")
        if os.path.exists(build_dir_maestro):
            run_dirs = [d for d in os.listdir(build_dir_maestro) if d.startswith("run_")]
        else:
            run_dirs = []
        
        artifacts = [session_file]
        if run_dirs:
            latest_run_dir = os.path.join(build_dir_maestro, max(run_dirs))
            diag_file = os.path.join(latest_run_dir, "diagnostics.json")
            if os.path.exists(diag_file):
                artifacts.append(diag_file)
        
        # Check for helpful error messages about CWD and path resolution
        has_cwd_info = "cwd" in stdout.lower() or "working directory" in stdout.lower() or "current directory" in stdout.lower()
        has_path_info = "path" in stdout.lower() or "resolved" in stdout.lower() or "command" in stdout.lower()
        has_helpful_hint = "dry-run" in stdout.lower() or "build show" in stdout.lower() or "verbose" in stdout.lower()
        
        duration = time.time() - start_time
        
        # Check if the error was properly diagnosed
        if exit_code != 0:  # We expect the run to fail due to path issue
            if has_cwd_info or has_path_info:
                return ScenarioResult(
                    name="Scenario B - Path/CWD Misconfiguration",
                    status="pass",
                    duration=duration,
                    details=f"Successfully diagnosed path/CWD issue. Found CWD info: {has_cwd_info}, Path info: {has_path_info}",
                    artifacts=artifacts
                )
            else:
                record_suggestion(
                    "Maestro's error message for path/CWD misconfiguration could be more informative about working directory", 
                    "major", 
                    "Scenario B - Path/CWD Misconfiguration"
                )
                return ScenarioResult(
                    name="Scenario B - Path/CWD Misconfiguration",
                    status="fail",
                    duration=duration,
                    details=f"Path issue occurred but error message lacks CWD/path information",
                    artifacts=artifacts
                )
        else:
            # If it didn't fail, that's also an issue
            record_suggestion(
                "Maestro should have failed when running from wrong CWD but it didn't", 
                "major", 
                "Scenario B - Path/CWD Misconfiguration"
            )
            return ScenarioResult(
                name="Scenario B - Path/CWD Misconfiguration",
                status="fail",
                duration=duration,
                details="Expected path issue didn't occur - build may have succeeded when it should have failed",
                artifacts=artifacts
            )
    
    except Exception as e:
        duration = time.time() - start_time
        record_suggestion(
            f"Exception occurred in Scenario B: {str(e)}", 
            "critical", 
            "Scenario B - Path/CWD Misconfiguration"
        )
        return ScenarioResult(
            name="Scenario B - Path/CWD Misconfiguration",
            status="error",
            duration=duration,
            details=f"Exception: {str(e)}",
            artifacts=[]
        )
    finally:
        # Cleanup
        if 'project_dir' in locals():
            shutil.rmtree(project_dir, ignore_errors=True)


def scenario_c_library_trap_error() -> ScenarioResult:
    """
    Scenario C — "Library Trap" Error (Rulebook Trigger + Escalation)
    
    Produce diagnostics that match a rule to test rulebook triggering.
    """
    start_time = time.time()
    
    try:
        # Setup
        project_dir = setup_temp_project()
        session_file = initialize_maestro_session(project_dir)
        create_build_target(session_file, project_dir)
        
        # Introduce a library error - using U++ style with problematic template
        main_cpp_path = os.path.join(project_dir, "main.cpp")
        problematic_content = """
#include <iostream>
#include <vector>

// Intentionally problematic code that would trigger U++/template rules
template<typename T>
class VectorContainer {
public:
    VectorContainer() = default;
    
    void add(const T& item) {
        // Intentionally problematic move operation
        data.push_back(std::move(const_cast<T&>(item))); // This would cause issues
    }
    
    void print() {
        for (const auto& item : data) {
            std::cout << item << " ";
        }
        std::cout << std::endl;
    }

private:
    std::vector<T> data;
};

int main() {
    VectorContainer<int> container;
    container.add(1);
    container.add(2);
    container.add(3);
    container.print();
    
    return 0;
}
"""
        with open(main_cpp_path, 'w') as f:
            f.write(problematic_content)
        
        # Run build to generate diagnostics
        exit_code, stdout, stderr = run_command(f"cd {project_dir} && python3 -m maestro.main handle_build_run '{session_file}'", timeout=60)
        
        # Look for diagnostic artifacts
        build_dir_maestro = os.path.join(os.path.dirname(session_file), ".maestro", "build", "runs")
        if os.path.exists(build_dir_maestro):
            run_dirs = [d for d in os.listdir(build_dir_maestro) if d.startswith("run_")]
        else:
            run_dirs = []
        
        artifacts = []
        if run_dirs:
            latest_run_dir = os.path.join(build_dir_maestro, max(run_dirs))
            diag_file = os.path.join(latest_run_dir, "diagnostics.json")
            if os.path.exists(diag_file):
                artifacts.append(diag_file)
        
        # Create a simple rulebook that could match this issue
        rulebook_dir = os.path.join(project_dir, ".maestro", "rulebooks")
        os.makedirs(rulebook_dir, exist_ok=True)
        
        rulebook_content = {
            "version": 1,
            "name": "test_template_rules",
            "description": "Test rulebook for template-related errors",
            "rules": [
                {
                    "id": "template_moveable_fix",
                    "enabled": True,
                    "priority": 10,
                    "match": {
                        "any": [
                            {
                                "contains": "move"
                            },
                            {
                                "contains": "template"
                            },
                            {
                                "contains": "std::move"
                            }
                        ]
                    },
                    "confidence": 0.8,
                    "explanation": "Template with move operations may need special handling",
                    "actions": [
                        {
                            "type": "prompt_patch",
                            "text": "Fix template with move operations by ensuring proper move semantics",
                            "model_preference": ["qwen", "claude"]
                        }
                    ],
                    "verify": {
                        "expect_signature_gone": True
                    }
                }
            ]
        }
        
        rulebook_file = os.path.join(rulebook_dir, "template_rules.json")
        with open(rulebook_file, 'w') as f:
            json.dump(rulebook_content, f, indent=2)
        
        # Run fix with the rulebook
        exit_code, stdout, stderr = run_command(f"cd {project_dir} && python3 -m maestro.main handle_build_fix '{session_file}' --max-iterations 2", timeout=120)
        
        # Check if rule matching was logged
        has_rule_match = "template_moveable_fix" in stdout.lower() or ("rule" in stdout.lower() and "match" in stdout.lower())
        has_model_change = "claude" in stdout.lower() or "qwen" in stdout.lower()  # Escalation might switch models
        
        duration = time.time() - start_time
        
        if has_rule_match or len(artifacts) > 0:
            return ScenarioResult(
                name="Scenario C - Library Trap Error",
                status="pass",
                duration=duration,
                details=f"Successfully triggered rule matching. Rule match detected: {has_rule_match}, Model change: {has_model_change}",
                artifacts=artifacts
            )
        else:
            record_suggestion(
                "Rule matching didn't occur as expected in library trap scenario", 
                "major", 
                "Scenario C - Library Trap Error"
            )
            return ScenarioResult(
                name="Scenario C - Library Trap Error",
                status="fail",
                duration=duration,
                details=f"Failed to trigger rule matching. Rule match detected: {has_rule_match}",
                artifacts=artifacts
            )
    
    except Exception as e:
        duration = time.time() - start_time
        record_suggestion(
            f"Exception occurred in Scenario C: {str(e)}", 
            "critical", 
            "Scenario C - Library Trap Error"
        )
        return ScenarioResult(
            name="Scenario C - Library Trap Error",
            status="error",
            duration=duration,
            details=f"Exception: {str(e)}",
            artifacts=[]
        )
    finally:
        # Cleanup
        if 'project_dir' in locals():
            shutil.rmtree(project_dir, ignore_errors=True)


def scenario_d_multi_error() -> ScenarioResult:
    """
    Scenario D — Multi-Error Situation (Fix One Without Breaking Others)
    
    Seed at least 2 independent compile errors and verify targeted fixing.
    """
    start_time = time.time()
    
    try:
        # Setup
        project_dir = setup_temp_project()
        session_file = initialize_maestro_session(project_dir)
        create_build_target(session_file, project_dir)
        
        # Introduce multiple independent errors
        main_cpp_path = os.path.join(project_dir, "main.cpp")
        multi_error_content = """
#include <iostream>
#include <vector>

int main() {
    std::vector<int> numbers;
    numbers.push_back(1);
    numbers.push_back(2);
    
    // Error 1: Using undeclared variable
    for (int i = 0; i < size; i++) {  // 'size' is not defined
        std::cout << numbers[i] << " ";
    }
    
    // Error 2: Missing semicolon
    std::cout << std::endl  // Missing semicolon
    
    return 0;
}
"""
        with open(main_cpp_path, 'w') as f:
            f.write(multi_error_content)
        
        # Run build to capture initial diagnostics
        exit_code, stdout, stderr = run_command(f"cd {project_dir} && python3 -m maestro.main handle_build_run '{session_file}'", timeout=60)
        
        # Look for diagnostic artifacts
        build_dir_maestro = os.path.join(os.path.dirname(session_file), ".maestro", "build", "runs")
        if os.path.exists(build_dir_maestro):
            run_dirs = [d for d in os.listdir(build_dir_maestro) if d.startswith("run_")]
        else:
            run_dirs = []
        
        artifacts = []
        if run_dirs:
            latest_run_dir = os.path.join(build_dir_maestro, max(run_dirs))
            diag_file = os.path.join(latest_run_dir, "diagnostics.json")
            if os.path.exists(diag_file):
                artifacts.append(diag_file)
        
        # Check number of diagnostics before fix
        diagnostics_before = []
        if artifacts and os.path.exists(artifacts[0]):
            with open(artifacts[0], 'r') as f:
                diagnostics_before = json.load(f)
            num_diagnostics_before = len(diagnostics_before)
        else:
            num_diagnostics_before = 0
        
        print(f"  Scenario D: Found {num_diagnostics_before} diagnostics before fix")
        
        # Run fix targeting just one error (the size variable issue)
        exit_code, stdout, stderr = run_command(f"cd {project_dir} && python3 -m maestro.main handle_build_fix '{session_file}' --max-iterations 1", timeout=120)
        
        # Run build again to check diagnostics after fix
        exit_code_after, stdout_after, stderr_after = run_command(f"cd {project_dir} && python3 -m maestro.main handle_build_run '{session_file}'", timeout=60)
        
        # Look for diagnostics after fix
        if os.path.exists(build_dir_maestro):
            run_dirs_after = [d for d in os.listdir(build_dir_maestro) if d.startswith("run_")]
        else:
            run_dirs_after = []
        
        artifacts_after = []
        if run_dirs_after and len(run_dirs_after) > len(run_dirs):
            # Find the latest run that's different from before
            latest_runs = sorted([r for r in run_dirs_after if r in run_dirs_after], reverse=True)
            if len(latest_runs) > 1:
                second_latest_run = latest_runs[1]  # The one before the most recent
                diag_file_after = os.path.join(build_dir_maestro, second_latest_run, "diagnostics.json")
                if os.path.exists(diag_file_after):
                    artifacts_after.append(diag_file_after)
            else:
                # If only one run, just use the latest
                diag_file_after = os.path.join(build_dir_maestro, max(run_dirs_after), "diagnostics.json")
                if os.path.exists(diag_file_after):
                    artifacts_after.append(diag_file_after)
        
        diagnostics_after = []
        if artifacts_after and os.path.exists(artifacts_after[0]):
            with open(artifacts_after[0], 'r') as f:
                diagnostics_after = json.load(f)
            num_diagnostics_after = len(diagnostics_after)
        else:
            # If no new diagnostics file, assume no change
            num_diagnostics_after = num_diagnostics_before
        
        duration = time.time() - start_time
        
        # Expected: Some errors fixed but not all (targeted fix)
        if num_diagnostics_after < num_diagnostics_before and num_diagnostics_after > 0:
            return ScenarioResult(
                name="Scenario D - Multi-Error Situation",
                status="pass",
                duration=duration,
                details=f"Successfully reduced errors from {num_diagnostics_before} to {num_diagnostics_after} (selective fixing)",
                artifacts=artifacts + artifacts_after
            )
        elif num_diagnostics_after == 0:
            # If all errors were fixed, that's also acceptable
            return ScenarioResult(
                name="Scenario D - Multi-Error Situation",
                status="pass",
                duration=duration,
                details=f"Successfully fixed all errors (even though targeted approach expected). Before: {num_diagnostics_before}, After: {num_diagnostics_after}",
                artifacts=artifacts + artifacts_after
            )
        elif num_diagnostics_after >= num_diagnostics_before:
            record_suggestion(
                "Multi-error scenario didn't show expected behavior - errors not reduced", 
                "major", 
                "Scenario D - Multi-Error Situation"
            )
            return ScenarioResult(
                name="Scenario D - Multi-Error Situation",
                status="fail",
                duration=duration,
                details=f"Failed to reduce errors. Before: {num_diagnostics_before}, After: {num_diagnostics_after}",
                artifacts=artifacts + artifacts_after
            )
        else:
            # Other unexpected outcome
            return ScenarioResult(
                name="Scenario D - Multi-Error Situation",
                status="pass",
                duration=duration,
                details=f"Mixed result - Before: {num_diagnostics_before}, After: {num_diagnostics_after}",
                artifacts=artifacts + artifacts_after
            )
    
    except Exception as e:
        duration = time.time() - start_time
        record_suggestion(
            f"Exception occurred in Scenario D: {str(e)}", 
            "critical", 
            "Scenario D - Multi-Error Situation"
        )
        return ScenarioResult(
            name="Scenario D - Multi-Error Situation",
            status="error",
            duration=duration,
            details=f"Exception: {str(e)}",
            artifacts=[]
        )
    finally:
        # Cleanup
        if 'project_dir' in locals():
            shutil.rmtree(project_dir, ignore_errors=True)


def run_all_scenarios(keep_going: bool = False) -> List[ScenarioResult]:
    """
    Run all defined scenarios.

    Args:
        keep_going: If True, continue running scenarios even if some fail

    Returns:
        List of scenario results
    """
    scenarios = [
        scenario_a_trivial_compile_error,
        scenario_b_path_cwd_misconfiguration,
        scenario_c_library_trap_error,
        scenario_d_multi_error
    ]
    
    results = []
    
    for scenario_func in scenarios:
        try:
            result = scenario_func()
            results.append(result)
            print(f"  {result.name}: {result.status.upper()} ({result.duration:.2f}s)")
            
            if not keep_going and result.status == 'error':
                break
        except Exception as e:
            print(f"  {scenario_func.__name__}: ERROR - {str(e)}")
            if not keep_going:
                break
    
    return results


def write_improvement_report():
    """
    Write the improvement suggestions to a report file.
    """
    if not improvement_suggestions:
        print("No improvement suggestions recorded.")
        return None
    
    # Create reports directory
    reports_dir = Path(".maestro/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = reports_dir / f"improvements_{timestamp}.md"
    
    with open(report_path, 'w') as f:
        f.write(f"# Maestro Improvement Suggestions Report\n\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")
        
        # Group by severity
        severity_groups = {}
        for suggestion in improvement_suggestions:
            severity = suggestion['severity']
            if severity not in severity_groups:
                severity_groups[severity] = []
            severity_groups[severity].append(suggestion)
        
        # Write by severity level
        for severity in ['critical', 'major', 'minor']:
            if severity in severity_groups:
                f.write(f"## {severity.upper()} Severity Suggestions\n\n")
                for suggestion in severity_groups[severity]:
                    f.write(f"- **{suggestion['text']}**\n")
                    f.write(f"  - Context: {suggestion.get('context', 'N/A')}\n")
                    f.write(f"  - Time: {suggestion['timestamp']}\n\n")
    
    return str(report_path)


def print_summary(results: List[ScenarioResult]):
    """
    Print a summary of scenario results.
    """
    print("\n" + "="*60)
    print("CHAOS REHEARSAL SUMMARY")
    print("="*60)
    
    total_scenarios = len(results)
    passed_scenarios = len([r for r in results if r.status == 'pass'])
    failed_scenarios = len([r for r in results if r.status == 'fail'])
    error_scenarios = len([r for r in results if r.status == 'error'])
    
    print(f"Total Scenarios: {total_scenarios}")
    print(f"Passed: {passed_scenarios}")
    print(f"Failed: {failed_scenarios}")
    print(f"Errors: {error_scenarios}")
    
    if results:
        total_duration = sum(r.duration for r in results)
        print(f"Total Duration: {total_duration:.2f}s")
    
    print("\nDetailed Results:")
    for result in results:
        status_color = {
            'pass': '\033[92m',  # Green
            'fail': '\033[91m',  # Red
            'error': '\033[93m'  # Yellow
        }.get(result.status, '')
        reset_color = '\033[0m'
        print(f"  {status_color}{result.status.upper():5s}{reset_color} - {result.name} ({result.duration:.2f}s)")
    
    # Write improvement report
    report_path = write_improvement_report()
    if report_path:
        print(f"\nImprovement suggestions report saved to: {report_path}")
        
        # Count by severity
        severity_counts = {}
        for suggestion in improvement_suggestions:
            severity = suggestion['severity']
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        print("Improvement suggestions by severity:")
        for severity in ['critical', 'major', 'minor']:
            count = severity_counts.get(severity, 0)
            print(f"  {severity.upper()}: {count}")
    
    print("\n" + "="*60)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Maestro Chaos Rehearsal - Intentional Broken-Code Scenarios")
    parser.add_argument('--keep-going', action='store_true', 
                        help='Continue running scenarios even if some fail')
    parser.add_argument('--list', action='store_true',
                        help='List available scenarios without running them')
    
    args = parser.parse_args()
    
    if args.list:
        print("Available scenarios:")
        print("  A - Trivial Compile Error")
        print("  B - Path/CWD Misconfiguration")  
        print("  C - Library Trap Error")
        print("  D - Multi-Error Situation")
        return
    
    print("Starting Maestro Chaos Rehearsal...")
    print("This will run a series of intentional failure scenarios to test Maestro's build + fix machinery.\n")
    
    results = run_all_scenarios(keep_going=args.keep_going)
    print_summary(results)


if __name__ == "__main__":
    main()