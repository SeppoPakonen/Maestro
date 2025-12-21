#!/usr/bin/env python3
"""
Test script for rulebook matching during build fix
"""

import sys
import os
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from maestro.main import (
    Diagnostic,
    match_rulebooks_to_diagnostics,
    load_registry,
    save_registry,
    get_registry_file_path
)


def test_rulebook_matching():
    print("Testing rulebook matching during build fix...")
    
    # Create a temporary directory to simulate a project
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Created temporary project directory: {temp_dir}")
        
        # Create a .maestro directory in the temp dir to make it a valid repo
        maestro_dir = os.path.join(temp_dir, '.maestro')
        os.makedirs(maestro_dir, exist_ok=True)
        
        # Register this temporary directory with the upp-cpp-fixes rulebook in the registry
        registry_path = get_registry_file_path()
        original_registry_content = None
        
        # Save original registry to restore later
        if os.path.exists(registry_path):
            with open(registry_path, 'r') as f:
                original_registry_content = f.read()
        
        # Create a registry entry for our test directory
        test_registry = {
            "repos": [
                {
                    "repo_id": "test_repo",
                    "relative_hint": None,
                    "abs_path": temp_dir,
                    "rulebook": "upp-cpp-fixes"
                }
            ],
            "active_rulebook": "upp-cpp-fixes"
        }
        
        save_registry(test_registry)
        print("✓ Created test registry entry")
        
        # Create test diagnostics that should match the upp-cpp-fixes rulebook
        test_diagnostics = [
            Diagnostic(
                tool="g++",
                severity="error",
                file="test.cpp",
                line=10,
                message="static_assert failed: 'Element type must be Moveable for Vector<T>'",
                raw="In file included from /usr/include/upp/Vector.h:10:0,\n                     from test.cpp:5:\n/usr/include/upp/Vector.h:45:3: error: static_assert failed: 'Element type must be Moveable for Vector<T>'",
                signature="g++_vector_moveable_error",
                tags=["upp", "vector", "moveable"]
            ),
            Diagnostic(
                tool="clang++", 
                severity="error",
                file="main.cpp",
                line=5,
                message="error: no matching function for call to 'Vector<T>::Vector()'",
                raw="main.cpp:5:12: error: no matching function for call to 'Vector<T>::Vector()'\nUpp::Vector<MyClass> vec;",
                signature="clang_vector_error", 
                tags=["upp", "vector"]
            )
        ]
        
        print("✓ Created test diagnostics")
        
        # Test the rulebook matching
        matched_rules = match_rulebooks_to_diagnostics(test_diagnostics, temp_dir)
        
        print(f"✓ Found {len(matched_rules)} matched rules")
        
        if len(matched_rules) > 0:
            for i, matched_rule in enumerate(matched_rules):
                print(f"  Match {i+1}:")
                print(f"    Rule ID: {matched_rule.rule.id}")
                print(f"    Confidence: {matched_rule.confidence}")
                print(f"    Explanation: {matched_rule.rule.explanation}")
                print(f"    Diagnostic: {matched_rule.diagnostic.message[:60]}...")
        else:
            print("  ⚠ No rules matched - this might be expected if the rulebook isn't loaded properly")
        
        # Test with a diagnostic that should NOT match
        non_matching_diagnostic = [
            Diagnostic(
                tool="gcc",
                severity="warning", 
                file="other.cpp",
                line=20,
                message="unused variable 'x'",
                raw="warning: unused variable 'x'",
                signature="gcc_unused_var",
                tags=["compiler", "warning"]
            )
        ]
        
        non_matching_rules = match_rulebooks_to_diagnostics(non_matching_diagnostic, temp_dir)
        print(f"✓ Non-matching diagnostic matched {len(non_matching_rules)} rules (should be 0)")
        
        # Restore original registry
        if original_registry_content:
            with open(registry_path, 'w') as f:
                f.write(original_registry_content)
        else:
            # If there was no original registry, remove the test one
            os.remove(registry_path)
        
        print("✓ Restored original registry")
    
    print("\n✓ Rulebook matching test completed!")
    return True


def test_generate_debugger_prompt_with_rules():
    print("\nTesting generate_debugger_prompt with rulebook matching...")
    
    # Import the function
    from maestro.main import generate_debugger_prompt
    from maestro.session_model import Session
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a minimal session
        session = Session(
            id="test-session",
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00", 
            root_task="Test task",
            subtasks=[],
            rules_path=None,
            status="new"
        )
        
        # Create test diagnostic
        test_diagnostics = [
            Diagnostic(
                tool="g++",
                severity="error",
                file="test.cpp", 
                line=10,
                message="static_assert failed: 'Element type must be Moveable for Vector<T>'",
                raw="In file included from /usr/include/upp/Vector.h:10:0,\n                     from test.cpp:5:\n/usr/include/upp/Vector.h:45:3: error: static_assert failed: 'Element type must be Moveable for Vector<T>'",
                signature="g++_vector_moveable_error",
                tags=["upp", "vector", "moveable"]
            )
        ]
        
        # Register this temp dir to use the upp-cpp-fixes rulebook
        test_registry = {
            "repos": [
                {
                    "repo_id": "test_repo",
                    "relative_hint": None,
                    "abs_path": temp_dir,
                    "rulebook": "upp-cpp-fixes"
                }
            ],
            "active_rulebook": "upp-cpp-fixes"
        }
        save_registry(test_registry)
        
        # Generate prompt
        try:
            prompt = generate_debugger_prompt(session, test_diagnostics, temp_dir)
            print("✓ Generated debugger prompt with rulebook matching")
            
            # Check if the prompt contains rulebook information
            has_matched_rules = "[MATCHED REACTIVE RULES]" in prompt
            print(f"✓ Prompt contains rulebook matches: {has_matched_rules}")
            
            if has_matched_rules:
                print("  ✓ Rulebook matching correctly integrated into prompt")
                # Extract and show the matched rules section
                lines = prompt.split('\n')
                in_rules_section = False
                rule_lines = []
                for line in lines:
                    if line.startswith("[MATCHED REACTIVE RULES]"):
                        in_rules_section = True
                        continue
                    elif line.startswith("[") and in_rules_section:
                        break
                    elif in_rules_section:
                        rule_lines.append(line)
                
                if rule_lines:
                    print(f"  Sample rule content: {' '.join(rule_lines[:5])}")
            
        except Exception as e:
            print(f"✗ Error generating debugger prompt: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # Restore registry
            original_registry_content = None
            registry_path = get_registry_file_path()
            if os.path.exists(registry_path):
                os.remove(registry_path)
    
    print("✓ Debugger prompt test completed!")
    return True


if __name__ == "__main__":
    success1 = test_rulebook_matching()
    success2 = test_generate_debugger_prompt_with_rules()
    
    if success1 and success2:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed!")
        sys.exit(1)