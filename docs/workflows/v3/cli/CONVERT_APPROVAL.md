# Convert Plan Approval Workflow (v3)

This workflow enforces plan approval before `maestro convert run` executes. It makes the convert pipeline auditable and deterministic: plan -> decision -> run -> ledger.

## Canonical commands

- `maestro convert plan <PIPELINE_ID>`
- `maestro convert plan <PIPELINE_ID> <ACTION>`
- `maestro convert plan <ACTION> <PIPELINE_ID>`
- `maestro convert plan show <PIPELINE_ID>`
- `maestro convert plan approve <PIPELINE_ID> [--reason <TEXT>]`
- `maestro convert plan reject <PIPELINE_ID> [--reason <TEXT>]`
- `maestro convert run <PIPELINE_ID> [--ignore-gates]`

Actions: `show`, `approve`, `reject`, `status`, `history`.

## State machine

- `draft` or `planned` -> `approved` or `rejected`
- `approved` -> `running` -> `done` or `failed`
- `rejected` blocks run unless `--ignore-gates`

## Gate

- `CONVERT_PLAN_NOT_APPROVED` blocks `convert run` unless `--ignore-gates` is provided.

## Storage (repo-local, JSON only)

All convert pipeline state lives under `./docs/maestro/convert/`:

- `pipelines/<PIPELINE_ID>/meta.json`
  - `status`: `draft|planned|approved|rejected|running|done|failed`
  - `created_at`, `updated_at`
  - `source_repo`, `target_repo`
- `pipelines/<PIPELINE_ID>/plan.json`
  - `steps`, `artifacts`, `expected_outputs`
- `pipelines/<PIPELINE_ID>/decision.json`
  - `decision`: `approved|rejected`
  - `reason`, `decided_by`, `decided_at`
- `pipelines/<PIPELINE_ID>/runs/<RUN_ID>/run.json`
  - status, timestamps, inputs, outputs, override flags
- `pipelines/<PIPELINE_ID>/runs/<RUN_ID>/diff.patch` (optional)

## Run behavior

- `convert run` requires plan status `approved` unless `--ignore-gates`.
- `--ignore-gates` prints a warning and logs the override in `run.json`.
- Cross-repo runs write artifacts only into the target repo `docs/maestro/**`.
- Repo locks are acquired in order: source, then target.

## Ledger

Behavioral changes are recorded in `docs/workflows/v3/IMPLEMENTATION_LEDGER.md`.
