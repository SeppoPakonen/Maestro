#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }

# EX-29: Select Toolchain Profiles (Toolchain-Local Libraries)

echo "=== Step 1: Select baseline toolchain (project scope) ==="
run maestro select toolchain set system --scope project
# EXPECT: Toolchain selection recorded in repo truth
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_TRUTH_FORMAT_IS_JSON

echo ""
echo "=== Step 2: Show selected toolchain ==="
run maestro select toolchain show --scope project
# EXPECT: Selected profile shown
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: TOOLCHAIN_PROFILE_EXISTS

echo ""
echo "=== Step 3: Export environment snippet ==="
run TODO_CMD: maestro select toolchain export --format env --out ./docs/maestro/toolchain.env
# EXPECT: Exported env with include/lib paths
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: TOOLCHAIN_PROFILE_EXISTS

echo ""
echo "=== Step 4: Build with baseline toolchain ==="
run TODO_CMD: maestro make
# EXPECT: Build succeeds with system toolchain
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE

echo ""
echo "=== Step 5: Switch to SDK toolchain ==="
run maestro select toolchain set android_ndk_r25 --scope project
# EXPECT: Toolchain selection updated
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: TOOLCHAIN_PROFILE_EXISTS

echo ""
echo "=== Step 6: Export SDK environment snippet ==="
run TODO_CMD: maestro select toolchain export --format env
# EXPECT: Export includes SDK sysroot paths
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: TOOLCHAIN_PROFILE_EXISTS

echo ""
echo "=== Step 7: Build with SDK toolchain ==="
run TODO_CMD: maestro make
# EXPECT: Build uses toolchain-local libs (SDK/sysroot)
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE

echo ""
echo "=== Outcome: Missing profile ==="
run TODO_CMD: maestro select toolchain detect
# EXPECT: List detected profiles or suggest hub install
# STORES_READ: HOME_HUB_REPO
# GATES: TOOLCHAIN_PROFILE_DISCOVERY
