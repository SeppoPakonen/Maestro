#!/usr/bin/env bash
set -euo pipefail

#══════════════════════════════════════════════════════════════════════════════
# Finalize Command IR Extraction
#══════════════════════════════════════════════════════════════════════════════
#
# This script performs post-extraction cleanup and validation:
#   1. Strip markdown fences from command YAML files
#   2. Validate all YAML files
#   3. Create ledger candidates report
#   4. Run PlantUML validation (if applicable)
#   5. Show summary
#
#══════════════════════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CMD_IR_DIR="${REPO_ROOT}/docs/workflows/v2/ir/cmd"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
RESET='\033[0m'

log() { echo -e "${GREEN}$*${RESET}"; }
info() { echo -e "${BLUE}$*${RESET}"; }
warn() { echo -e "${YELLOW}$*${RESET}"; }
error() { echo -e "${RED}ERROR: $*${RESET}" >&2; }

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${BLUE}║   Maestro Command IR Extraction Finalization                      ║${RESET}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════╝${RESET}"
echo

# ═════════════════════════════════════════════════════════════════════════════
# Step 1: Strip markdown fences from command YAML files
# ═════════════════════════════════════════════════════════════════════════════

info "Step 1: Stripping markdown fences from command YAML files..."
echo

stripped_count=0
for yaml_file in "${CMD_IR_DIR}"/CMD-*.yaml; do
    if [ ! -f "$yaml_file" ]; then
        continue
    fi

    # Check if first line is markdown fence
    if head -n 1 "$yaml_file" | grep -q '^```yaml$'; then
        sed -i '1{/^```yaml$/d;}' "$yaml_file"
        sed -i '${/^```$/d;}' "$yaml_file"
        log "  ✓ Cleaned $(basename "$yaml_file")"
        stripped_count=$((stripped_count + 1))
    fi
done

if [ "$stripped_count" -eq 0 ]; then
    log "  No markdown fences found (all files clean)"
else
    log "  Stripped fences from ${stripped_count} files"
fi
echo

# ═════════════════════════════════════════════════════════════════════════════
# Step 2: Validate all YAML files
# ═════════════════════════════════════════════════════════════════════════════

info "Step 2: Validating all YAML files..."
echo

if ! python3 "${SCRIPT_DIR}/validate_all_yaml.py"; then
    error "YAML validation failed!"
    exit 1
fi
echo

# ═════════════════════════════════════════════════════════════════════════════
# Step 3: Create ledger candidates report
# ═════════════════════════════════════════════════════════════════════════════

info "Step 3: Creating ledger candidates report..."
echo

if ! python3 "${SCRIPT_DIR}/create_ledger_candidates.py"; then
    warn "Ledger candidates report creation failed (non-fatal)"
else
    log "  ✓ Ledger candidates report created"
fi
echo

# ═════════════════════════════════════════════════════════════════════════════
# Step 4: PlantUML validation (check if any .puml files exist)
# ═════════════════════════════════════════════════════════════════════════════

info "Step 4: Checking for PlantUML files..."
echo

puml_count=$(find "${REPO_ROOT}/docs/workflows/v2" -name "*.puml" 2>/dev/null | wc -l)

if [ "$puml_count" -gt 0 ]; then
    warn "Found ${puml_count} PlantUML files - validation not implemented yet"
    info "  Run: /usr/bin/plantuml -tsvg <files>"
else
    log "  No PlantUML files found in v2 directory"
fi
echo

# ═════════════════════════════════════════════════════════════════════════════
# Step 5: Summary
# ═════════════════════════════════════════════════════════════════════════════

info "═══════════════════════════════════════════════════════════════════"
log "✓ Finalization complete!"
info "═══════════════════════════════════════════════════════════════════"
echo

# Count files
wf_count=$(find "${REPO_ROOT}/docs/workflows/v2/ir/wf" -name "WF-*.intent.yaml" 2>/dev/null | wc -l)
cmd_cli_count=$(find "${CMD_IR_DIR}" -name "CMD-*.cli.yaml" 2>/dev/null | wc -l)
cmd_code_count=$(find "${CMD_IR_DIR}" -name "CMD-*.code.yaml" 2>/dev/null | wc -l)
map_count=$(find "${REPO_ROOT}/docs/workflows/v2/ir/maps" -name "*.yaml" 2>/dev/null | wc -l)

echo "Summary:"
echo "  WF intent files:     ${wf_count}"
echo "  CMD CLI files:       ${cmd_cli_count}"
echo "  CMD code files:      ${cmd_code_count}"
echo "  Mapping files:       ${map_count}"
echo
echo "Next steps:"
echo "  1. Review ledger candidates report: docs/workflows/v2/reports/ledger_candidates.md"
echo "  2. Commit changes:"
echo "     cd ${REPO_ROOT}"
echo "     git add docs/workflows/v2/ir"
echo "     git add tools/workflow_v2"
echo "     git commit -m 'docs(workflows): extract CLI+code command IR and link to WF intents'"
echo

info "═══════════════════════════════════════════════════════════════════"
