#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../../../.." && pwd)"

run(){ echo "+ $*"; "$@"; }

if [[ -n "${MAESTRO_BIN:-}" ]]; then
  read -r -a MAESTRO_CMD <<<"$MAESTRO_BIN"
elif [[ -x "$REPO_ROOT/maestro.py" ]]; then
  MAESTRO_CMD=("$REPO_ROOT/maestro.py")
else
  MAESTRO_CMD=(python -m maestro)
fi

# Create pipeline
run "${MAESTRO_CMD[@]}" convert add demo-pipe
# EXPECT: pipeline metadata + plan skeleton created
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: none

# Generate/refresh plan
run "${MAESTRO_CMD[@]}" convert plan demo-pipe
# EXPECT: plan saved, status planned
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: none

# Show plan
# Compatibility: `convert plan demo-pipe show` also works (pipeline-first action).
run "${MAESTRO_CMD[@]}" convert plan show demo-pipe
# EXPECT: plan details printed
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: none

# Expected failure: run without approval should block
run "${MAESTRO_CMD[@]}" convert run demo-pipe || echo "Expected gate block (CONVERT_PLAN_NOT_APPROVED)"
# EXPECT: gate message
# STORES: none
# GATES: CONVERT_PLAN_NOT_APPROVED

# Approve plan
# Compatibility: `convert plan demo-pipe approve --reason "..."`
run "${MAESTRO_CMD[@]}" convert plan approve demo-pipe --reason "ready to run"
# EXPECT: decision recorded, status approved
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: none

# Run conversion
run "${MAESTRO_CMD[@]}" convert run demo-pipe
# EXPECT: run recorded under target repo docs/maestro/convert
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: none

# Verify ledger entry
run rg "Convert plan approval" docs/workflows/v3/IMPLEMENTATION_LEDGER.md
# EXPECT: ledger reflects convert approval behavior
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: none
