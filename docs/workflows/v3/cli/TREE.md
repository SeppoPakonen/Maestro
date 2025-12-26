# v3 CLI Tree (Normative)

This is the proposed v3 command tree. Verbs are short; keyword namespaces carry specificity.

## Top-level

- `maestro init`
- `maestro runbook {list|show|add|edit|rm|step|export|discuss}`
- `maestro workflow {list|show|add|edit|rm|node|edge|validate|export|render|discuss}`
- `maestro repo {resolve|conf|show|hub|make}`
- `maestro track {list|show|add|edit|rm|discuss}`
- `maestro phase {list|show|add|edit|rm|discuss}`
- `maestro task {list|show|add|edit|rm|discuss|link|set}`
- `maestro issues {list|show|add|edit|rm|discuss|link|ignore}`
- `maestro solutions {list|show|add|edit|rm|match|discuss}`
- `maestro work {start|resume|pause|stop|status|task|spawn}`
- `maestro wsession {list|show|breadcrumb|close}`
- `maestro discuss` (router)
- `maestro ai {list|use|run|resume}`
- `maestro settings {list|show|set|reset}`
- `maestro ops {list|run|doctor|commit}`
- `maestro tu {build|query|refactor}`
- `maestro convert {list|show|add|edit|rm|run}`
- `maestro select {toolchain}`

## Selected subtrees

- `maestro repo resolve {lite|deep}`
- `maestro repo conf {show|select-default target}`
- `maestro repo hub {find|list|link}`
- `maestro workflow node {add|edit|rm}`
- `maestro workflow edge {add|edit|rm}`
- `maestro runbook step {add|edit|rm|list}`
- `maestro task link {phase|issue|solution}`
- `maestro task set {status|dependency}`
- `maestro issues link {task|solution}`
- `maestro wsession breadcrumb {add|list}`
- `maestro ops commit {suggest|create}`
- `maestro select toolchain {list|show|set|unset|detect|export}`

## Legacy/problem commands

- `understand` -> fold into `repo resolve` + `runbook add` or `runbook discuss`.
- `rules` -> fold into `solutions` (preferred) or `repo conf` (secondary). Choose `solutions` for policy rules.
- `resume` -> fold into `work resume` (primary) and `ai resume` (if engine-specific).
- `session` -> deprecate in favor of `wsession` and `ai`.
- `root` -> deprecate; use `track/phase/task` hierarchy instead.

## Build naming

- Canonical verb: `make`.
- Compatibility alias: `build`.

## Keyword help

Bare keywords (e.g., `maestro repo`) show full subtree help and exit 0.
