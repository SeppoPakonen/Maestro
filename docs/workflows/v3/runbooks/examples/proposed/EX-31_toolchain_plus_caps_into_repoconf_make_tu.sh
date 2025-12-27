#!/usr/bin/env bash
set -euo pipefail

run(){ echo "+ $*"; }
MAESTRO_BIN="${MAESTRO_BIN:-maestro}"

# Preconditions:
# - Repo truth is JSON under ./docs/maestro/**
# - Toolchain profiles exist in hub
# - Optional: repo already resolved

run "$MAESTRO_BIN" init
# EXPECT: repo truth created
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_TRUTH_FORMAT_IS_JSON

# Select project toolchain
# NOT IMPLEMENTED (CLI_GAPS: GAP-0036)
run "$MAESTRO_BIN" select toolchain set <profile> --scope project
# EXPECT: NOT IMPLEMENTED (CLI_GAPS: GAP-0036)
# STORES: REPO_TRUTH_DOCS_MAESTRO HOME_HUB_REPO
# GATES: GATE_TOOLCHAIN_SELECTED

# Detect caps under current toolchain
# NOT IMPLEMENTED (CLI_GAPS: GAP-0037)
run "$MAESTRO_BIN" platform caps detect
# EXPECT: NOT IMPLEMENTED (CLI_GAPS: GAP-0037)
# STORES: HOME_HUB_REPO
# GATES: GATE_CAPS_DETECTED

# Prefer optional Vulkan
# NOT IMPLEMENTED (CLI_GAPS: GAP-0038)
run "$MAESTRO_BIN" platform caps prefer vulkan --scope project
# EXPECT: NOT IMPLEMENTED (CLI_GAPS: GAP-0038)
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_TRUTH_FORMAT_IS_JSON

# Resolve repo context
# Resolve repo context
run "$MAESTRO_BIN" repo refresh all
# EXPECT: repo resolved to targets
# STORES: REPO_TRUTH_DOCS_MAESTRO HOME_HUB_REPO
# GATES: REPO_TRUTH_FORMAT_IS_JSON

# Configure target
run "$MAESTRO_BIN" repo conf select-default target <t>
# EXPECT: repoconf present
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: GATE_REPOCONF_PRESENT

# Build with prefer policy
run "$MAESTRO_BIN" make
# EXPECT: build succeeds; Vulkan enabled if present
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: GATE_BUILD_OK

# TU build
run "$MAESTRO_BIN" tu build
# EXPECT: TU build succeeds
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: GATE_TU_READY

# Strict mode: require Vulkan
# NOT IMPLEMENTED (CLI_GAPS: GAP-0039)
run "$MAESTRO_BIN" platform caps require vulkan --scope project
# EXPECT: NOT IMPLEMENTED (CLI_GAPS: GAP-0039)
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_TRUTH_FORMAT_IS_JSON

# Build must enforce required caps
run "$MAESTRO_BIN" make
# EXPECT: NOT IMPLEMENTED (caps gate + issue creation) (CLI_GAPS: GAP-0040)
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: GATE_REQUIRE_CAPS_SATISFIED

# Optional: switch toolchain to satisfy caps
# NOT IMPLEMENTED (CLI_GAPS: GAP-0036)
run "$MAESTRO_BIN" select toolchain set <profile-with-vulkan> --scope project
# EXPECT: NOT IMPLEMENTED (CLI_GAPS: GAP-0036)
# STORES: REPO_TRUTH_DOCS_MAESTRO HOME_HUB_REPO
# GATES: GATE_TOOLCHAIN_SELECTED

# /done would return JSON OPS in discuss mode
