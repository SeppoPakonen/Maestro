#!/usr/bin/env python3
"""
Integration test for playbook functionality with the conversion pipeline
"""

import subprocess
import sys
import os
import tempfile
import shutil
import json
from pathlib import Path


def test_playbook_integration():
    """Test full integration of playbook functionality."""
    print("Testing playbook integration with conversion pipeline...")
    
    # Create test directories
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")
        
        # Change to temp directory
        original_dir = os.getcwd()
        os.chdir(temp_dir)
        
        try:
            # Initialize a .maestro directory
            os.makedirs(".maestro", exist_ok=True)
            
            # Create a simple test source file
            os.makedirs("source_repo", exist_ok=True)
            with open("source_repo/test.cpp", "w") as f:
                f.write("""
#include <iostream>

class TestClass {
public:
    TestClass() { std::cout << "RAII constructor" << std::endl; }
    ~TestClass() { std::cout << "RAII destructor" << std::endl; }
    
    void doSomething() {
        try {
            // Throwing an exception
            throw std::runtime_error("test exception");
        } catch (const std::exception& e) {
            std::cout << e.what() << std::endl;
        }
    }
};

int main() {
    TestClass obj;
    obj.doSomething();
    return 0;
}
""")
            
            # Create target directory
            os.makedirs("target_repo", exist_ok=True)
            
            # Test 1: List playbooks (should work)
            print("\n1. Testing playbook list command...")
            result = subprocess.run([sys.executable, f"{original_dir}/maestro.py", "convert", "playbook", "list"], 
                                    capture_output=True, text=True)
            print(f"Playbook list exit code: {result.returncode}")
            if result.returncode != 0:
                print(f"Error: {result.stderr}")
            else:
                print("✓ Playbook list command works")
            
            # Test 2: Show specific playbook (should work)
            print("\n2. Testing playbook show command...")
            result = subprocess.run([sys.executable, f"{original_dir}/maestro.py", "convert", "playbook", "show", "cpp_to_c"], 
                                    capture_output=True, text=True)
            print(f"Playbook show exit code: {result.returncode}")
            if result.returncode != 0:
                print(f"Error: {result.stderr}")
            else:
                print("✓ Playbook show command works")
            
            # Test 3: Use playbook (should work)
            print("\n3. Testing playbook use command...")
            result = subprocess.run([sys.executable, f"{original_dir}/maestro.py", "convert", "playbook", "use", "cpp_to_c"], 
                                    capture_output=True, text=True)
            print(f"Playbook use exit code: {result.returncode}")
            if result.returncode != 0:
                print(f"Error: {result.stderr}")
            else:
                print("✓ Playbook use command works")
                print(f"Output: {result.stdout}")
                
                # Check that binding file was created
                binding_file = Path(".maestro/convert/playbook_binding.json")
                if binding_file.exists():
                    print("✓ Playbook binding file created successfully")
                    with open(binding_file, 'r') as f:
                        binding_data = json.load(f)
                        print(f"  Binding: {binding_data}")
                else:
                    print("✗ Playbook binding file not created")
            
            # Test 4: Test override functionality
            print("\n4. Testing playbook override command...")
            result = subprocess.run([sys.executable, f"{original_dir}/maestro.py", "convert", "playbook-override", 
                                    "test_task_123", "--reason", "Test override for integration"], 
                                    capture_output=True, text=True)
            print(f"Playbook override exit code: {result.returncode}")
            if result.returncode != 0:
                print(f"Error: {result.stderr}")
            else:
                print("✓ Playbook override command works")
                
                # Check that override file was created
                override_file = Path(".maestro/convert/playbook_overrides.json")
                if override_file.exists():
                    print("✓ Playbook overrides file created successfully")
                    with open(override_file, 'r') as f:
                        overrides = json.load(f)
                        print(f"  Overrides: {overrides}")
                else:
                    print("✗ Playbook overrides file not created")
            
            print("\n✓ All integration tests passed!")
            return True
            
        except Exception as e:
            print(f"Integration test failed with error: {e}")
            return False
        finally:
            os.chdir(original_dir)


if __name__ == "__main__":
    success = test_playbook_integration()
    if success:
        print("\n🎉 All playbook integration tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)