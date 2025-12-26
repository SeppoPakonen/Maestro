#!/usr/bin/env bash
set -euo pipefail

# Helper function to support dry-run
run() { echo "+ $*"; }

# WF-11: Manual repo model + manual RepoConf
# This runbook shows manual authoring with optional resolve augmentation.

# Step 1: Initialize repo truth
run maestro init
# EXPECT: Creates repo truth storage under ./docs/maestro/
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 2: Add a package to the repo model
run maestro repo package add "core" --path "src/core"
# EXPECT: Adds a package entry to the repo model
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN
# TODO: Confirm package add command

# Step 3: Set package language
run maestro repo package set-language "core" --language "cpp"
# EXPECT: Records package language in repo model
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 4: Set package build driver
run maestro repo package set-driver "core" --driver "cmake"
# EXPECT: Records package build driver in repo model
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 5: Add a target to RepoConf
run maestro repo conf target add "app" --type exe --package "core"
# EXPECT: Adds a build target to repo configuration
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN
# TODO: Confirm repo conf target add syntax

# Step 6: Set default target
run maestro repo conf set-default-target "app"
# EXPECT: Sets default target in repo configuration
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 7: Optional resolve to augment manual data
run maestro repo resolve --level lite
# EXPECT: Augments repo model and conf with detected info
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_RESOLVE_LITE
# INTERNAL: UNKNOWN

# Step 8: Build using manual RepoConf
run maestro build --target "app"
# EXPECT: Builds the target using manual RepoConf
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: READONLY_GUARD
# INTERNAL: UNKNOWN
# TODO: Confirm build target syntax

# Step 9: Generate TU/AST for package
run maestro tu --package "core"
# EXPECT: Generates TU/AST using manual RepoConf
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: READONLY_GUARD
# INTERNAL: UNKNOWN
# TODO: Confirm TU command syntax
