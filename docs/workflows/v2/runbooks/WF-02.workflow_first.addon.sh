#!/usr/bin/env bash
set -euo pipefail

# Helper function to support dry-run
run() { echo "+ $*"; }

# WF-02 addon: workflow-first bootstrap for greenfield projects
# This runbook adds a workflow graph before the manual plan steps.

# Step 1: Initialize the maestro environment for a new project
run maestro init
# EXPECT: Initializes the maestro environment in the current directory
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 2: Create a workflow graph for the product spec
run maestro workflow init product_spec
# EXPECT: Creates a workflow graph at ./docs/maestro/workflows/product_spec.json
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_TRUTH_IS_DOCS_MAESTRO, REPO_TRUTH_FORMAT_IS_JSON
# INTERNAL: UNKNOWN

# Step 3: Add manager intent and user intent nodes
run maestro workflow node add --graph product_spec --layer manager_intent --id MI-001 --title "Product intent"
# EXPECT: Adds a manager_intent node
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_TRUTH_IS_DOCS_MAESTRO, REPO_TRUTH_FORMAT_IS_JSON
# INTERNAL: UNKNOWN

run maestro workflow node add --graph product_spec --layer user_intent --id UI-001 --title "User needs"
# EXPECT: Adds a user_intent node
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_TRUTH_IS_DOCS_MAESTRO, REPO_TRUTH_FORMAT_IS_JSON
# INTERNAL: UNKNOWN

# Step 4: Add interface candidates (CLI/TUI/GUI/game loops)
run maestro workflow node add --graph product_spec --layer interface --id IF-CLI --title "CLI interface"
run maestro workflow node add --graph product_spec --layer interface --id IF-TUI --title "TUI interface"
run maestro workflow node add --graph product_spec --layer interface --id IF-GUI --title "GUI interface"
run maestro workflow node add --graph product_spec --layer interface --id IF-LOOP --title "Game loop interface"
# EXPECT: Adds interface candidates for later pruning
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_TRUTH_IS_DOCS_MAESTRO, REPO_TRUTH_FORMAT_IS_JSON
# INTERNAL: UNKNOWN

# Step 5: Add high-level edges
run maestro workflow edge add --graph product_spec --from MI-001 --to UI-001
run maestro workflow edge add --graph product_spec --from UI-001 --to IF-CLI
run maestro workflow edge add --graph product_spec --from UI-001 --to IF-TUI
run maestro workflow edge add --graph product_spec --from UI-001 --to IF-GUI
run maestro workflow edge add --graph product_spec --from UI-001 --to IF-LOOP
# EXPECT: Links intents to interface candidates
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_TRUTH_IS_DOCS_MAESTRO, REPO_TRUTH_FORMAT_IS_JSON
# INTERNAL: UNKNOWN

# Step 6: Validate and export
run maestro workflow validate --graph product_spec
run maestro workflow export --graph product_spec --format puml
run maestro workflow render --graph product_spec --format svg
# EXPECT: Produces PlantUML and SVG artifacts
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_TRUTH_IS_DOCS_MAESTRO, REPO_TRUTH_FORMAT_IS_JSON
# INTERNAL: UNKNOWN

# Step 7: Proceed with manual plan (track/phase/task) or repo steps
# TODO: Continue with WF-02.runbook steps (track/phase/task) after workflow alignment
