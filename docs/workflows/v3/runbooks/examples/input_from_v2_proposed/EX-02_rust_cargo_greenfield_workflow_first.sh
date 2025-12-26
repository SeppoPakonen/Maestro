#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }

# EX-02: Rust Cargo Greenfield — Workflow-First, Generate Skeleton, Build, Work Session

# Step 1: Initialize greenfield project
run maestro init --greenfield  # TODO: confirm if --greenfield flag exists
# EXPECT: Creates ./docs/maestro/** for new project
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 2: Create workflow graph
run maestro workflow init user-auth-service  # TODO_CMD: spec-level command
# EXPECT: Workflow template created
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 3-4: Add workflow nodes
run maestro workflow node add manager-intent "User can log in securely"  # TODO_CMD
run maestro workflow node add user-action "Submit login form"  # TODO_CMD
# EXPECT: Nodes added to workflow graph
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 5: Render workflow to PlantUML
run maestro workflow render --format puml  # TODO_CMD
# EXPECT: Generated user-auth-service.puml and .svg
# STORES_WRITE: (exports directory)
# GATES: (none)
# INTERNAL: UNKNOWN

# Step 6: Accept workflow, trigger skeleton generation
run maestro workflow accept user-auth-service  # TODO_CMD
# EXPECT: Cargo.toml and src/main.rs generated
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO + source files
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 7: Build the Rust skeleton
run maestro build
# EXPECT: Cargo build succeeds, binary in target/debug/my-rust-service
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: READONLY_GUARD
# INTERNAL: UNKNOWN

# Step 8: Create track
run maestro track add "Sprint 1" --start 2025-01-01
# EXPECT: Track created
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 9: Create phase
run maestro phase add track-001 "P1: Core Auth"
# EXPECT: Phase added to track
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 10: Create task
run maestro task add phase-001 "Implement login endpoint"
# EXPECT: Task created in phase
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 11: Start work session
run maestro work task task-001
# EXPECT: Work session started, AI has workflow context
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO, IPC_MAILBOX
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

echo ""
echo "EX-02 Outcome A: Workflow accepted, skeleton built, work session active"
echo "Workflow: ./docs/maestro/workflows/user-auth-service.json (status: accepted)"
echo "Binary: target/debug/my-rust-service"
