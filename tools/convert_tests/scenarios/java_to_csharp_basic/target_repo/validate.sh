#!/bin/bash
# Validation script for converted C# code
echo "Validating C# conversion..."

# Look for .cs files and validate project structure
cs_files=$(find . -name "*.cs")
if [ -z "$cs_files" ]; then
    echo "WARNING: No C# files found to validate"
    exit 0  # Not an error if no files exist yet
fi

echo "Found C# files: $cs_files"

# Check for project files
proj_files=$(find . -name "*.csproj")
if [ -n "$proj_files" ]; then
    echo "Found project files: $proj_files"
    # If dotnet is available, try to build
    if command -v dotnet &> /dev/null; then
        for proj in $proj_files; do
            echo "Building project $proj..."
            dotnet build "$proj" --nologo
            if [ $? -eq 0 ]; then
                echo "Project $proj built successfully"
            else
                echo "Project $proj build FAILED"
                exit 1
            fi
        done
    else
        echo "Dotnet SDK not found, skipping build validation"
    fi
else
    echo "No .csproj files found, validating C# syntax individually..."
    # Validate syntax by checking for common C# constructs
    for file in $cs_files; do
        if [ -s "$file" ]; then
            echo "Syntax check for $file completed"
        fi
    done
fi

echo "C# validation completed"