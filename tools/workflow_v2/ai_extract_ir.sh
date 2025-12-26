#!/usr/bin/env bash
# AI-driven YAML IR extraction for Maestro workflows
# Uses qwen to convert v1 documentation to v2 YAML IR format

set -euo pipefail

# Directories
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
V1_DIR="${REPO_ROOT}/docs/workflows/v1"
V2_IR_DIR="${REPO_ROOT}/docs/workflows/v2/ir/wf"
SCHEMA_DIR="${REPO_ROOT}/docs/workflows/v2/ir/schema"
PROMPT_TEMPLATE="${SCHEMA_DIR}/ai_prompt_template.md"
WORKFLOW_IR_SCHEMA="${SCHEMA_DIR}/workflow_ir.md"

# Options
DRY_RUN=false
VERBOSE=false
WORKFLOWS=()

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Usage
usage() {
    cat <<EOF
Usage: $0 [OPTIONS] [WF-XX...]

AI-driven extraction of YAML IR from v1 Maestro workflow documentation.

OPTIONS:
    -d, --dry-run       Print commands without executing
    -v, --verbose       Verbose output
    -h, --help          Show this help message

ARGUMENTS:
    WF-XX               Workflow IDs to extract (e.g., WF-09 WF-10)
                        If not specified, defaults to WF-09 through WF-16

EXAMPLES:
    $0                  # Extract WF-09 through WF-16
    $0 WF-09 WF-10      # Extract only WF-09 and WF-10
    $0 -d WF-09         # Dry run for WF-09
    $0 -v               # Verbose mode, all default workflows

REQUIREMENTS:
    - qwen command must be available in PATH
    - v1 documentation must exist in docs/workflows/v1/
    - Prompt template must exist at: ${PROMPT_TEMPLATE}
EOF
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        WF-*)
            WORKFLOWS+=("$1")
            shift
            ;;
        *)
            echo -e "${RED}Error: Unknown argument: $1${NC}" >&2
            usage
            ;;
    esac
done

# Default workflows if none specified
if [ ${#WORKFLOWS[@]} -eq 0 ]; then
    WORKFLOWS=(WF-09 WF-10 WF-11 WF-12 WF-13 WF-14 WF-15 WF-16)
fi

# Check prerequisites
check_prerequisites() {
    local missing=false

    if ! command -v qwen &> /dev/null; then
        echo -e "${RED}Error: qwen command not found in PATH${NC}" >&2
        missing=true
    fi

    if [ ! -f "${PROMPT_TEMPLATE}" ]; then
        echo -e "${RED}Error: Prompt template not found: ${PROMPT_TEMPLATE}${NC}" >&2
        missing=true
    fi

    if [ ! -f "${WORKFLOW_IR_SCHEMA}" ]; then
        echo -e "${RED}Error: Workflow IR schema not found: ${WORKFLOW_IR_SCHEMA}${NC}" >&2
        missing=true
    fi

    if [ ! -d "${V1_DIR}" ]; then
        echo -e "${RED}Error: v1 directory not found: ${V1_DIR}${NC}" >&2
        missing=true
    fi

    if [ "$missing" = true ]; then
        exit 1
    fi
}

# Convert WF-XX to scenario number (e.g., WF-09 -> 09)
wf_to_scenario_num() {
    local wf_id="$1"
    echo "${wf_id#WF-}"
}

# Find v1 files for a workflow
find_v1_files() {
    local wf_id="$1"
    local scenario_num
    scenario_num=$(wf_to_scenario_num "$wf_id")

    # Find scenario files (intent layer)
    local scenario_md
    local scenario_puml
    scenario_md=$(find "${V1_DIR}" -maxdepth 1 -name "scenario_${scenario_num}_*.md" | head -1)
    scenario_puml=$(find "${V1_DIR}" -maxdepth 1 -name "scenario_${scenario_num}_*.puml" | head -1)

    # Find internal/deep files (observed/code layer)
    local deep_files
    deep_files=$(find "${V1_DIR}/internal/deep" -name "*deep.puml" 2>/dev/null | tr '\n' ' ')

    echo "${scenario_md}|${scenario_puml}|${deep_files}"
}

# Extract layer from v1 files using AI
extract_layer() {
    local wf_id="$1"
    local layer="$2"  # intent, cli, code, observed
    local input_files="$3"
    local output_file="$4"

    local prompt
    prompt=$(cat <<EOF
You are extracting Maestro workflow YAML IR from v1 documentation.

**Task:** Extract the ${layer} layer for workflow ${wf_id}.

**Instructions:** Read the prompt template and IR schema below, then extract YAML IR from the provided v1 files.

**CRITICAL:** Output YAML ONLY. No markdown, no explanations, just YAML starting with 'wf_id:'.

---
PROMPT TEMPLATE:
$(cat "${PROMPT_TEMPLATE}")

---
IR SCHEMA:
$(cat "${WORKFLOW_IR_SCHEMA}")

---
V1 INPUT FILES:
${input_files}

---
OUTPUT REQUIREMENTS:
- wf_id: ${wf_id}
- layer: ${layer}
- storage_backend: Detect from v1 content (json/markdown/mixed/unknown)
- status: Assess based on v1 completeness (correct/incorrect/partial/ignore)
- confidence: Assess based on v1 quality (low/medium/high)
- ledger_hints: Generate if contradictions detected (storage backend, invariants, etc.)

OUTPUT YAML NOW:
EOF
)

    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}Prompt for ${wf_id} ${layer}:${NC}"
        echo "$prompt"
        echo ""
    fi

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY-RUN]${NC} qwen -y \"<prompt>\" > ${output_file}"
    else
        echo -e "${GREEN}Extracting ${wf_id} ${layer} layer...${NC}"
        qwen -y "$prompt" > "${output_file}"

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Extracted: ${output_file}${NC}"
        else
            echo -e "${RED}✗ Failed to extract: ${output_file}${NC}" >&2
            return 1
        fi
    fi
}

# Process a single workflow
process_workflow() {
    local wf_id="$1"
    local scenario_num
    scenario_num=$(wf_to_scenario_num "$wf_id")

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Processing ${wf_id}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # Find v1 files
    local v1_files
    v1_files=$(find_v1_files "$wf_id")
    IFS='|' read -r scenario_md scenario_puml deep_files <<< "$v1_files"

    if [ -z "$scenario_md" ]; then
        echo -e "${YELLOW}⚠ No v1 scenario file found for ${wf_id}, skipping${NC}"
        return 0
    fi

    echo -e "  Found v1 files:"
    [ -n "$scenario_md" ] && echo -e "    - ${scenario_md}"
    [ -n "$scenario_puml" ] && echo -e "    - ${scenario_puml}"
    [ -n "$deep_files" ] && echo -e "    - internal/deep: ${deep_files}"

    # Prepare input content for AI
    local intent_input=""
    [ -n "$scenario_md" ] && intent_input+="FILE: ${scenario_md}\n\n$(cat "${scenario_md}")\n\n"
    [ -n "$scenario_puml" ] && intent_input+="FILE: ${scenario_puml}\n\n$(cat "${scenario_puml}")\n\n"

    # Extract intent layer
    local intent_output="${V2_IR_DIR}/${wf_id}.intent.yaml"
    mkdir -p "${V2_IR_DIR}"
    extract_layer "$wf_id" "intent" "$intent_input" "$intent_output"

    # Extract observed layer from internal/deep if exists
    if [ -n "$deep_files" ]; then
        local observed_input=""
        for deep_file in $deep_files; do
            if [ -f "$deep_file" ]; then
                observed_input+="FILE: ${deep_file}\n\n$(cat "${deep_file}")\n\n"
            fi
        done

        if [ -n "$observed_input" ]; then
            local observed_output="${V2_IR_DIR}/${wf_id}.observed.yaml"
            extract_layer "$wf_id" "observed" "$observed_input" "$observed_output"
        fi
    fi

    echo -e "${GREEN}✓ Completed ${wf_id}${NC}"
}

# Main execution
main() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   Maestro Workflow AI-Driven YAML IR Extraction Pipeline          ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}Running in DRY-RUN mode (no files will be written)${NC}"
        echo ""
    fi

    check_prerequisites

    echo -e "Workflows to extract: ${WORKFLOWS[*]}"
    echo -e "Output directory: ${V2_IR_DIR}"
    echo ""

    for wf_id in "${WORKFLOWS[@]}"; do
        process_workflow "$wf_id"
    done

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✓ Extraction complete!${NC}"
    echo ""
    echo -e "Generated IR files:"
    ls -1 "${V2_IR_DIR}"/*.yaml 2>/dev/null || echo "  (none)"
    echo ""
}

main
