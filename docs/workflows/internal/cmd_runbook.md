# Runbook Command - Internal Documentation

## Overview

The `maestro runbook` command provides a lower-friction, narrative-first modeling layer for describing system procedures before formalization into workflow graphs. It serves as a "runbook-first bootstrap" positioned between `maestro init` and `maestro workflow` in the command hierarchy.

## Positioning

```
maestro init → maestro runbook → maestro workflow → maestro repo
```

This positioning allows users to:
1. Initialize a project (`init`)
2. Paint the product/system using narrative runbooks (`runbook`)
3. Formalize into workflow graphs (`workflow`)
4. Manage repo truth (`repo`)

## Data Model

### Storage Layout
```
./docs/maestro/runbooks/
├── index.json                 # Index of all runbooks
├── items/
│   ├── <runbook-id>.json     # Individual runbook files
│   └── ...
└── exports/
    ├── <runbook-id>.md       # Exported markdown
    ├── <runbook-id>.puml     # Exported PlantUML
    ├── <runbook-id>.svg      # Rendered SVG
    └── ...
```

### JSON Schema

#### index.json
```json
[
  {
    "id": "string",
    "title": "string",
    "tags": ["string"],
    "status": "proposed|approved|deprecated",
    "updated_at": "ISO8601"
  }
]
```

#### items/<runbook-id>.json
```json
{
  "id": "string",
  "title": "string",
  "status": "proposed|approved|deprecated",
  "scope": "product|user|manager|ui|code|reverse_engineering",
  "tags": ["string"],
  "context": {
    "source_program": "string (optional)",
    "target_project": "string (optional)"
  },
  "steps": [
    {
      "n": "integer",
      "actor": "string",
      "action": "string",
      "details": "string (optional)",
      "expected": "string",
      "variants": ["string (optional)"]
    }
  ],
  "links": {
    "workflows": ["string"],
    "issues": ["string"],
    "tasks": ["string"]
  },
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

## Command Surface

### Top-level Commands

- `maestro runbook list [--status STATUS] [--scope SCOPE] [--tag TAG]`
- `maestro runbook show <id>`
- `maestro runbook add --title TITLE [--scope SCOPE] [--tag TAG]...`
- `maestro runbook edit <id> [--title TITLE] [--status STATUS] [--scope SCOPE] [--tag TAG]...`
- `maestro runbook rm <id> [--force]`

### Step Management Commands

- `maestro runbook step-add <id> --actor ACTOR --action ACTION --expected EXPECTED [--details DETAILS] [--variants VARIANT]...`
- `maestro runbook step-edit <id> <n> [--actor ACTOR] [--action ACTION] [--expected EXPECTED] [--details DETAILS]`
- `maestro runbook step-rm <id> <n>`
- `maestro runbook step-renumber <id>`

### Export Commands

- `maestro runbook export <id> --format md|puml [--out PATH]`
- `maestro runbook render <id> [--out PATH]` (PUML to SVG)

### AI Integration

- `maestro runbook discuss <id>` (placeholder for AI orchestration)

## Aliases

- `runbook` → `runba`, `rb`
- Subcommands follow standard conventions (list→ls, show→sh, etc.)

## Use Cases

### 1. Greenfield Product Modeling
User starts with narrative descriptions before formal workflow graphs:
```bash
maestro runbook add --title "User Registration Flow" --scope user
maestro runbook step-add user-registration-flow --actor user --action "Navigate to signup" --expected "Signup form displayed"
maestro runbook export user-registration-flow --format md
```

### 2. Reverse Engineering
User models an existing program before re-implementation:
```bash
maestro runbook add --title "Legacy Auth System" --scope reverse_engineering \
  --source-program "Old System v1.2" --target-project "New Auth Service"
maestro runbook step-add legacy-auth-system --actor system --action "Check session cookie" \
  --expected "User session validated or rejected"
```

### 3. Manager/Product Perspective
Product managers describe desired behavior before technical implementation:
```bash
maestro runbook add --title "Checkout Process" --scope product --tag ux --tag critical
maestro runbook step-add checkout-process --actor user --action "Review cart" \
  --expected "Cart summary with totals displayed"
```

## Integration with Workflow

Runbooks serve as a stepping stone to workflow graphs. Future enhancements may include:
```bash
maestro workflow create --from-runbook <runbook-id>
```

This would convert runbook steps into formal workflow nodes.

## Storage Conventions

1. **No .maestro directory**: All data stored in `./docs/maestro/`
2. **JSON is authoritative**: Markdown and PUML exports are non-authoritative
3. **Index for performance**: Avoids scanning filesystem for list operations
4. **Stable IDs**: Generated from titles, collision-resistant with numeric suffixes

## Future Enhancements

1. **AI Discuss Integration**: Full integration with existing discuss mechanism for step refinement
2. **Workflow Conversion**: Automatic conversion from runbook to workflow graph
3. **Variant Execution**: Support for testing multiple step variants
4. **Cross-linking**: Deep integration with issues, tasks, and workflow graphs
