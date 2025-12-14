#!/bin/bash
# Validation script for converted C++ code
echo "Validating C++ conversion..."

# Look for .cpp or .cxx files and attempt to compile them
cpp_files=$(find . -name "*.cpp" -o -name "*.cxx" -o -name "*.cc")
if [ -z "$cpp_files" ]; then
    echo "WARNING: No C++ files found to compile"
    exit 0  # Not an error if no files exist yet
fi

echo "Found C++ files: $cpp_files"

# Create a simple build script
echo "Building C++ files..."
if command -v g++ &> /dev/null; then
    for file in $cpp_files; do
        echo "Compiling $file..."
        g++ -c "$file" -o "${file%.cpp}.o" -std=c++17 -Wall -Wextra
        if [ $? -ne 0 ]; then
            echo "Compilation of $file FAILED"
            exit 1
        fi
    done
    echo "C++ compilation PASSED"
else
    echo "G++ compiler not found, skipping compilation validation"
fi

echo "C++ validation completed"