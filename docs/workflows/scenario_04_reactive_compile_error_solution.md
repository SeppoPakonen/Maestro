# WF-04: Reactive compile error → Solutions match → immediate solution-task

## Metadata
```
id: WF-04
title: Reactive compile error → Solutions match → immediate solution-task
tags: [build, compile-error, solutions, reactive, issues, tasks, dependency, work-loop]
entry_conditions: 
  - Operator runs `maestro make build` (or equivalent build command)
  - Build process fails with compiler error
  - Error text contains patterns that may match existing solution rules
exit_conditions: 
  - Issue created for the build error
  - If solution matches: high-priority task created to try solution
  - If solution fails: fallback task created for normal investigation
artifacts_created: 
  - Issue file in docs/issues/
  - Task file in docs/tasks/ (if solution matches)
  - Fallback task file (if solution attempt fails)
failure_semantics: 
  - If solution matching fails: proceed to normal issue workflow
  - If solution application fails: create fallback task for normal fix
related_commands: 
  - `maestro make build` - triggers the workflow
  - `maestro work issue` - processes the created issue
  - `maestro solutions` - manages solution rules
notes_on_scope: 
  - This scenario covers using existing Solutions, not editing them
  - Does not cover editing Solutions; that is a later scenario
```

## Narrative Flow

### Phase 1: Build Failure Detection
1. Operator runs `maestro make build` (or current equivalent)
2. Build starts and fails with a compile error
3. Maestro always creates an Issue (compile diagnostic) to capture the error

### Phase 2: Solution Matching
4. Maestro runs Solutions matcher against the error text
5. If match found:
   - Creates a Task: "Try Solution <X> for Issue <Y>"
   - Makes it high priority / blocker-style so it surfaces first in `maestro work`
6. If no match found:
   - Continues with normal issue workflow

### Phase 3: Solution Application
7. When the solution-task runs:
   - Applies the solution's prescribed steps
   - Re-runs build
   - If build succeeds: continues normal flow
   - If build still fails:
     - Creates a new Task (or replaces/branches) for "Fix as a novel problem"
     - Ensures linkage: Issue ↔ (SolutionAttemptTask) ↔ (FallbackTask)
     - Continues work loop

## Clarification of Intent

This workflow exists because:
- Many C++ compiler errors are non-intuitive and lead AI astray
- This mechanism is deliberately "reactive" and not "smart"
- It is meant to reduce time-to-first-correct-fix for repeated patterns
- It provides a fast rule-based remediation loop before deeper analysis

## Command Contracts

### `maestro make build`
- **Purpose**: Execute build process with error capture and solution matching
- **Inputs**: Package name, build method, configuration options
- **Outputs**: 
  - Issue creation for build errors
  - Solution attempt task creation (when matches found)
- **Hard stops vs recoverable states**: Build failure is recoverable; creates issues and solution tasks

### `maestro solutions`
- **Purpose**: Manage solution rules that match against build errors
- **Inputs**: Solution definitions with keywords, regex patterns, and context rules
- **Outputs**: Solution records that can be matched against issues
- **Hard stops vs recoverable states**: Solution definition errors are recoverable; malformed rules are skipped

### `maestro work issue`
- **Purpose**: Process an issue, potentially using matched solutions
- **Inputs**: Issue ID, potential solution matches
- **Outputs**: Work session execution with solution application or fallback
- **Hard stops vs recoverable states**: Solution application failure triggers fallback workflow

## Tests Implied by This Scenario

### Unit Tests
- Solution matching (keyword/pattern): Verify keywords in error text trigger matches
- Compile error parsing normalization: Ensure error formats are correctly parsed
- "Match found ⇒ creates solution attempt task": When solutions match, tasks are created
- "Match not found ⇒ creates normal investigation task": When no solutions match, normal workflow continues
- "Attempt failed ⇒ creates fallback task": When solution application fails, fallback is created

### Integration Fixtures
- A fixture repo that deterministically triggers a known error string
- A fixture solution rule that matches it
- Verify task ordering and linkage (graph edges) between issue, solution task, and fallback task