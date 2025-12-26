#!/usr/bin/env bash
set -euo pipefail

run(){ echo "+ $*"; }

# Preconditions:
# - Repo truth is JSON under ./docs/maestro/**
# - Toolchain profiles exist in hub
# - Optional: repo already resolved

run maestro init
# EXPECT: repo truth created
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_TRUTH_FORMAT_IS_JSON

# Select project toolchain
# TODO_CMD: maestro select toolchain set <profile> --scope project
run maestro select toolchain set <profile> --scope project
# EXPECT: toolchain reference stored in repo
# STORES: REPO_TRUTH_DOCS_MAESTRO HOME_HUB_REPO
# GATES: GATE_TOOLCHAIN_SELECTED

# Detect caps under current toolchain
# TODO_CMD: maestro platform caps detect
run maestro platform caps detect
# EXPECT: detection cached in hub
# STORES: HOME_HUB_REPO
# GATES: GATE_CAPS_DETECTED

# Prefer optional Vulkan
# TODO_CMD: maestro platform caps prefer vulkan --scope project
run maestro platform caps prefer vulkan --scope project
# EXPECT: policy stored; missing is OK
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_TRUTH_FORMAT_IS_JSON

# Resolve repo context
# TODO_CMD: maestro repo resolve --level deep
run maestro repo resolve --level deep
# EXPECT: repo resolved to targets
# STORES: REPO_TRUTH_DOCS_MAESTRO HOME_HUB_REPO
# GATES: REPO_TRUTH_FORMAT_IS_JSON

# Configure target
# TODO_CMD: maestro repo conf select-default target <t>
run maestro repo conf select-default target <t>
# EXPECT: repoconf present
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: GATE_REPOCONF_PRESENT

# Build with prefer policy
# TODO_CMD: maestro make
run maestro make
# EXPECT: build succeeds; Vulkan enabled if present
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: GATE_BUILD_OK

# TU build
# TODO_CMD: maestro tu build
run maestro tu build
# EXPECT: TU build succeeds
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: GATE_TU_READY

# Strict mode: require Vulkan
# TODO_CMD: maestro platform caps require vulkan --scope project
run maestro platform caps require vulkan --scope project
# EXPECT: policy stored; missing blocks
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_TRUTH_FORMAT_IS_JSON

# Build must enforce required caps
run maestro make
# EXPECT: missing Vulkan gates + issue/task
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: GATE_REQUIRE_CAPS_SATISFIED

# Optional: switch toolchain to satisfy caps
# TODO_CMD: maestro select toolchain set <profile-with-vulkan> --scope project
run maestro select toolchain set <profile-with-vulkan> --scope project
# EXPECT: toolchain switch updates environment
# STORES: REPO_TRUTH_DOCS_MAESTRO HOME_HUB_REPO
# GATES: GATE_TOOLCHAIN_SELECTED

# /done would return JSON OPS in discuss mode
