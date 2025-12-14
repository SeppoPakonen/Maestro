# Conversion Pipeline Stage 2 - Core Builds Regression Checklist

## Overview
This checklist verifies the proper functioning of Stage 2 ("core_builds") of the conversion pipeline: a controlled loop that gets a minimal subset of the project compiling, using Maestro's build target + diagnostics + fix machinery.

## Pre-requisites
- [ ] Ensure you have a directory with source code to convert
- [ ] Maestro CLI is installed and accessible from command line
- [ ] Target directory is prepared and contains code that needs conversion/build fixes

## Stage 2 Core Builds - Setup

### 1. Pipeline Creation and Stage Initialization
- [ ] Run: `maestro convert new <source_path> <target_path> --name "Test Conversion"`
- [ ] Verify pipeline.json is created in `.maestro/convert/`
- [ ] Verify stage directories are created: `.maestro/convert/stages/core_builds/`

### 2. Stage 2 Build Target Management
- [ ] Run: `maestro convert run --stage core_builds`
- [ ] Verify a conversion build target is created/selected:
  - [ ] Check that `convert-core` build target is created if none exists
  - [ ] Verify target has minimal pipeline steps: configure (optional) + build (required)
  - [ ] Check that appropriate build commands are set based on target directory content (Makefile, CMakeLists.txt, etc.)
- [ ] Verify the stage uses the correct build target and doesn't overwrite user's normal build target

## Stage 2 Core Builds - Execution

### 3. Baseline Capture
- [ ] Check that baseline build run is captured when Stage 2 starts
- [ ] Verify `run_id` and diagnostics.json are saved appropriately
- [ ] Check that top signatures and counts are captured
- [ ] Verify artifacts are saved to `.maestro/convert/stages/core_builds/`

### 4. Fix Loop with Hard Limits
- [ ] Verify fix loop runs with maximum iterations (default 10)
- [ ] Check that each iteration selects target signature properly (default: top signature by count/severity)
- [ ] Verify `maestro build fix run --limit-fixes 1 --target signature:<sig>` is called correctly
- [ ] Confirm verified keep/revert behavior is maintained
- [ ] Run `maestro build run` again after each fix iteration
- [ ] Verify progress is recorded (signatures disappeared, remained, error count dropped)

### 5. Stop Conditions
- [ ] When build returns success, verify stage marks as completed
- [ ] If error count falls below configurable threshold, verify stage marks as completed
- [ ] If iteration limit reached with no progress, verify stage stops appropriately

## Stage 2 Core Builds - Progress Tracking

### 6. User Visibility
- [ ] During each iteration (unless `--quiet`), verify progress is printed:
  - [ ] Iteration number
  - [ ] Targeted signature
  - [ ] Kept/reverted
  - [ ] Errors before/after
  - [ ] Next action suggestion
- [ ] Check that `progress.json` is updated with structured entries containing:
  - [ ] Timestamp
  - [ ] Signature targeted
  - [ ] Result
  - [ ] Errors before/after
  - [ ] Model used (qwen/claude escalation)

## Stage 2 Core Builds - Resume Support

### 7. Interruption Recovery
- [ ] During Stage 2 execution, interrupt with Ctrl+C
- [ ] Verify partial state remains valid
- [ ] Run again: `maestro convert run`
- [ ] Verify Stage 2 resumes instead of restarting from scratch
- [ ] Check that iteration count continues from progress.json

## Stage 2 Core Builds - Show Command

### 8. Convert Show Information
- [ ] When Stage 2 is active or completed, run: `maestro convert show`
- [ ] Verify it displays:
  - [ ] Stage build target
  - [ ] Baseline run id + timestamp
  - [ ] Current error count trend
  - [ ] Top remaining signatures
  - [ ] Last 3 iteration outcomes

## Error Handling and Edge Cases

### 9. Edge Cases
- [ ] Test when build succeeds immediately - verify Stage 2 marks as done and advances to Stage 3
- [ ] Test with no build targets in target directory - verify fallback to `convert-core` target
- [ ] Test with existing `convert-core` target - verify it reuses the target

### 10. Build Target Persistence
- [ ] Verify the selected/created build target ID is persisted in `.maestro/convert/stages/core_builds/stage.json`
- [ ] Check that stage can resume with the same build target

## Expected Artifacts After Successful Stage 2

- [ ] `.maestro/convert/stages/core_builds/stage.json` - Stage state + config
- [ ] `.maestro/convert/stages/core_builds/runs/` - Links to build runs and fix runs  
- [ ] `.maestro/convert/stages/core_builds/diagnostics_baseline.json` - First failing run
- [ ] `.maestro/convert/stages/core_builds/progress.json` - Timeline of eliminated signatures
- [ ] Updated `.maestro/convert/pipeline.json` with Stage 2 completion status
- [ ] Pipeline advances to Stage 3 when core build passes

## Final Verification
- [ ] Stage 2 runs a baseline build and captures diagnostics
- [ ] Iterative fix loop runs with hard limits and verified keep/revert
- [ ] Progress is recorded and visible
- [ ] Stage can be resumed after interruption
- [ ] Pipeline advances to Stage 3 when core build passes (or configured criteria met)

This checklist should be run after any changes to the conversion pipeline Stage 2 functionality to ensure all requirements continue to work correctly.