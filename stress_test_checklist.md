# Maestro Task Runner Stress Test Checklist

## Overview
This document outlines the required stress test scenarios for the Maestro task runner.

## Required Stress Scenarios

### Scenario 1: Interrupt Mid-Stream
**Objective**: Verify that Ctrl+C interrupts are handled gracefully with partial output capture.

**Steps**:
1. Create a session with subtasks that produce significant output
2. Run `maestro task run --stream-ai-output` 
3. During output streaming, press Ctrl+C
4. Verify:
   - Process stops cleanly
   - Partial output is saved to `partials/worker_<subtask>.partial.txt`
   - Subtask status is marked as `interrupted`
   - Session is saved properly
   - No stack traces or silent failures occur

### Scenario 2: Stop After N (Limit Subtasks)
**Objective**: Verify that `--limit-subtasks` works properly to control execution.

**Steps**:
1. Create a session with multiple subtasks (> 3 tasks)
2. Run `maestro task run --limit-subtasks 1`
3. Verify:
   - Only 1 subtask changes from `pending` to `done`
   - Other subtasks remain in `pending` state
   - Process exits cleanly after 1 task
4. Run `maestro task run --limit-subtasks 2` again
5. Verify:
   - Next 2 subtasks are processed
   - Total of 3 tasks completed now
   - Process respects the limit properly

## Expected Outcomes
- No corruption of remaining subtasks
- Proper session state preservation
- Clear visibility of current progress
- Clean interruption handling
- Proper resume functionality

## Validation Commands
- `maestro task list` - to see current status
- `ls .maestro/inputs/` - to see saved prompts
- `ls .maestro/outputs/` - to see saved outputs
- `ls .maestro/partials/` - to see partial outputs (for interrupted tasks)
- `maestro task run --retry-interrupted` - to resume interrupted tasks