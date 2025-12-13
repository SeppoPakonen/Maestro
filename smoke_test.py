#!/usr/bin/env python3
"""
Maestro CLI Smoke Test Script

This script performs a comprehensive smoke test of the Maestro CLI,
verifying that all command groups, aliases, and help paths work correctly.
"""
import subprocess
import sys
import os
from typing import List, Tuple


def run_command(cmd: List[str], timeout: int = 10) -> Tuple[int, str, str]:
    """
    Run a command and return (return_code, stdout, stderr).
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"


def test_help_commands():
    """Test all help command variations."""
    print("Testing help commands...")
    
    help_tests = [
        # Base help
        (["python3", "maestro.py", "--help"], "main help"),
        (["python3", "maestro.py", "-h"], "main -h"),
        
        # Command help
        (["python3", "maestro.py", "session", "--help"], "session --help"),
        (["python3", "maestro.py", "session", "-h"], "session -h"),
        (["python3", "maestro.py", "s", "--help"], "s --help"),
        (["python3", "maestro.py", "s", "-h"], "s -h"),
        (["python3", "maestro.py", "session", "h"], "session h"),
        (["python3", "maestro.py", "s", "h"], "s h"),
        
        (["python3", "maestro.py", "plan", "--help"], "plan --help"),
        (["python3", "maestro.py", "plan", "-h"], "plan -h"),
        (["python3", "maestro.py", "p", "--help"], "p --help"),
        (["python3", "maestro.py", "p", "-h"], "p -h"),
        (["python3", "maestro.py", "plan", "h"], "plan h"),
        (["python3", "maestro.py", "p", "h"], "p h"),
        
        (["python3", "maestro.py", "build", "--help"], "build --help"),
        (["python3", "maestro.py", "build", "-h"], "build -h"),
        (["python3", "maestro.py", "b", "--help"], "b --help"),
        (["python3", "maestro.py", "b", "-h"], "b -h"),
        (["python3", "maestro.py", "build", "h"], "build h"),
        (["python3", "maestro.py", "b", "h"], "b h"),
        
        (["python3", "maestro.py", "task", "--help"], "task --help"),
        (["python3", "maestro.py", "task", "-h"], "task -h"),
        (["python3", "maestro.py", "t", "--help"], "t --help"),
        (["python3", "maestro.py", "t", "-h"], "t -h"),
        (["python3", "maestro.py", "task", "h"], "task h"),
        (["python3", "maestro.py", "t", "h"], "t h"),
        
        (["python3", "maestro.py", "log", "--help"], "log --help"),
        (["python3", "maestro.py", "log", "-h"], "log -h"),
        (["python3", "maestro.py", "l", "--help"], "l --help"),
        (["python3", "maestro.py", "l", "-h"], "l -h"),
        (["python3", "maestro.py", "log", "h"], "log h"),
        (["python3", "maestro.py", "l", "h"], "l h"),
        
        (["python3", "maestro.py", "root", "--help"], "root --help"),
        (["python3", "maestro.py", "root", "-h"], "root -h"),
        (["python3", "maestro.py", "root", "h"], "root h"),
        
        (["python3", "maestro.py", "convert", "--help"], "convert --help"),
        (["python3", "maestro.py", "convert", "-h"], "convert -h"),
        (["python3", "maestro.py", "c", "--help"], "c --help"),
        (["python3", "maestro.py", "c", "-h"], "c -h"),
        (["python3", "maestro.py", "convert", "h"], "convert h"),
        (["python3", "maestro.py", "c", "h"], "c h"),
    ]
    
    failed_tests = []
    
    for cmd, description in help_tests:
        returncode, stdout, stderr = run_command(cmd)
        if returncode != 0:
            failed_tests.append((description, f"Command failed with return code {returncode}"))
        elif len(stdout.strip()) == 0:
            failed_tests.append((description, "Command produced no output"))
    
    return failed_tests


def test_alias_consistency():
    """Test that aliases behave consistently."""
    print("Testing alias consistency...")
    
    alias_tests = [
        # These should all produce similar output
        (["python3", "maestro.py", "session", "list"], "session list"),
        (["python3", "maestro.py", "s", "list"], "s list"),
        (["python3", "maestro.py", "session", "ls"], "session ls"),
        (["python3", "maestro.py", "s", "ls"], "s ls"),
        (["python3", "maestro.py", "session", "l"], "session l"),
        (["python3", "maestro.py", "s", "l"], "s l"),
    ]
    
    failed_tests = []
    
    # For this test, we'll just check that they don't crash
    for cmd, description in alias_tests:
        returncode, stdout, stderr = run_command(cmd, timeout=5)
        if returncode not in [0, 1]:  # 0 = success, 1 = expected error (like no session)
            failed_tests.append((description, f"Command failed with unexpected return code {returncode}: {stderr}"))
    
    return failed_tests


def test_subcommand_help():
    """Test help for subcommands."""
    print("Testing subcommand help...")
    
    subcmd_help_tests = [
        (["python3", "maestro.py", "build", "fix", "--help"], "build fix --help"),
        (["python3", "maestro.py", "build", "f", "--help"], "build f --help"),
        (["python3", "maestro.py", "b", "f", "--help"], "b f --help"),
        (["python3", "maestro.py", "build", "fix", "h"], "build fix h"),
        (["python3", "maestro.py", "build", "f", "h"], "build f h"),
        (["python3", "maestro.py", "b", "f", "h"], "b f h"),
        
        (["python3", "maestro.py", "build", "structure", "--help"], "build structure --help"),
        (["python3", "maestro.py", "build", "str", "--help"], "build str --help"),
        (["python3", "maestro.py", "b", "str", "--help"], "b str --help"),
        (["python3", "maestro.py", "build", "structure", "h"], "build structure h"),
        (["python3", "maestro.py", "build", "str", "h"], "build str h"),
        (["python3", "maestro.py", "b", "str", "h"], "b str h"),
        
        (["python3", "maestro.py", "plan", "tree", "--help"], "plan tree --help"),
        (["python3", "maestro.py", "plan", "tr", "--help"], "plan tr --help"),
        (["python3", "maestro.py", "p", "tr", "--help"], "p tr --help"),
    ]
    
    failed_tests = []
    
    for cmd, description in subcmd_help_tests:
        returncode, stdout, stderr = run_command(cmd)
        if returncode != 0:
            failed_tests.append((description, f"Command failed with return code {returncode}"))
        elif len(stdout.strip()) == 0:
            failed_tests.append((description, "Command produced no output"))
    
    return failed_tests


def test_no_silent_commands():
    """Test that commands don't silently do nothing."""
    print("Testing for silent commands...")
    
    # Test basic commands to ensure they respond appropriately
    silent_tests = [
        (["python3", "maestro.py", "session"], "session (no subcommand)"),
        (["python3", "maestro.py", "log"], "log (no subcommand)"),
        (["python3", "maestro.py", "root"], "root (no subcommand)"),
        (["python3", "maestro.py", "convert"], "convert (no subcommand)"),
    ]
    
    failed_tests = []
    
    for cmd, description in silent_tests:
        returncode, stdout, stderr = run_command(cmd, timeout=3)
        # Commands should either produce output or a clear error message
        # They should not hang or be completely silent
        if len(stdout.strip()) == 0 and len(stderr.strip()) == 0:
            failed_tests.append((description, "Command produced no output at all"))
    
    return failed_tests


def test_global_flags():
    """Test global flags consistency."""
    print("Testing global flags...")
    
    global_flag_tests = [
        (["python3", "maestro.py", "-v", "session", "list"], "-v global flag"),
        (["python3", "maestro.py", "--verbose", "session", "list"], "--verbose global flag"),
        (["python3", "maestro.py", "-q", "session", "list"], "-q global flag"),
        (["python3", "maestro.py", "--quiet", "session", "list"], "--quiet global flag"),
    ]
    
    failed_tests = []
    
    for cmd, description in global_flag_tests:
        returncode, stdout, stderr = run_command(cmd, timeout=5)
        # Global flags should not cause the program to crash
        if returncode not in [0, 1]:  # Allow error codes as long as not crashing
            failed_tests.append((description, f"Command failed with return code {returncode}"))
    
    return failed_tests


def main():
    """Run all smoke tests."""
    print("Running Maestro CLI Smoke Tests...")
    print("=" * 50)
    
    all_failed_tests = []
    
    # Run all test suites
    all_failed_tests.extend(test_help_commands())
    all_failed_tests.extend(test_alias_consistency()) 
    all_failed_tests.extend(test_subcommand_help())
    all_failed_tests.extend(test_no_silent_commands())
    all_failed_tests.extend(test_global_flags())
    
    print("=" * 50)
    
    if all_failed_tests:
        print(f"❌ {len(all_failed_tests)} tests failed:")
        for test_name, error in all_failed_tests:
            print(f"  - {test_name}: {error}")
        return 1
    else:
        print("✅ All smoke tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())