#!/usr/bin/env bash
set -euo pipefail

run(){ echo "+ $*"; }
MAESTRO_BIN="${MAESTRO_BIN:-maestro}"

# Create pipeline
run "$MAESTRO_BIN" convert add demo-pipe
# EXPECT: pipeline metadata + plan skeleton created
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: none

# Generate/refresh plan
run "$MAESTRO_BIN" convert plan demo-pipe
# EXPECT: plan saved, status planned
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: none

# Show plan
run "$MAESTRO_BIN" convert plan show demo-pipe
# EXPECT: plan details printed
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: none

# Expected failure: run without approval should block
run "$MAESTRO_BIN" convert run demo-pipe || echo "Expected gate block (CONVERT_PLAN_NOT_APPROVED)"
# EXPECT: gate message
# STORES: none
# GATES: CONVERT_PLAN_NOT_APPROVED

# Approve plan
run "$MAESTRO_BIN" convert plan approve demo-pipe --reason "ready to run"
# EXPECT: decision recorded, status approved
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: none

# Run conversion
run "$MAESTRO_BIN" convert run demo-pipe
# EXPECT: run recorded under target repo docs/maestro/convert
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: none

# Verify ledger entry
run rg "Convert plan approval" docs/workflows/v3/IMPLEMENTATION_LEDGER.md
# EXPECT: ledger reflects convert approval behavior
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: none
