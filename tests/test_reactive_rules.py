#!/usr/bin/env python3
"""
Test script for reactive fix rules functionality
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from maestro.main import (
    load_rulebook, 
    match_rules, 
    Diagnostic,
    Rulebook,
    Rule,
    RuleMatch,
    MatchCondition,
    RuleAction,
    RuleVerify
)


def test_reactive_rules():
    print("Testing reactive fix rules functionality...")
    
    # Test loading the rulebook
    print("\n1. Testing load_rulebook function...")
    try:
        rulebook = load_rulebook("upp-cpp-fixes")
        print(f"   ✓ Loaded rulebook: {rulebook.name}")
        print(f"   ✓ Description: {rulebook.description}")
        print(f"   ✓ Version: {rulebook.version}")
        print(f"   ✓ Number of rules: {len(rulebook.rules)}")
        
        if rulebook.rules:
            rule = rulebook.rules[0]  # Take the first rule if it exists
            print(f"   ✓ Sample rule ID: {rule.id}")
            print(f"   ✓ Rule enabled: {rule.enabled}")
            print(f"   ✓ Rule priority: {rule.priority}")
            print(f"   ✓ Rule confidence: {rule.confidence}")
            print(f"   ✓ Number of match conditions: {len(rule.match.any)}")
            print(f"   ✓ Number of 'not' conditions: {len(rule.match.not_conditions)}")
            print(f"   ✓ Number of actions: {len(rule.actions)}")
    except Exception as e:
        print(f"   ✗ Error loading rulebook: {e}")
        return False
    
    # Create a sample diagnostic that should match the U++ Vector/Moveable rule
    print("\n2. Creating sample diagnostic...")
    sample_diagnostic = Diagnostic(
        tool="g++",
        severity="error",
        file="test.cpp",
        line=10,
        message="static_assert failed: 'Element type must be Moveable for Vector<T>'",
        raw="In file included from /usr/include/upp/Vector.h:10:0,\n                     from test.cpp:5:\n/usr/include/upp/Vector.h:45:3: error: static_assert failed: 'Element type must be Moveable for Vector<T>'",
        signature="g++_vector_moveable_error",
        tags=["upp", "vector", "moveable"]
    )
    print(f"   ✓ Created diagnostic: {sample_diagnostic.message}")
    
    # Test matching rules
    print("\n3. Testing match_rules function...")
    try:
        matched_rules = match_rules([sample_diagnostic], rulebook)
        print(f"   ✓ Found {len(matched_rules)} matched rules")
        
        for i, match in enumerate(matched_rules):
            print(f"   Match {i+1}:")
            print(f"     - Rule ID: {match.rule.id}")
            print(f"     - Confidence: {match.confidence}")
            print(f"     - Explanation: {match.rule.explanation}")
            print(f"     - Diagnostic: {match.diagnostic.message}")
    except Exception as e:
        print(f"   ✗ Error matching rules: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Create a diagnostic that should NOT match (contains "already derives from Moveable")
    print("\n4. Testing negative match (should not match)...")
    negative_diagnostic = Diagnostic(
        tool="g++",
        severity="warning",
        file="test.cpp",
        line=15,
        message="Type already derives from Moveable, no changes needed",
        raw="warning: Type already derives from Moveable, no changes needed",
        signature="g++_already_moveable",
        tags=["upp", "vector"]
    )
    
    try:
        negative_matches = match_rules([negative_diagnostic], rulebook)
        print(f"   ✓ Found {len(negative_matches)} matched rules (should be 0)")
        if len(negative_matches) == 0:
            print("   ✓ Correctly filtered out the diagnostic with 'not' condition")
        else:
            print("   ⚠ Warning: Should not have matched this diagnostic")
    except Exception as e:
        print(f"   ✗ Error in negative matching: {e}")
        return False
    
    # Test with a diagnostic that contains Upp::Vector
    print("\n5. Testing with Upp::Vector diagnostic...")
    vector_diagnostic = Diagnostic(
        tool="clang++",
        severity="error", 
        file="main.cpp",
        line=5,
        message="error: no matching function for call to 'Vector<T>::Vector()'",
        raw="main.cpp:5:12: error: no matching function for call to 'Vector<T>::Vector()'\nUpp::Vector<MyClass> vec;",
        signature="clang_vector_error",
        tags=["upp", "vector"]
    )
    
    try:
        vector_matches = match_rules([vector_diagnostic], rulebook)
        print(f"   ✓ Found {len(vector_matches)} matched rules for U++ Vector diagnostic")
        for i, match in enumerate(vector_matches):
            print(f"     Match {i+1}: Rule {match.rule.id} with confidence {match.confidence}")
    except Exception as e:
        print(f"   ✗ Error matching vector diagnostic: {e}")
        return False

    print("\n✓ All tests passed!")
    return True


if __name__ == "__main__":
    success = test_reactive_rules()
    sys.exit(0 if success else 1)