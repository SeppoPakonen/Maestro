#!/usr/bin/env python3
"""
Test script to verify the known issue matching functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from maestro.main import Diagnostic
from maestro.known_issues import match_known_issues

def test_upp_known_issue():
    # Create a diagnostic that matches U++ Vector<T> Moveable<T> issue
    test_diag = Diagnostic(
        tool="gcc",
        severity="error",
        file="main.cpp",
        line=15,
        message="no match for 'operator=' in Vector<MyClass> assignment - MyClass does not satisfy Moveable requirement",
        raw="main.cpp:15:10: error: no match for 'operator=' (operand types are 'Vector<MyClass>' and 'Vector<MyClass>') - MyClass does not satisfy Moveable<T> requirement for Vector<T> element type",
        signature="test_signature_123",
        tags=["gcc", "cpp", "vector"],
        known_issues=[]
    )
    
    print("Testing U++ Moveable/Vector known issue matching...")
    print(f"Diagnostic raw: {test_diag.raw}")
    print(f"Diagnostic message: {test_diag.message}")
    
    # Test matching
    matches = match_known_issues([test_diag])
    
    print(f"Matches found: {len(matches)}")
    
    if matches:
        for sig, issues in matches.items():
            print(f"Signature '{sig}' has {len(issues)} matched issues:")
            for issue in issues:
                print(f"  - ID: {issue.id}")
                print(f"  - Description: {issue.description}")
                print(f"  - Confidence: {issue.confidence}")
                print(f"  - Fix hint: {issue.fix_hint}")
                print(f"  - Tags: {issue.tags}")
    
    # Test with another diagnostic that should match
    upp_diag = Diagnostic(
        tool="clang",
        severity="error", 
        file="container.cpp",
        line=22,
        message="template constraint failed: Vector<T> requires T : Moveable<T>",
        raw="container.cpp:22:5: error: static assertion failed: Vector<T> requires T : Moveable<T> for proper element relocation",
        signature="test_signature_456",
        tags=["clang", "cpp", "vector"],
        known_issues=[]
    )
    
    matches2 = match_known_issues([upp_diag])
    print(f"\nSecond test - Matches found: {len(matches2)}")
    
    if matches2:
        for sig, issues in matches2.items():
            print(f"Signature '{sig}' has {len(issues)} matched issues:")
            for issue in issues:
                print(f"  - ID: {issue.id}")
                print(f"  - Description: {issue.description}")
                print(f"  - Confidence: {issue.confidence}")
                print(f"  - Fix hint: {issue.fix_hint}")
    
    return len(matches) > 0 or len(matches2) > 0

if __name__ == "__main__":
    success = test_upp_known_issue()
    if success:
        print("\n✓ Known issue matching test passed!")
        sys.exit(0)
    else:
        print("\n✗ Known issue matching test failed!")
        sys.exit(1)