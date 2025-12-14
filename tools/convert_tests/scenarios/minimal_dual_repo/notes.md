# Minimal Dual Repo Test Scenario

## Intent
Test basic dual-repo functionality with a minimal source repository.

## Description
This scenario tests the most basic functionality:
- Source repo contains a simple project with a README and a Python file
- Target repo starts empty and should receive converted content
- Conversion should succeed without writing to source

## Expected Behavior
- Maestro should be able to read from source_repo
- Maestro should write converted content to target_repo
- Source repo should remain unchanged