# Maestro Prompt Contract Specification

## Overview

This document describes the structured prompt contract enforced throughout the Maestro system. All AI invocations must follow the standardized prompt format to ensure predictability, debuggability, and maintainability.

## Required Prompt Structure

Every AI prompt must contain all five required sections in the exact order specified:

```
[GOAL]
...

[CONTEXT]
...

[REQUIREMENTS]
...

[ACCEPTANCE CRITERIA]
...

[DELIVERABLES]
...
```

### Section Descriptions

- **GOAL**: The main objective or task to be accomplished
- **CONTEXT**: Background information, current state, and relevant context
- **REQUIREMENTS**: Specific requirements and constraints that must be met
- **ACCEPTANCE CRITERIA**: Conditions that define when the task is successfully completed
- **DELIVERABLES**: The specific outputs or results expected from the AI

### Section Rules

1. No section may be omitted
2. If a section is not applicable, it must contain the literal text "None"
3. Free-form text outside these sections is not allowed
4. Section headers must appear exactly as specified (case-sensitive)

## Centralized Prompt Builder

All prompts must be constructed using the `build_prompt()` function:

```python
def build_prompt(
    goal: str,
    context: str | None,
    requirements: str | None,
    acceptance: str | None,
    deliverables: str | None,
) -> str
```

This function ensures all required sections are present and properly formatted.

## Engine Role Declaration

Each prompt must include an engine role declaration in the format:

```
[ENGINE ROLE]
Engine: <engine_name>
Purpose: <purpose_description>
```

## Standardized Planner Templates

The system provides three standardized planner templates:

### Build Target Planner
- Returns JSON describing build steps, diagnostic commands, categories, and verification strategy
- Uses `build_build_target_planner_prompt()` function

### Fix Rulebook Planner
- Returns JSON describing trigger patterns, proposed fixes, verification steps, and escalation conditions
- Uses `build_fix_rulebook_planner_prompt()` function

### Conversion Pipeline Planner
- Returns JSON describing stages, entry/exit criteria, expected artifacts, and failure handling
- Uses `build_conversion_pipeline_planner_prompt()` function

## Persistence and Traceability

All AI invocations must include:

### Prompt Persistence
- Input prompts saved to: `sessions/<session>/inputs/<type>_<engine>_<timestamp>.txt`
- Saved before AI invocation
- Includes complete structured prompt

### Output Persistence
- AI outputs saved to: `sessions/<session>/outputs/<type>_<engine>_<timestamp>.txt`
- Saved after AI invocation
- Includes raw AI response

### Error/Exception Handling
- Even failed invocations must be logged
- Includes error details in output files

## Usage Examples

### Standard Worker Task
```python
prompt = build_prompt(
    goal="Implement the user registration functionality",
    context="Current user auth system, existing codebase structure, requirements document",
    requirements="User input validation, secure password storage, error handling, integration with existing auth system",
    acceptance="Users can register, passwords are securely stored, proper error messages shown",
    deliverables="Registration form, backend API endpoint, database schema updates, integration tests"
)
```

### Planner Task
```python
prompt = build_build_target_planner_prompt(
    root_task=task_description,
    summaries=worker_summaries,
    rules=project_rules,
    subtasks=existing_subtasks
)
```

## Validation

All prompts undergo validation before AI invocation:
- Checks that all five sections exist
- Ensures section order is correct
- Verifies no section is empty
- If validation fails, raises `ValueError` with clear error message
- Operation is aborted before calling AI

## Benefits

This standardized approach provides:

- **Predictability**: All prompts follow the same structure
- **Debuggability**: Prompts are saved and reproducible
- **Maintainability**: Easy to understand and modify prompt logic
- **Reliability**: Validation catches errors before AI invocation
- **Traceability**: All AI interactions are logged with context

## Migration

When migrating existing prompts to the new format:
1. Identify the goal of the prompt
2. Separate context from requirements
3. Define clear acceptance criteria
4. Specify expected deliverables
5. Use the `build_prompt()` function
6. Add engine role declaration
7. Ensure persistence is implemented