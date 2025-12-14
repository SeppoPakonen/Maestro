# Conversion Pipeline Stage 1 - Regression Checklist

## Overview
This checklist verifies the proper functioning of Stage 1 (Overview) of the conversion pipeline. Complete this checklist after any changes to ensure the core functionality remains intact.

## Pre-Test Setup
- [ ] Ensure you have a directory with source code to convert
- [ ] Verify that your AI engines are properly configured in settings
- [ ] Confirm Maestro is installed and accessible from command line

## Core Functionality Tests

### 1. Pipeline Creation (`maestro convert new`)
- [ ] Run: `maestro convert new <source_path> <target_path> --name "Test Conversion"`
- [ ] Verify pipeline.json is created in `.maestro/convert/`
- [ ] Check that the pipeline contains the 4 required stages (overview, core_builds, grow_from_main, full_tree_check)
- [ ] Confirm initial stage status is "pending" for all stages
- [ ] Verify the "active_stage" is set to "overview"
- [ ] Check that storage directories are created:
  - [ ] `.maestro/convert/inputs/`
  - [ ] `.maestro/convert/outputs/`
  - [ ] `.maestro/convert/logs/`
  - [ ] `.maestro/convert/stages/`

### 2. Pipeline Execution (`maestro convert run`)
- [ ] Run: `maestro convert run`
- [ ] Confirm the overview stage executes without errors
- [ ] Verify stage status changes from "pending" to "running" to "completed"
- [ ] Check that inventory file is created: `.maestro/convert/stages/overview_inventory.json`
- [ ] Confirm overview JSON is created: `.maestro/convert/stages/overview.json`
- [ ] Verify prompt file is saved in `.maestro/convert/inputs/`
- [ ] Verify output file is saved in `.maestro/convert/outputs/`
- [ ] Check that `active_stage` advances to "core_builds"
- [ ] Verify the inventory contains:
  - [ ] Repository root path
  - [ ] Top-level directories
  - [ ] File counts by extension
  - [ ] Detected build files
  - [ ] Guessed entrypoints
  - [ ] Git information (if applicable)

### 3. Pipeline Status (`maestro convert status`)
- [ ] Run: `maestro convert status`
- [ ] Verify display shows pipeline name, source, target
- [ ] Check that stage progress is shown correctly (✓ for completed, ○ for pending, → for running)
- [ ] Confirm key file locations are displayed
- [ ] Verify storage directory paths are shown

### 4. Pipeline Details (`maestro convert show`)
- [ ] Run: `maestro convert show`
- [ ] Verify detailed pipeline information is displayed
- [ ] Check that stage details with timestamps are shown
- [ ] Confirm overview plan details are displayed when available:
  - [ ] Repository summary
  - [ ] Risks identified
  - [ ] Mapping plan
  - [ ] Stage entry/exit criteria
- [ ] Verify inventory details are displayed:
  - [ ] File counts by extension
  - [ ] Build files found
  - [ ] Entrypoints found
  - [ ] Git information

### 5. Rerun Behavior
- [ ] Run: `maestro convert run` again on a completed overview stage
- [ ] Verify the command advances to the next stage (core_builds)
- [ ] Or, run a specific stage: `maestro convert run --stage overview`
- [ ] Confirm stage can be rerun and status updates correctly

### 6. Error Handling
- [ ] Try running with invalid source path
- [ ] Verify appropriate error messages are shown
- [ ] Check that pipeline status reflects errors if they occur
- [ ] Verify that the system recovers and allows reruns after fixing issues

## Verification Checklist
- [ ] All four commands work as expected: `new`, `run`, `status`, `show`
- [ ] Stage state transitions work correctly (pending → running → completed)
- [ ] Files are saved to correct locations with proper naming
- [ ] AI planner is called and generates valid JSON response
- [ ] Inventory contains appropriate repository information
- [ ] Next stage is properly activated after current stage completes
- [ ] No stack traces in normal operation (only in verbose mode if needed)

## Expected Artifacts After Successful Stage 1
- [ ] `.maestro/convert/pipeline_<id>.json` - Main pipeline state
- [ ] `.maestro/convert/stages/overview_inventory.json` - Repository inventory
- [ ] `.maestro/convert/stages/overview.json` - Planning output from AI
- [ ] `.maestro/convert/inputs/overview_<timestamp>.txt` - Planner prompt
- [ ] `.maestro/convert/outputs/overview_<engine>_<timestamp>.txt` - Raw AI output
- [ ] Pipeline status shows overview as completed and core_builds as active

## Clean Up
- [ ] Remove test pipeline after verification if needed (optional)

This checklist should be run after any changes to the conversion pipeline functionality to ensure Stage 1 continues to work correctly.