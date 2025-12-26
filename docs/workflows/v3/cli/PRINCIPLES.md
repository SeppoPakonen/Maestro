# v3 CLI Principles (Normative)

Canonical command shapes are locked in `docs/workflows/v3/cli/SIGNATURES.md`.
Hard gates and lifecycle rules live in `docs/workflows/v3/cli/INVARIANTS.md`.

## Help rule

- Any bare keyword (e.g., `maestro repo`) prints full extended help for that subtree and exits 0.
- `--help` remains supported for argparse compatibility, but keyword-help is the canonical UX.
- Short help (if needed) is via `-h/--help`, not via bare keywords.

## Verb uniformity rule

Canonical verbs that should exist consistently across entities:

- `list`, `show`, `add`, `edit`, `rm`
- `discuss` (where applicable)
- `export`, `render` (only when artifacts exist)
- `run` (execution pipelines)
- `validate` (gates / schema checks)

Avoid long verbs. Grow with keyword namespaces instead of verb proliferation.

## Keyword-first growth rule

If a command is getting too specific, do not extend the verb. Keep verbs short and add keyword paths.

- Bad: `repo select-default-target`
- Good: `repo conf select-default target <target>`

## Naming consistency

- Canonical name in v3: `make` (build pipeline entrypoint).
- Keep `build` as a compatibility alias (soft deprecation) when needed.

## Selection command rule

- Selection commands are hard switches; they must support `show`, `list`, `set`, `unset` uniformly.

## Prefer vs require rule

- Prefer is the default: adapt to supply; require is explicit gating.
- Detection is data, not truth: store detection in the hub; store policy in repo truth.

## Repo truth and stores

- Repo truth is always under `./docs/maestro/**`.
- Commands that mutate repo truth should declare or imply `REPO_TRUTH_DOCS_MAESTRO` as a store.

## Discuss contract alignment

- `discuss` commands must enforce the JSON contract gate: invalid JSON blocks OPS.
- An op that has no CLI endpoint is considered a design smell and must be tracked in gaps.
