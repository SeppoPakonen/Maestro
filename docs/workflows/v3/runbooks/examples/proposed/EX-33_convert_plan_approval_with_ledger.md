# EX-33: Convert Plan Approval With Ledger

**Scope**: Enforce convert plan approval before run, log decisions, and record audit artifacts.
**Outcome**: Unapproved runs are blocked by gate; approved runs write run artifacts in target repo.

---

## Preconditions

- Repo initialized with `maestro init`
- Source repo has AST capability (or mocked plan data)
- Repo truth stored under `docs/maestro/`

## Gates / IDs / Stores

- Gates: `CONVERT_PLAN_NOT_APPROVED`
- IDs: `<PIPELINE_ID>`, `<RUN_ID>`
- Stores: `docs/maestro/convert/`, `docs/workflows/v3/IMPLEMENTATION_LEDGER.md`

---

## Runbook Steps

| Step | Command | Intent | Expected | Gates | Stores |
|------|---------|--------|----------|-------|--------|
| 1 | `maestro convert add demo-pipe` | Create pipeline | Pipeline metadata + plan skeleton created | - | `docs/maestro/convert/` |
| 2 | `maestro convert plan demo-pipe` | Generate/refresh plan | Plan saved, status planned | - | `docs/maestro/convert/` |
| 3 | `maestro convert plan show demo-pipe` | Inspect plan | Plan details printed | - | `docs/maestro/convert/` |
| 4 | `maestro convert plan approve demo-pipe --reason "ready to run"` | Approve plan | Decision recorded, status approved | - | `docs/maestro/convert/` |
| 5 | `maestro convert run demo-pipe` | Execute conversion | Run recorded under target repo `docs/maestro/` | - | `docs/maestro/convert/` |
| 6 | `rg "Convert plan approval" docs/workflows/v3/IMPLEMENTATION_LEDGER.md` | Verify ledger entry | Ledger reflects convert approval behavior | - | `docs/workflows/v3/IMPLEMENTATION_LEDGER.md` |

---

## Expected failure (gate)

Attempting to run without approval should block:

```
$ maestro convert run demo-pipe
============================================
GATE: CONVERT_PLAN_NOT_APPROVED
============================================
Pipeline demo-pipe is not approved (status: planned).
Approve or reject the plan before running:
  maestro convert plan approve demo-pipe --reason "..."
  maestro convert plan reject demo-pipe --reason "..."
Or bypass gates explicitly:
  maestro convert run demo-pipe --ignore-gates
```

---

## Outcomes

- Plan decisions recorded in `decision.json`
- Run artifacts in `runs/<RUN_ID>/run.json`
- Gate message printed when plan not approved

---

## Trace (YAML)

```yaml
trace:
  example: EX-33
  steps:
    - step: create_pipeline
      command: "maestro convert add demo-pipe"
      gates: []
      stores: [CONVERT_PIPELINES]
    - step: plan_generate
      command: "maestro convert plan demo-pipe"
      gates: []
      stores: [CONVERT_PIPELINES]
    - step: plan_show
      command: "maestro convert plan show demo-pipe"
      gates: []
      stores: [CONVERT_PIPELINES]
    - step: plan_approve
      command: "maestro convert plan approve demo-pipe --reason \"ready to run\""
      gates: []
      stores: [CONVERT_PIPELINES]
    - step: run
      command: "maestro convert run demo-pipe"
      gates: []
      stores: [CONVERT_PIPELINES]
```
