# Human-Authored Conversion Playbooks

## Overview

Conversion playbooks are structured, versioned, human-authored guides that tell Maestro how to think about a class of conversions before any AI is invoked. Playbooks let you:

- Encode architectural intent once
- Prevent planners from "reinventing" decisions
- Standardize conversions across repos
- Reduce AI hallucination by narrowing the solution space
- Make conversions reproducible across teams and time

## Directory Structure

```
.maestro/playbooks/
  cpp_to_c/                # Example playbook directory
    playbook.json          # Required - main playbook definition
    glossary.json          # Optional - terminology definitions
    constraints.json       # Optional - additional constraint details
    examples.md            # Optional - example implementations
```

## Playbook Schema

The `playbook.json` file contains the following fields:

```json
{
  "id": "cpp_to_c",
  "title": "C++ → C lowering (no runtime)",
  "version": "1.0",
  "applies_to": {
    "source_language": "C++",
    "target_language": "C"
  },
  "intent": "high_to_low_level",
  "principles": [
    "No hidden runtime",
    "Explicit memory ownership",
    "No exceptions; use error codes",
    "No templates in output"
  ],
  "required_losses": [
    "RAII",
    "exceptions", 
    "templates"
  ],
  "forbidden_constructs": {
    "target": ["new", "delete", "throw", "try", "catch"]
  },
  "preferred_patterns": [
    "init/cleanup pairs",
    "opaque structs", 
    "manual vtables"
  ],
  "checkpoint_policy": {
    "after_files": 5,
    "on_semantic_loss": true
  },
  "validation_policy": {
    "mode": "vectors_only",
    "require_behavior_envelope": true
  }
}
```

## CLI Commands

### List Playbooks
```bash
maestro convert playbook list
```

### Show Playbook Details
```bash
maestro convert playbook show <id>
```

### Bind a Playbook
```bash
maestro convert playbook use <id>
```

### Override a Playbook Violation
```bash
maestro convert playbook-override <task_id> --violation-type forbidden_construct --reason "Required for legacy compatibility"
```

## Integration Points

### Planner
- The planner checks for an active playbook binding before generating plans
- Applies checkpoint policies from the playbook
- Enforces intent consistency

### Worker
- Checks playbook for forbidden constructs in AI output
- Rejects outputs containing forbidden constructs unless overridden

### Semantic Diff
- Treats required losses as expected rather than suspicious
- Flags missing required losses as suspicious
- Treats violations of forbidden constructs as hard errors

## Override Mechanism

When a playbook constraint is violated, the conversion will fail unless:

1. An override is explicitly recorded using `maestro convert playbook-override`
2. The violation is for an acceptable reason
3. The override is properly documented

All overrides are auditable and recorded in `.maestro/convert/playbook_overrides.json`.

## Example Usage

```bash
# List available playbooks
maestro convert playbook list

# Use a specific playbook
maestro convert playbook use cpp_to_c

# Plan with playbook constraints
maestro convert plan --rehearse

# Run conversion (will enforce playbook rules)
maestro convert run --rehearse

# If violations occur, you can override with a reason
maestro convert playbook-override task_abc123 --violation-type forbidden_construct --reason "Required for legacy compatibility"
```