# Build Plan Interactive UX Checklist

This checklist verifies that the `maestro build plan` interactive experience provides proper user feedback and behaves like a real conversational planning instrument.

## Prerequisites
- [ ] Maestro is installed and accessible via `maestro` command
- [ ] Repository has a `.maestro/` directory
- [ ] At least one session exists

## Test Cases

### 1. Input Acknowledgement
- [ ] Execute: `maestro build plan --discuss` with a target
- [ ] Type a message and press Enter
- [ ] Verify: Maestro prints "Sending message to build planner…" immediately
- [ ] Type an empty message and press Enter
- [ ] Verify: Shows warning about empty input, doesn't contact AI
- [ ] Verify: No silence after pressing Enter

### 2. Planner Output Streaming
- [ ] Execute: `maestro build plan --discuss` (default mode, not quiet)
- [ ] Enter a prompt to the AI
- [ ] Verify: Planner output streams live to stdout
- [ ] Verify: Partial tokens/lines are visible as they arrive
- [ ] After AI responds, verify: "Build planner responded (XX chars)." message
- [ ] Execute with: `maestro build plan --discuss --quiet`
- [ ] Verify: No streaming output or confirmations shown
- [ ] Verify: All prompts and outputs still saved to disk

### 3. Prompt & Output Persistence
- [ ] Execute: `maestro build plan --discuss` and interact
- [ ] Verify: Prompts saved to `.maestro/build/inputs/build_plan_<timestamp>.txt`
- [ ] Verify: Raw outputs saved to `.maestro/build/outputs/build_plan_<engine>_<timestamp>.txt`
- [ ] Execute with: `maestro build plan --discuss --verbose`
- [ ] Verify: File paths are explicitly printed
- [ ] Verify: Both one-shot and discuss modes save to same format

### 4. `/done` Finalization
- [ ] Execute: `maestro build plan --discuss`
- [ ] Type: `/done` as a command
- [ ] Verify: Shows "Finalizing build target configuration..."
- [ ] Verify: The planner returns valid JSON only
- [ ] Verify: JSON is parsed successfully
- [ ] Verify: Schema is validated properly
- [ ] Verify: Build target is created with updated plan
- [ ] Type invalid JSON response from planner
- [ ] Verify: Clear error message about JSON parsing
- [ ] Verify: Shows AI response preview
- [ ] Type schema-invalid JSON
- [ ] Verify: Clear error about required fields

### 5. `/abort` Command
- [ ] Execute: `maestro build plan --discuss`
- [ ] Type: `/quit` as a command
- [ ] Verify: Exits without creating build target
- [ ] Verify: Shows "Exiting without creating build target."

### 6. One-Shot Mode
- [ ] Execute: `maestro build plan --one-shot`
- [ ] Verify: Single AI call with no conversation loop
- [ ] Verify: Same prompt contract used
- [ ] Verify: Same JSON validation applied
- [ ] Verify: Proper confirmations and error handling

### 7. No Silent Failures
- [ ] Execute with invalid session
- [ ] Verify: Clear error message about session not existing
- [ ] Cause AI to return malformed JSON
- [ ] Verify: Clear error about JSON parsing, shows where it failed
- [ ] Cause all planners to fail
- [ ] Verify: Clear error message about planner failures
- [ ] Execute when planner engines unavailable
- [ ] Verify: Shows where to check logs and what to try next

### 8. Mode Clarity
- [ ] Execute without --one-shot or --discuss flags
- [ ] Verify: User is prompted to choose between modes
- [ ] Execute with --one-shot
- [ ] Verify: Only one AI call made
- [ ] Execute with --discuss
- [ ] Verify: Conversational loop initiated
- [ ] Verify: User always knows which mode they are in

### 9. Quiet Mode Behavior
- [ ] Execute: `maestro build plan --discuss --quiet`
- [ ] Verify: No streaming output to terminal
- [ ] Verify: No confirmation messages printed
- [ ] Verify: All prompts and responses still saved to disk
- [ ] Verify: Final target still gets created properly

### 10. Streaming Control
- [ ] Execute: `maestro build plan --discuss -o` (or --stream-ai-output)
- [ ] Verify: Planner output streams in real-time
- [ ] Execute: `maestro build plan --discuss -q` (or --quiet)
- [ ] Verify: No output to terminal (but still saved to files)

## Success Criteria
- [ ] User input always gets immediate acknowledgment
- [ ] Planner output streams visibly by default
- [ ] `--quiet` suppresses terminal output but preserves logs
- [ ] `/done` reliably produces valid, parsed JSON
- [ ] Invalid planner output is caught with clear error messages
- [ ] No silent failures - all paths provide feedback
- [ ] Both one-shot and discuss modes work properly
- [ ] All files are saved in correct locations with proper naming

## Error Scenarios to Test
- [ ] Enter invalid JSON in AI response (verify proper error handling)
- [ ] AI returns no JSON at all (verify detection and error)
- [ ] Missing required fields in response (verify validation)
- [ ] Planner engine unavailable (verify graceful fallback)
- [ ] Network issues during AI call (verify error handling)
- [ ] Insufficient permissions to save files (verify error message)

## Notes
- If `/done` doesn't work properly, check that the AI is returning valid JSON
- If streaming isn't working, verify engine configuration supports streaming
- If files aren't being saved, check `.maestro/build/inputs` and `.maestro/build/outputs` directories