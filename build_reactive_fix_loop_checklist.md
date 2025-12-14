# Conversion Pipeline Stage 2 - Regression Checklist

## Overview
This checklist verifies the proper functioning of Stage 2 (Core Builds) of the conversion pipeline. Complete this checklist after any changes to ensure the core functionality remains intact.

## Pre-requisites
- [ ] Ensure you have a directory with source code to convert
- [ ] Maestro CLI is installed and accessible from command line
- [ ] Target directory is prepared for conversion

## Stage 2 Core Builds - Setup

### 1. Pipeline Creation and Stage Initialization
- [ ] Run: `maestro convert new <source_path> <target_path> --name "Test Conversion"`
- [ ] Verify pipeline.json is created in `.maestro/convert/`
- [ ] Verify stage directories are created: `.maestro/convert/stages/core_builds/`

### 2. Stage 2 Execution Preparations
- [ ] Check that a conversion build target is created/selected:
  - [ ] Run: `maestro build list` 
  - [ ] Verify `convert-core` target exists or was created
  - [ ] Verify build target has minimal pipeline: configure (optional) + build (required)

## Stage 2 Core Builds - Execution

### 3. Baseline Capture
- [ ] Run: `maestro convert run --stage core_builds`
- [ ] Check that baseline diagnostics are captured: `.maestro/convert/stages/core_builds/diagnostics_baseline.json`
- [ ] Verify the baseline contains initial diagnostic signatures

### 4. Fix Loop Execution
- [ ] Verify the fix loop starts running with signature targeting
- [ ] Check iteration progress is being tracked: `.maestro/convert/stages/core_builds/progress.json`
- [ ] Verify each iteration shows: 
  - [ ] Targeted signature
  - [ ] Build errors before/after fix attempt
  - [ ] Whether error count dropped

### 5. Progress Tracking
- [ ] Verify progress.json contains structured entries with:
  - [ ] Timestamp
  - [ ] Signature targeted
  - [ ] Result (eliminated/remaining)
  - [ ] Errors before/after
  - [ ] Model used
- [ ] Check that `convert show` displays:
  - [ ] Stage build target ID and path
  - [ ] Baseline run ID + timestamp
  - [ ] Current error count trend
  - [ ] Top remaining signatures
  - [ ] Last 3 iteration outcomes

### 6. Build Success Condition
- [ ] If build passes after fixes, verify stage completes successfully
- [ ] Check that stage status is marked as "completed"
- [ ] Verify appropriate completion message

### 7. Limit Conditions
- [ ] Verify fix loop stops after maximum iterations (default 10)
- [ ] Check that stage completes with "max_iterations_reached" status when limit reached

## Stage 2 Core Builds - Resume Behavior

### 8. Interruption Recovery
- [ ] During stage execution, interrupt with Ctrl+C
- [ ] Verify progress is saved to progress.json
- [ ] Run again: `maestro convert run` 
- [ ] Verify stage resumes from correct iteration number

### 9. Pipeline Continuation
- [ ] When Stage 2 completes successfully, verify pipeline advances to Stage 3 (grow_from_main)

## Error Handling

### 10. Error Conditions
- [ ] Test with target that has no build system - verify fallback to basic build target
- [ ] Test with failing build - verify fix loop runs properly
- [ ] Test with successful build initially - verify stage completes immediately

## Documentation and Output

### 11. Command Output Verification
- [ ] Run: `maestro convert show` - verify Stage 2 information is shown when active/completed
- [ ] Check that verbose output shows proper iteration information
- [ ] Verify all stage artifacts are properly stored and accessible

## Clean-up

### 12. Test Environment Clean-up
- [ ] Run: `maestro convert reset` to clean up test pipeline
- [ ] Verify `.maestro/convert/` directory is cleaned up appropriately

## Expected Artifacts After Successful Stage 2

- [ ] `.maestro/convert/stages/core_builds/stage.json` - Stage state + config
- [ ] `.maestro/convert/stages/core_builds/runs/` - Links to build runs and fix runs  
- [ ] `.maestro/convert/stages/core_builds/diagnostics_baseline.json` - First failing run
- [ ] `.maestro/convert/stages/core_builds/progress.json` - Timeline of eliminated signatures
- [ ] Updated `.maestro/convert/pipeline_<id>.json` with Stage 2 completion status

## Final Verification
- [ ] Stage 2 completes successfully on a test project with compilation errors
- [ ] At least some signatures are eliminated during the process
- [ ] Progress is properly visible and trackable
- [ ] Resume functionality works correctly
- [ ] Conversion pipeline advances to Stage 3 upon completion

This checklist should be run after any changes to the conversion pipeline Stage 2 functionality to ensure it continues to work correctly.