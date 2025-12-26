#!/usr/bin/env bash
set -euo pipefail

run(){ echo "+ $*"; }

# Preconditions:
# - Repo truth is JSON under ./docs/maestro/**
# - Repo initialized
# - Optional toolchain selection may be active

run maestro init
# EXPECT: repo truth created
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_TRUTH_FORMAT_IS_JSON

# TODO_CMD: maestro platform caps detect
run maestro platform caps detect
# EXPECT: detected caps cached in hub
# STORES: HOME_HUB_REPO
# GATES: CAP_DETECT

# Prefer Vulkan if present (opportunistic)
# TODO_CMD: maestro platform caps prefer vulkan --scope project
run maestro platform caps prefer vulkan --scope project
# EXPECT: policy stored; missing is OK
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_TRUTH_FORMAT_IS_JSON

# Build adapts to caps
# TODO_CMD: maestro make --cap-report
run maestro make
# EXPECT: build uses Vulkan only if present
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE

# Strict mode: require Vulkan
# TODO_CMD: maestro platform caps require vulkan --scope project
run maestro platform caps require vulkan --scope project
# EXPECT: policy stored; missing will gate
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_TRUTH_FORMAT_IS_JSON

# Build must enforce require
run maestro make
# EXPECT: missing cap triggers gate + issue/task
# STORES: REPO_TRUTH_DOCS_MAESTRO
# GATES: CAP_REQUIRE

# /done would return JSON OPS in discuss mode
