# v3 CLI Tree (Normative)

This is the proposed v3 command tree. Verbs are short; keyword namespaces carry specificity.
Canonical shapes are defined in `docs/workflows/v3/cli/SIGNATURES.md`, and hard gates are listed in `docs/workflows/v3/cli/INVARIANTS.md`.

**Note:** This tree shows v3 canonical commands (`MAESTRO_ENABLE_LEGACY=0`, default mode). Legacy commands (session, understand, resume, rules, root) are hidden by default and require `MAESTRO_ENABLE_LEGACY=1` to enable. See [CLI Surface Contract](./CLI_SURFACE_CONTRACT.md) for details.

## Top-level

- `maestro init`
- `maestro runbook {list|show|add|edit|rm|step-add|step-edit|step-rm|step-renumber|export|render|archive|restore|discuss|resolve}`
- `maestro workflow {list|show|create|edit|delete|visualize|archive|restore}`
- `maestro repo {resolve|refresh|conf|show|hub|make|asm}`
- `maestro track {list|show|add|edit|rm|discuss}`
- `maestro phase {list|show|add|edit|rm|discuss}`
- `maestro task {list|show|add|edit|rm|discuss|link|set}`
- `maestro issues {list|show|state|rollback|react|analyze|decide|fix}`
- `maestro solutions {list|show|add|edit|remove}`
- `maestro work {any|track|phase|issue|task|discuss|analyze|fix|resume|subwork}`
- `maestro wsession {list|show|tree|breadcrumbs|breadcrumb|timeline|stats|close}`
- `maestro discuss` (router)
- `maestro ai {list|use|run|resume}`
- `maestro settings {list|show|set|reset}`
- `maestro ops {doctor|run|list|show}`
- `maestro tu {build|query|refactor}`
- `maestro convert {list|show|add|edit|rm|plan|run}`
- `maestro select {toolchain}`
- `maestro platform {caps}`

## Selected subtrees

- `maestro discuss resume <SESSION_ID>`
- `maestro discuss replay <PATH> --dry-run [--allow-cross-context]`
- `maestro discuss --wsession <WSESSION_ID>`
- `maestro repo resolve`
- `maestro repo refresh all`
- `maestro repo conf {show|select-default target}`
- `maestro repo asm {list|show}` (aliases: `assembly`)
- `maestro repo hub {find|list|link}`
- `maestro workflow node {add|edit|rm}`
- `maestro workflow edge {add|edit|rm}`
- `maestro runbook step {add|edit|rm|list}`
- `maestro task link {phase|issue|solution}`
- `maestro task set {status|dependency}`
- `maestro issues link {task|solution}`
- `maestro wsession breadcrumb {add|list}`
- `maestro work subwork {start|list|show|close|resume-parent}`
- `maestro select toolchain {list|show|set|unset|detect|export}`
- `maestro platform caps {detect|list|show|prefer|require|unprefer|unrequire|export}`
- `maestro convert plan {show|approve|reject}`

See also: `docs/workflows/v3/cli/INTEGRATION_SELECT_PLATFORM_REPOCONF.md` for toolchain/caps/repoconf/make/tu integration.

## Legacy/Deprecated Commands (Hidden by Default)

**Kill Switch:** `MAESTRO_ENABLE_LEGACY=1` enables these commands with deprecation warnings.

**Default behavior:** Legacy commands NOT in parser; `maestro session --help` fails with helpful error message.

**Deprecated commands and their replacements:**

- `maestro session` → `maestro wsession` (work sessions with breadcrumbs)
- `maestro understand` → `maestro repo resolve` + `maestro runbook export` (repository analysis)
- `maestro resume` → `maestro work resume` / `maestro discuss resume` (explicit context)
- `maestro rules` → `maestro repo conventions` / `maestro solutions` (policy rules)
- `maestro root` → `maestro track` / `maestro phase` / `maestro task` (hierarchical structure)

**See:**
- [CLI Surface Contract](./CLI_SURFACE_CONTRACT.md) - Migration playbook and contract
- [Deprecation Policy](./DEPRECATION.md) - Kill switch implementation details
- [CLI Signatures](./SIGNATURES.md) - MAESTRO_ENABLE_LEGACY environment variable

## Build naming

- Canonical verb: `make`.
- Compatibility alias: `build`.

## Keyword help

Bare keywords (e.g., `maestro repo`) show full subtree help and exit 0.
