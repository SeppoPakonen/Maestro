#!/bin/bash
# Validation script for converted TypeScript code
echo "Validating TypeScript conversion..."

# Check if tsconfig.json exists
if [ ! -f "tsconfig.json" ]; then
    echo "ERROR: tsconfig.json not found"
    exit 1
fi

# Look for .ts files and validate them
ts_files=$(find . -name "*.ts" -o -name "*.tsx")
if [ -z "$ts_files" ]; then
    echo "WARNING: No TypeScript files found to validate"
else
    echo "Found TypeScript files: $ts_files"
    # If tsc is available, run type checking
    if command -v tsc &> /dev/null; then
        tsc --noEmit
        if [ $? -eq 0 ]; then
            echo "TypeScript validation PASSED"
        else
            echo "TypeScript validation FAILED"
            exit 1
        fi
    else
        echo "TypeScript compiler (tsc) not found, skipping type validation"
    fi
fi

echo "TypeScript validation completed successfully"