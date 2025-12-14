# Maestro Chaos Rehearsal - Sample Output

This document shows an example of what the chaos rehearsal output looks like when running successfully.

## Example Output

```
Starting Maestro Chaos Rehearsal...
This will run a series of intentional failure scenarios to test Maestro's build + fix machinery.

  Scenario A - Trivial Compile Error: PASS (24.32s)
  Scenario B - Path/CWD Misconfiguration: PASS (18.76s)
  Scenario C - Library Trap Error: PASS (35.41s)
  Scenario D - Multi-Error Situation: PASS (29.23s)

============================================================
CHAOS REHEARSAL SUMMARY
============================================================
Total Scenarios: 4
Passed: 4
Failed: 0
Errors: 0
Total Duration: 107.72s

Detailed Results:
  PASS  - Scenario A - Trivial Compile Error (24.32s)
  PASS  - Scenario B - Path/CWD Misconfiguration (18.76s)
  PASS  - Scenario C - Library Trap Error (35.41s)
  PASS  - Scenario D - Multi-Error Situation (29.23s)

Improvement suggestions report saved to: .maestro/reports/improvements_20251214_123456.md
Improvement suggestions by severity:
  CRITICAL: 1
  MAJOR: 2
  MINOR: 3

============================================================
```

## Key Features Demonstrated

1. **Scenario A** - Successfully detected and fixed a trivial compile error (missing semicolon, undefined variable)
2. **Scenario B** - Detected path/CWD misconfiguration when running from subdirectory
3. **Scenario C** - Triggered rulebook matching for U++ template issues and demonstrated escalation
4. **Scenario D** - Implemented targeted fixing of specific errors while preserving others

## Improvement Suggestions Example

The system captured suggestions like:
- "Build output could be more verbose for debugging"
- "Error messages should include more context about file paths"
- "Rule matching could provide more detailed explanation of matches"