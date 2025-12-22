#!/bin/bash

# Test script for Qwen Python implementation with existing configuration
# This script runs the test that uses the existing OAuth configuration in ~/.qwen

cd "$(dirname "$0")/.." || exit 1

# Run the test with existing configuration
python3 -m maestro.qwen.test_with_config config