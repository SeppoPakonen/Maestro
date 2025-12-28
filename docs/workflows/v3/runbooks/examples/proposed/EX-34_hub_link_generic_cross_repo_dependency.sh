#!/usr/bin/env bash
set -euo pipefail

run(){ echo "+ $*"; "$@"; }

# Preconditions:
# - Repo truth is JSON under ./docs/maestro/**
# - Multiple repositories on local machine (CMake, U++, Maven, etc.)
# - Build system integration active

# Assume we have two repos:
# - /tmp/test-repos/CoreLib (external library)
# - /tmp/test-repos/MyApp (our application)

echo "=== Step 1: Scan CoreLib repository ==="
# (Assume we're in CoreLib directory)
# cd /tmp/test-repos/CoreLib
run maestro repo resolve
# EXPECT: repo model + hub index updated
# STORES: REPO_TRUTH_DOCS_MAESTRO, HOME_HUB_INDEX
# GATES: REPO_TRUTH_FORMAT_IS_JSON, HUB_DETERMINISM

echo ""
echo "=== Step 2: List scanned repositories ==="
run maestro repo hub list
# EXPECT: shows CoreLib repo in hub
# STORES: HOME_HUB_INDEX
# GATES: HOME_HUB_INDEX

echo ""
echo "=== Step 3: Scan MyApp repository ==="
# (Assume we're now in MyApp directory)
# cd /tmp/test-repos/MyApp
run maestro repo resolve
# EXPECT: repo model + hub index updated
# STORES: REPO_TRUTH_DOCS_MAESTRO, HOME_HUB_INDEX
# GATES: HUB_DETERMINISM

echo ""
echo "=== Step 4: Find CoreLib package across all repos ==="
run maestro repo hub find package CoreLib
# EXPECT: returns single match or ambiguous
# STORES: HOME_HUB_INDEX
# GATES: HUB_AMBIGUITY_GATE

echo ""
echo "=== Step 5: Link MyApp to CoreLib ==="
# If single match, use the returned pkg_id
# If ambiguous, user must select with --to <PKG_ID>
run maestro repo hub link package MyApp --to sha256:def456...
# EXPECT: link created in docs/maestro/repo/hub_links.json
# STORES: REPO_HUB_LINKS
# GATES: REPO_TRUTH_FORMAT_IS_JSON

echo ""
echo "=== Step 6: Show current hub links ==="
run maestro repo hub link show
# EXPECT: shows MyApp → CoreLib link
# STORES: REPO_HUB_LINKS
# GATES: none

echo ""
echo "=== Step 7: Build MyApp with external link ==="
run maestro make build MyApp
# EXPECT: CoreLib package root added to include paths
# STORES: REPO_TRUTH_DOCS_MAESTRO, REPO_HUB_LINKS
# GATES: REPOCONF_GATE

echo ""
echo "=== Additional Operations (Optional) ==="

echo "Show detailed hub info for a repo:"
run maestro repo hub show sha256:abc123...
# EXPECT: detailed repo information with package list
# STORES: HOME_HUB_INDEX

echo ""
echo "Remove a hub link:"
run maestro repo hub link remove sha256:link123...
# EXPECT: link removed from hub_links.json
# STORES: REPO_HUB_LINKS

echo ""
echo "Rescan to update hub index:"
run maestro repo resolve --no-write
# EXPECT: hub index updated without writing repo artifacts
# STORES: HOME_HUB_INDEX
# GATES: HUB_DETERMINISM

# /done would return JSON OPS in discuss mode
