#!/usr/bin/env bash
set -euo pipefail

#══════════════════════════════════════════════════════════════════════════════
# Maestro Command IR Extraction Pipeline (AI-driven)
#══════════════════════════════════════════════════════════════════════════════
#
# Extracts CLI and code layers from v1/internal command documentation
# into command-based YAML IR files (CMD-*.cli.yaml, CMD-*.code.yaml)
#
# Usage:
#   ./ai_extract_cmd_ir.sh [options] [COMMAND_NAME...]
#
# Options:
#   -d, --dry-run       Show what would be done without executing
#   -v, --verbose       Show detailed output
#   -h, --help          Show this help message
#
# Examples:
#   ./ai_extract_cmd_ir.sh                    # Extract all commands
#   ./ai_extract_cmd_ir.sh repo phase task    # Extract specific commands
#   ./ai_extract_cmd_ir.sh -d -v repo         # Dry-run with verbose output
#
#══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
V1_INTERNAL_DIR="${REPO_ROOT}/docs/workflows/v1/internal"
V1_DEEP_DIR="${REPO_ROOT}/docs/workflows/v1/internal/deep"
OUTPUT_DIR="${REPO_ROOT}/docs/workflows/v2/ir/cmd"
PROMPT_TEMPLATE="${REPO_ROOT}/docs/workflows/v2/ir/schema/ai_prompt_template.md"
WORKFLOW_IR_SCHEMA="${REPO_ROOT}/docs/workflows/v2/ir/schema/workflow_ir.md"

DRY_RUN=false
VERBOSE=false
COMMANDS_TO_EXTRACT=()

# ═══════════════════════════════════════════════════════════════════════════
# Colors
# ═══════════════════════════════════════════════════════════════════════════

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RESET='\033[0m'

# ═══════════════════════════════════════════════════════════════════════════
# Functions
# ═══════════════════════════════════════════════════════════════════════════

usage() {
    cat << EOF
Usage: $(basename "$0") [options] [COMMAND_NAME...]

Extract CLI and code layers from v1/internal command documentation.

Options:
  -d, --dry-run       Show what would be done without executing
  -v, --verbose       Show detailed output
  -h, --help          Show this help message

Examples:
  $(basename "$0")                    # Extract all commands
  $(basename "$0") repo phase task    # Extract specific commands
  $(basename "$0") -d -v repo         # Dry-run with verbose output
EOF
    exit 0
}

log() {
    echo -e "${GREEN}$*${RESET}"
}

info() {
    echo -e "${BLUE}$*${RESET}"
}

warn() {
    echo -e "${YELLOW}$*${RESET}"
}

error() {
    echo -e "${RED}ERROR: $*${RESET}" >&2
}

# Get list of all available commands
get_all_commands() {
    find "${V1_INTERNAL_DIR}" -maxdepth 1 -name "cmd_*.md" \
        | sed 's|.*/cmd_\(.*\)\.md|\1|' \
        | sort
}

# Extract CLI layer for a command
extract_cli_layer() {
    local cmd_name="$1"
    local cmd_md="${V1_INTERNAL_DIR}/cmd_${cmd_name}.md"
    local cmd_puml="${V1_INTERNAL_DIR}/cmd_${cmd_name}.puml"
    local output_file="${OUTPUT_DIR}/CMD-${cmd_name}.cli.yaml"

    if [[ ! -f "${cmd_md}" ]]; then
        warn "CLI source not found: ${cmd_md}"
        return 1
    fi

    local input_content=""
    input_content+="# ${cmd_name} CLI Documentation\n\n"
    input_content+="## Markdown Documentation\n\n"
    input_content+="$(cat "${cmd_md}")\n\n"

    if [[ -f "${cmd_puml}" ]]; then
        input_content+="## PlantUML Diagram\n\n"
        input_content+="$(cat "${cmd_puml}")\n\n"
    fi

    local prompt
    prompt=$(cat <<EOF
You are extracting Maestro command YAML IR from v1 CLI documentation.

**Task:** Extract the CLI layer for command: ${cmd_name}

**CRITICAL:** Output YAML ONLY. No markdown, no explanations, just YAML starting with 'id:'.

**Required fields:**
- id: "CMD-${cmd_name}"
- layer: "cli"
- title: "${cmd_name} command surface"
- status: "correct" | "partial" | "ignore"
- confidence: "low" | "medium" | "high"
- storage_backend: "json" | "markdown" | "mixed" | "unknown" (set to "unknown" unless explicitly mentioned)

**Extract:**
- commands: list full command names and subcommands seen in docs
- nodes: CLI subcommands as nodes with type "command" or "subcommand"
- edges: typical call flow if described
- exports: list outputs the command produces (e.g., "writes repo conf", "creates issue")
- evidence: include paths to source files

**Do not invent behavior not documented.** If uncertain, mark as "partial" and put unknowns in "notes" field.

---
PROMPT TEMPLATE:
$(cat "${PROMPT_TEMPLATE}")

---
V1 CLI DOCUMENTATION:
${input_content}
EOF
)

    if [[ "${DRY_RUN}" == "true" ]]; then
        info "[DRY-RUN] Would extract CLI layer for: ${cmd_name}"
        info "[DRY-RUN] Output: ${output_file}"
        return 0
    fi

    log "Extracting CLI layer for: ${cmd_name}"

    if [[ "${VERBOSE}" == "true" ]]; then
        echo "═══ Prompt Preview (first 500 chars) ═══"
        echo "${prompt}" | head -c 500
        echo -e "\n... (truncated)\n"
    fi

    # Use qwen to extract YAML IR
    qwen -y "${prompt}" > "${output_file}.tmp"

    # Strip markdown fences if present
    sed -i '1{/^```yaml$/d;}' "${output_file}.tmp"
    sed -i '${/^```$/d;}' "${output_file}.tmp"

    mv "${output_file}.tmp" "${output_file}"
    log "✓ Extracted CLI: ${output_file}"
}

# Extract code/deep layer for a command
extract_code_layer() {
    local cmd_name="$1"
    local cmd_deep_md="${V1_DEEP_DIR}/cmd_${cmd_name}_deep.md"
    local cmd_deep_puml="${V1_DEEP_DIR}/cmd_${cmd_name}_deep.puml"
    local output_file="${OUTPUT_DIR}/CMD-${cmd_name}.code.yaml"

    if [[ ! -f "${cmd_deep_md}" && ! -f "${cmd_deep_puml}" ]]; then
        warn "Deep source not found for: ${cmd_name}"
        return 1
    fi

    local input_content=""
    input_content+="# ${cmd_name} Deep Internal Flow\n\n"

    if [[ -f "${cmd_deep_md}" ]]; then
        input_content+="## Markdown Documentation\n\n"
        input_content+="$(cat "${cmd_deep_md}")\n\n"
    fi

    if [[ -f "${cmd_deep_puml}" ]]; then
        input_content+="## PlantUML Diagram\n\n"
        input_content+="$(cat "${cmd_deep_puml}")\n\n"
    fi

    local prompt
    prompt=$(cat <<EOF
You are extracting Maestro command YAML IR from v1 deep/code documentation.

**Task:** Extract the code/observed layer for command: ${cmd_name}

**CRITICAL:** Output YAML ONLY. No markdown, no explanations, just YAML starting with 'id:'.

**Required fields:**
- id: "CMD-${cmd_name}"
- layer: "code"
- title: "${cmd_name} deep internal flow (observed)"
- status: "correct" | "partial" | "ignore"
- confidence: "low" | "medium" | "high"
- storage_backend: **MUST reflect what deep docs show**
  - If mentions "DataMarkdown" or markdown persistence: set "markdown" or "mixed"
  - If shows JSON persistence: set "json"
  - Otherwise: "unknown"

**Extract:**
- calls: list functions/classes mentioned
- stores: list data stores touched (repo truth/home hub/IPC if inferable)
- nodes: internal function calls at coarse level (use types: function, class, module, datastore, actor)
- edges: call flow between functions
- evidence: include paths to source files

**IMPORTANT - Ledger Hints:**
Add ledger_hints entries for contradictions vs v2 spec:
- If text contains "DataMarkdown" or implies markdown persistence, add:
  ledger_hints: ["Observed DataMarkdown persistence in cmd_${cmd_name} deep flow; v2 repo truth uses JSON. Replace/remove DataMarkdown codepaths and update docs/tests."]
- If mentions .maestro directory usage, add hint about FORBID_REPO_DOT_MAESTRO invariant
- If shows markdown file persistence for repo truth, add hint about REPO_TRUTH_FORMAT_IS_JSON

---
PROMPT TEMPLATE:
$(cat "${PROMPT_TEMPLATE}")

---
V1 DEEP DOCUMENTATION:
${input_content}
EOF
)

    if [[ "${DRY_RUN}" == "true" ]]; then
        info "[DRY-RUN] Would extract code layer for: ${cmd_name}"
        info "[DRY-RUN] Output: ${output_file}"
        return 0
    fi

    log "Extracting code layer for: ${cmd_name}"

    if [[ "${VERBOSE}" == "true" ]]; then
        echo "═══ Prompt Preview (first 500 chars) ═══"
        echo "${prompt}" | head -c 500
        echo -e "\n... (truncated)\n"
    fi

    # Use qwen to extract YAML IR
    qwen -y "${prompt}" > "${output_file}.tmp"

    # Strip markdown fences if present
    sed -i '1{/^```yaml$/d;}' "${output_file}.tmp"
    sed -i '${/^```$/d;}' "${output_file}.tmp"

    mv "${output_file}.tmp" "${output_file}"
    log "✓ Extracted code: ${output_file}"
}

# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                usage
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            *)
                COMMANDS_TO_EXTRACT+=("$1")
                shift
                ;;
        esac
    done

    # If no commands specified, extract all
    if [[ ${#COMMANDS_TO_EXTRACT[@]} -eq 0 ]]; then
        mapfile -t COMMANDS_TO_EXTRACT < <(get_all_commands)
    fi

    # Header
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════╗${RESET}"
    echo -e "${BLUE}║   Maestro Command IR Extraction Pipeline (CLI + Code Layers)      ║${RESET}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════╝${RESET}"
    echo
    echo "Commands to extract: ${COMMANDS_TO_EXTRACT[*]}"
    echo "Output directory: ${OUTPUT_DIR}"
    echo
    if [[ "${DRY_RUN}" == "true" ]]; then
        warn "DRY-RUN MODE - No files will be written"
        echo
    fi

    # Create output directory
    if [[ "${DRY_RUN}" == "false" ]]; then
        mkdir -p "${OUTPUT_DIR}"
    fi

    # Extract each command
    local total=${#COMMANDS_TO_EXTRACT[@]}
    local current=0
    local failed=0

    for cmd_name in "${COMMANDS_TO_EXTRACT[@]}"; do
        current=$((current + 1))
        echo
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
        echo -e "${BLUE}Processing ${cmd_name} (${current}/${total})${RESET}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"

        # Extract CLI layer
        if ! extract_cli_layer "${cmd_name}"; then
            warn "Failed to extract CLI layer for: ${cmd_name}"
            failed=$((failed + 1))
        fi

        # Extract code layer
        if ! extract_code_layer "${cmd_name}"; then
            warn "Failed to extract code layer for: ${cmd_name}"
            failed=$((failed + 1))
        fi
    done

    # Summary
    echo
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "${GREEN}✓ Extraction complete${RESET}"
    echo "  Total commands: ${total}"
    echo "  Failed extractions: ${failed}"
    echo "  Output: ${OUTPUT_DIR}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
}

main "$@"
