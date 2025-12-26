# cmd_workflow.md - Workflow Command Spec (v2)

## Synopsis
- Command: `workflow`
- Subcommands: init, list, show, node add|rm|edit, edge add|rm|edit, validate, export, render, discuss
- Example invocations:
  - `maestro workflow init product_spec`
  - `maestro workflow node add --graph product_spec --layer manager_intent --id MI-001 --title "Product intent"`
  - `maestro workflow export --format puml --graph product_spec`

## Purpose
Provide a headless workflow graph editor that bootstraps canonical specs for greenfield work. The workflow graph is the first-class spec layer for mapping manager intent, user intent, interface decisions, and code intent before plan/track/phase/task execution.

## Data Location (Repo Truth)
- Workflow graphs live under `./docs/maestro/workflows/<name>.json`
- Repo truth for workflows is JSON-only (`REPO_TRUTH_FORMAT_IS_JSON`)
- Repo truth lives under `./docs/maestro/` (`REPO_TRUTH_IS_DOCS_MAESTRO`)

## Subcommand Sketch (Spec)
- `workflow init|list|show`
- `workflow node add|rm|edit`
- `workflow edge add|rm|edit`
- `workflow validate`
- `workflow export --format puml`
- `workflow render --format svg` (calls `/usr/bin/plantuml -tsvg`)
- `workflow discuss` (AI orchestrates the same subcommands; optional)

## Workflow Layers
Workflow graphs can include the following layered nodes:
- `manager_intent`
- `user_intent`
- `interface`
- `code`

## Gates / Invariants
- `REPO_TRUTH_FORMAT_IS_JSON`
- `REPO_TRUTH_IS_DOCS_MAESTRO`
- Branch guard: workflow graphs must not mutate across a branch switch

## Internal Flow (Coarse)
1. Parse CLI args and detect `workflow` command
2. Dispatch to subcommand handler
3. Read workflow graph JSON (if needed)
4. Apply node/edge edits or validation
5. Write updated workflow graph JSON
6. Optionally export to PlantUML
7. Optionally render PlantUML to SVG using `/usr/bin/plantuml -tsvg`

## Failure Semantics
- Missing or invalid graph IDs result in a hard stop with usage hints
- Validation failures block write operations
- Export/render failures should not mutate repo truth

## Outputs
- Lists and summaries to stdout
- Updated workflow graph JSON in repo truth
- Optional PlantUML/SVG artifacts when requested
