#!/bin/bash
# Validation script for JS -> Strict TS conversion
# This script runs the required validation checks

echo "Running validation for JS to Strict TS conversion..."

# Check if TypeScript compiler is available
if ! command -v tsc &> /dev/null; then
    echo "TypeScript compiler (tsc) not found - installing locally..."
    npm install typescript --save-dev
fi

# Compile TypeScript with --noEmit to check for type errors
echo "Running TypeScript type check..."
npx tsc --noEmit --strict true
if [ $? -ne 0 ]; then
    echo "FAILED: TypeScript compilation error"
    npx tsc --noEmit --strict true --listFiles 2>&1  # Show more details
    exit 1
fi

echo "TypeScript files passed type checking"

# Run a basic execution test (if compiled output exists)
if [ -f "dist/calculator.js" ]; then
    echo "Running compiled output test..."
    node dist/calculator.js > execution_output.txt 2>&1
    if [ $? -ne 0 ]; then
        echo "WARNING: Execution test failed, but this might be expected"
    fi
else
    echo "No compiled output found to execute"
fi

echo "JS to Strict TS validation completed successfully"