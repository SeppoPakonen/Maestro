#!/usr/bin/env bash
set -euo pipefail

# Helper function to support dry-run
run() { echo "+ $*"; }

# WF-08: Convert cross-repo pipeline
# This runbook demonstrates creating and running cross-repo conversion pipelines.

# Step 1: Initialize a new conversion project
run maestro convert new --name "cpp-to-rust-conversion" --description "Convert C++ codebase to Rust"
# EXPECT: Creates a new conversion project with specified name and description
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN
# TODO: Confirm the exact command for creating new conversion projects

# Step 2: Generate a conversion plan
run maestro convert plan --from "C++" --to "Rust" --source "src/cpp" --target "src/rust"
# EXPECT: Creates a plan for converting code from C++ to Rust
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN
# TODO: Confirm the exact command for creating conversion plans

# Step 3: Review the conversion plan
run maestro convert plan --show --name "cpp-to-rust-conversion"
# EXPECT: Shows the details of the conversion plan
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN
# TODO: Confirm the exact command for showing conversion plans

# Step 4: Run the conversion pipeline
run maestro convert run --pipeline "cpp-to-rust-conversion"
# EXPECT: Executes the conversion pipeline
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: READONLY_GUARD
# INTERNAL: UNKNOWN

# Step 5: Adopt the second repository if needed
run maestro init --repo "path/to/target/repo"
# EXPECT: Initializes maestro in the target repository for adoption
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN
# TODO: Confirm how to specify a second repository for cross-repo operations

# Step 6: Export conversion results to another repo
run maestro convert export --pipeline "cpp-to-rust-conversion" --destination "path/to/target/repo"
# EXPECT: Exports conversion results to another repository
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: READONLY_GUARD
# INTERNAL: UNKNOWN
# TODO: Confirm the exact command for exporting conversion results