"""
Semantic Integrity System - Usage Guide
=======================================

This document explains how to use the semantic integrity system for conversion tasks.

## Overview

The semantic integrity system detects meaning loss during conversion and ensures
that the converted code maintains the same purpose and behavior as the original.

## CLI Commands

### View Semantic Check Results
```bash
# List all semantic check results
maestro convert semantics list

# Show details for a specific task
maestro convert semantics show <task_id>

# Accept a semantic change after human review
maestro convert semantics accept <task_id> --note "Optional explanation"

# Reject a semantic change after human review  
maestro convert semantics reject <task_id> --note "Explanation for rejection"
```

## Automatic Risk Classification

The system automatically classifies risks based on:
- Semantic equivalence level (high, medium, low, unknown)
- Confidence in the conversion
- Risk flags (control_flow, memory, concurrency, io, lifetime)
- Need for human review

Risk levels:
- block: Pipeline stops due to low semantic equivalence
- pause: Awaits human confirmation if --accept-semantic-risk not provided
- escalate: High-risk patterns with low confidence
- continue: Safe to proceed

## Configuration

### Accepting Semantic Risk
To bypass human review prompts:
```bash
export MAESTRO_ACCEPT_SEMANTIC_RISK=true
# OR use command line flags in future implementations
```

### Thresholds
Semantic drift thresholds can be configured via the SemanticIntegrityChecker:
- Max 20% low equivalence files
- Max 10 unresolved warnings
- Max 30% control flow risk
- Max 20% memory risk

## Integration Points

- **Execution Engine**: Runs semantic checks after file tasks
- **Planner**: Considers semantic warnings when generating plans
- **Conversion Memory**: Records semantic issues and decisions
- **Realize Worker**: Provides file content for analysis

## Data Storage

Semantic results are stored in `.maestro/convert/semantics/`:
- `task_<id>.json`: Individual task semantic analysis
- `summary.json`: Aggregated semantic health metrics
- `open_issues.json`: Cross-file consistency issues

## JSON Response Format

For each semantic check, AI returns (mock implementation provides heuristic results):

```json
{
  "semantic_equivalence": "high | medium | low | unknown",
  "confidence": 0.0,
  "preserved_concepts": ["..."],
  "changed_concepts": ["..."],
  "lost_concepts": ["..."],
  "assumptions": ["..."],
  "risk_flags": ["control_flow", "memory", "concurrency", "io", "lifetime"],
  "requires_human_review": true
}
```
"""