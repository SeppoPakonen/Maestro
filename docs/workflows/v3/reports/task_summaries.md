# Task Summaries (Curated)

## unknown — Reserve EX-29..EX-31 + Example Index

- What changed:
  - Reserved EX-29..EX-31 for toolchain, platform caps, and integration chain.
  - Renumbered candidate examples to avoid collisions.
  - Added a canonical example index for v3.
- Files touched:
  - docs/workflows/v3/reports/new_example_candidates.md
  - docs/workflows/v3/reports/example_index.md
- Validation:
  - /usr/bin/plantuml -tsvg docs/workflows/v2/generated/puml/*.puml
- Follow-ups:
  - Keep example_index.md updated when new EX files are added.

## unknown — Integration Contract + EX-31

- What changed:
  - Defined integration contract for toolchain, platform caps, and repoconf.
  - Added EX-31 runbook and script for the full chain.
  - Appended ledger items for required plumbing.
- Files touched:
  - docs/workflows/v3/cli/INTEGRATION_SELECT_PLATFORM_REPOCONF.md
  - docs/workflows/v3/runbooks/examples/proposed/EX-31_toolchain_plus_caps_into_repoconf_make_tu.md
  - docs/workflows/v3/runbooks/examples/proposed/EX-31_toolchain_plus_caps_into_repoconf_make_tu.sh
  - docs/workflows/v3/IMPLEMENTATION_LEDGER.md
- Validation:
  - /usr/bin/plantuml -tsvg docs/workflows/v2/generated/puml/*.puml
- Follow-ups:
  - Ensure EX-31 gate names match the canonical registry.
