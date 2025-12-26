# Discuss OPS Contract (JSON -> OPS -> CLI)

## Purpose

Define a strict JSON contract for discuss sessions. The contract yields OPS (operations) that map 1:1 to Maestro CLI actions and internal handlers. Invalid JSON hard-fails and applies no OPS.

## What Is an OPS?

An OPS is a machine-executable operation that corresponds directly to a CLI command (and, when implemented, an internal handler). OPS are the unit of application for discuss output.

## Canonical JSON Envelope

```json
{
  "ops": [
    {
      "op": "task.create",
      "args": { "title": "Fix build", "phase_id": "PH-01" },
      "hints": { "reason": "build failed", "confidence": 0.7 },
      "guards": ["REPO_TRUTH_IS_DOCS_MAESTRO"]
    }
  ],
  "summary": "Create a build-fix task"
}
```

## Rules

1. `op` must map to an entry in `docs/workflows/v2/reports/command_trace_glossary.md`.
2. `args` must be validated for required fields and types before apply.
3. `hints` are optional, non-authoritative metadata.
4. `guards` are evaluated before apply; if any guard fails, the entire apply fails.
5. Invalid JSON or schema mismatch is a hard fail. No OPS are applied.

## Equivalence and Execution

Each OPS maps to:

- a CLI command (primary interface)
- an internal handler (when implemented)
- a store mutation set (repo truth, home hub, IPC mailbox)

This makes discuss output executable and auditable.

## Canonical OP Namespaces

- `runbook.*`, `workflow.*`
- `track.*`, `phase.*`, `task.*`
- `repo.resolve.*`, `repo.conf.*`, `build.*`, `tu.*`, `convert.*`
- `issues.*`, `solutions.*`
- `wsession.*`

## JSON Contract Gate

If the discuss response is not a **single valid JSON object** matching the schema, Maestro must hard-fail at `JSON_CONTRACT_GATE` and apply no OPS. The user must retry or resume to proceed.
