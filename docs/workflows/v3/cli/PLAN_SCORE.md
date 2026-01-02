# maestro plan score / plan recommend

Deterministic WorkGraph task scoring and prioritization for investor/purpose modes.

## Problem

After generating a WorkGraph with `maestro plan decompose`, users need to answer: **"What should I do first?"**

Without prioritization, large WorkGraphs become "backlog soup" with no clear next action.

## Solution

Add deterministic (no AI) scoring that ranks tasks by:
- **Investor mode**: Maximize ROI (impact/effort) and reduce risk-to-green
- **Purpose mode**: Maximize mission-alignment/user-value even when ROI is fuzzy
- **Default**: Balanced approach

## Commands

### maestro plan score

Score and rank all tasks in a WorkGraph.

```bash
maestro plan score <WORKGRAPH_ID> [OPTIONS]
```

**Options:**
- `--profile investor|purpose|default` - Scoring profile (default: default)
- `--json` - Output as JSON (sorted keys, stable)
- `-v, --verbose` - Show detailed scoring rationale

**Examples:**

```bash
# Basic scoring (default profile)
maestro plan score wg-20260101-a3f5b8c2

# Investor mode (ROI-first)
maestro plan score wg-20260101-a3f5b8c2 --profile investor

# Purpose mode (mission-first)
maestro plan score wg-20260101-a3f5b8c2 --profile purpose

# Verbose output with rationale
maestro plan score wg-20260101-a3f5b8c2 --profile investor -v

# JSON output for scripting
maestro plan score wg-20260101-a3f5b8c2 --json
```

**Output (human-readable):**

```
WorkGraph Scoring: wg-20260101-a3f5b8c2
Profile: investor
Total tasks: 15

Summary:
  Quick wins (score>=5, effort<=2): 3
  Risky bets (risk>=4): 2
  Purpose wins (purpose>=4): 5
  Top score: 8.0
  Avg score: 3.2

Top 10 Tasks (by score)
 1. [+8.0] TASK-003: Fix build blocker in CI pipeline
    impact: critical (5); effort: quick (2); risk: low (1); purpose: medium (3); investor_score: 8
 2. [+6.0] TASK-001: Add usage metrics tracking
    impact: high (4); effort: medium (3); risk: medium (2); purpose: high (4); investor_score: 6
...
```

### maestro plan recommend

Get top N recommended next actions from a WorkGraph.

```bash
maestro plan recommend <WORKGRAPH_ID> [OPTIONS]
```

**Options:**
- `--profile investor|purpose|default` - Scoring profile (default: investor)
- `--top N` - Number of recommendations (default: 3)
- `--print-commands` - Include primary command(s) in output

**Examples:**

```bash
# Top 3 recommendations (investor mode)
maestro plan recommend wg-20260101-a3f5b8c2

# Top 5 recommendations (purpose mode)
maestro plan recommend wg-20260101-a3f5b8c2 --profile purpose --top 5

# Show primary commands
maestro plan recommend wg-20260101-a3f5b8c2 --print-commands
```

**Output:**

```
Top 3 Recommendations (investor profile)
WorkGraph: wg-20260101-a3f5b8c2

1. [+8.0] TASK-003: Fix build blocker in CI pipeline
   impact: critical (5); effort: quick (2); risk: low (1); purpose: medium (3); investor_score: 8
   Primary command: pytest tests/integration/test_build.py

2. [+6.0] TASK-001: Add usage metrics tracking
   impact: high (4); effort: medium (3); risk: medium (2); purpose: high (4); investor_score: 6
   Primary command: python scripts/add_telemetry.py --dry-run

3. [+5.0] TASK-007: Update documentation for new API
   impact: medium (3); effort: trivial (1); risk: none (0); purpose: critical (5); investor_score: 5
   Primary command: make docs
```

## Scoring Profiles

### Investor Profile (ROI-first)

**Formula**: `(impact*3 + purpose) - (effort*2 + risk*2)`

**Prioritizes:**
- High-impact, low-effort tasks (quick wins)
- Risk mitigation (green builds, unblocked workflows)
- Measurable value delivery

**Use when:**
- Building product roadmap
- Sprint planning with limited resources
- Optimizing for velocity

### Purpose Profile (Mission-first)

**Formula**: `(purpose*3 + impact) - (effort + risk)`

**Prioritizes:**
- User-facing features
- Documentation and accessibility
- Strategic alignment over short-term ROI

**Use when:**
- Developer experience improvements
- Open-source community work
- Long-term strategic initiatives

### Default Profile (Balanced)

**Formula**: `(impact*2 + purpose) - (effort + risk)`

**Prioritizes:**
- Balanced mix of impact and purpose
- Moderate risk tolerance
- General-purpose prioritization

**Use when:**
- Not sure which mode fits
- Mixed backlog (features + fixes + docs)

## Scoring Fields

Tasks can have optional scoring fields (added manually or by AI):

```json
{
  "id": "TASK-001",
  "title": "Example task",
  "effort": {"min": 10, "max": 30},  // minutes
  "impact": 4,                         // 0-5
  "risk_score": 2,                     // 0-5
  "purpose": 5,                        // 0-5
  "tags": ["build", "test"]
}
```

**If fields are missing**, the scoring engine uses deterministic heuristics:

### Effort Inference
- Command count (more commands → more effort)
- `safe_to_execute=false` → add effort penalty
- Tags: `build`, `test` → higher effort
- Tags: `docs`, `cleanup` → lower effort

### Impact Inference
- Domain=issues + "blocker" in title → critical impact
- Tags: `build`, `fix`, `blocker`, `gate` → high impact
- Tags: `cleanup`, `refactor` → low impact
- Tasks with outputs (artifacts) → higher impact

### Risk Inference
- `safe_to_execute=false` → high risk
- Many outputs (>5 files) → higher risk
- Tags: `unsafe`, `experimental` → critical risk
- Tags: `readonly`, `docs` → low risk

### Purpose Inference
- Tags: `docs`, `user-facing`, `accessibility`, `ux` → critical purpose
- Tags: `build`, `internal`, `cleanup` → low purpose
- Keywords: "user", "customer", "documentation" → high purpose

## Integration with Ops Doctor

When using `maestro ops doctor -v`, the doctor will show top 3 recommendations from the latest WorkGraph (if one exists):

```bash
maestro ops doctor -v
```

**Output includes:**

```
RECOMMENDATIONS (INVESTOR PROFILE)
----------------------------------------------------------------------
Top 3 recommendations (investor profile)
  WorkGraph: wg-20260101-a3f5b8c2
  1. [+8.0] TASK-003: Fix build blocker in CI pipeline
     impact: critical (5); effort: quick (2); risk: low (1); purpose: medium (3); investor_score: 8
  2. [+6.0] TASK-001: Add usage metrics tracking
     impact: high (4); effort: medium (3); risk: medium (2); purpose: high (4); investor_score: 6
  3. [+5.0] TASK-007: Update documentation for new API
     impact: medium (3); effort: trivial (1); risk: none (0); purpose: critical (5); investor_score: 5

  Next steps:
    • maestro plan score wg-20260101-a3f5b8c2
    • maestro plan recommend wg-20260101-a3f5b8c2
```

## Determinism Guarantees

- **No AI**: All scoring is rule-based (no network calls)
- **Reproducible**: Same WorkGraph + same profile = same scores
- **Fast**: Scores 100+ tasks in <100ms
- **Bounded**: Top N output prevents information overload

## JSON Output Format

```json
{
  "profile": "investor",
  "ranked_tasks": [
    {
      "effort_bucket": 2,
      "impact": 5,
      "inferred_fields": ["effort", "impact"],
      "purpose": 3,
      "rationale": "impact: critical (5); effort: quick (2); risk: low (1); purpose: medium (3); investor_score: 8; (inferred: effort, impact)",
      "risk": 1,
      "score": 8.0,
      "task_id": "TASK-003",
      "task_title": "Fix build blocker in CI pipeline"
    }
  ],
  "summary": {
    "avg_score": 3.2,
    "profile": "investor",
    "purpose_wins": 5,
    "quick_wins": 3,
    "risky_bets": 2,
    "top_score": 8.0,
    "total_tasks": 15
  },
  "workgraph_id": "wg-20260101-a3f5b8c2"
}
```

## See Also

- [PLAN_DECOMPOSE.md](./PLAN_DECOMPOSE.md) - Create WorkGraphs
- [PLAN_ENACT.md](./PLAN_ENACT.md) - Materialize WorkGraphs into tracks
- [INVARIANTS.md](./INVARIANTS.md) - Scoring determinism invariants
