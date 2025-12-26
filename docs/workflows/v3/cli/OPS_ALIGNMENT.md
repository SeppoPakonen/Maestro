# OPS Alignment Note

OPS are machine-executable operations that must map 1:1 to CLI endpoints.

## Alignment rules

- OPS namespaces match command namespaces (`task.*` -> `maestro task ...`).
- OPS verbs match canonical verbs (add/edit/rm/show/list/run/validate/discuss).
- Any op without a CLI endpoint is a design smell and must be tracked in CLI gaps.

## Examples

- `workflow.node.add` -> `maestro workflow node add`.
- `task.set.status` -> `maestro task set status <id> <status>`.
- `issues.link.solution` -> `maestro issues link solution <issue> <solution>`.

## Gate alignment

- OPS that mutate repo truth should require `REPO_TRUTH_DOCS_MAESTRO` guards.
- Read-only OPS should be clearly marked in CLI help and in trace metadata.
