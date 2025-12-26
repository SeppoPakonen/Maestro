#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }

# EX-11: Model an Existing GUI App Menu as Runbooks — Runbook→Workflow (Interface Layer)

# Step 1: Initialize Maestro
run maestro init
# EXPECT: Creates ./docs/maestro/** structure
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 2: Create Runbook for File Menu
run maestro runbook add --title "GUI Menu: File" --scope ui --tag menu
# EXPECT: Runbook gui-menu-file.json created
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 3: Add File Menu Steps
run maestro runbook step-add gui-menu-file --actor manager --action "Define File menu structure" --expected "Menu items documented"
# EXPECT: Manager intent step added
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

run maestro runbook step-add gui-menu-file --actor user --action "Click File → New (or Ctrl+N)" --expected "New document created"
run maestro runbook step-add gui-menu-file --actor user --action "Click File → Open (or Ctrl+O)" --expected "File picker dialog opens"
run maestro runbook step-add gui-menu-file --actor user --action "Click File → Save (or Ctrl+S)" --expected "Document saved to disk"
run maestro runbook step-add gui-menu-file --actor user --action "Click File → Export → Export as PDF" --expected "PDF export dialog opens"
# EXPECT: User action steps added
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 4: Create Runbook for Edit Menu
run maestro runbook add --title "GUI Menu: Edit" --scope ui --tag menu
# EXPECT: Runbook gui-menu-edit.json created
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 5: Add Edit Menu Steps
run maestro runbook step-add gui-menu-edit --actor user --action "Click Edit → Undo (or Ctrl+Z)" --expected "Last action undone"
run maestro runbook step-add gui-menu-edit --actor user --action "Click Edit → Copy (or Ctrl+C)" --expected "Selection copied to clipboard"
# EXPECT: Edit menu steps added
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 6: Create Runbook for Help Menu
run maestro runbook add --title "GUI Menu: Help" --scope ui --tag menu
# EXPECT: Runbook gui-menu-help.json created
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 7: Add Help Menu Steps
run maestro runbook step-add gui-menu-help --actor user --action "Click Help → About" --expected "About dialog displays app version"
run maestro runbook step-add gui-menu-help --actor user --action "Click Help → Check for Updates" --expected "Update check runs, reports status"
# EXPECT: Help menu steps added
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 8: Create Workflow for File Menu
run maestro workflow init file-menu-workflow --from-runbook gui-menu-file  # TODO_CMD
# EXPECT: Workflow JSON created from File menu runbook
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 9: Add Workflow Nodes (Interface Layer)
run maestro workflow node add file-menu-workflow --layer manager_intent --label "Manager defines File menu structure"  # TODO_CMD
run maestro workflow node add file-menu-workflow --layer user_intent --label "User wants to create/open/save/export files"  # TODO_CMD
run maestro workflow node add file-menu-workflow --layer interface --label "Menu: File → New/Open/Save/Export"  # TODO_CMD
# EXPECT: Workflow nodes added (layered)
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 10: Create Workflow for Edit Menu
run maestro workflow init edit-menu-workflow --from-runbook gui-menu-edit  # TODO_CMD
# EXPECT: Workflow JSON created from Edit menu runbook
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 11: Add Interface Nodes for Edit
run maestro workflow node add edit-menu-workflow --layer interface --label "Menu: Edit → Undo/Redo/Cut/Copy/Paste"  # TODO_CMD
# EXPECT: Edit menu interface layer node added
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 12: Validate Workflows
run maestro workflow validate file-menu-workflow  # TODO_CMD
run maestro workflow validate edit-menu-workflow  # TODO_CMD
# EXPECT: Both workflows validate successfully
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: (none)
# INTERNAL: UNKNOWN

# Step 13: Render Workflows
run maestro workflow render file-menu-workflow --format puml  # TODO_CMD
# EXPECT: .puml and .svg created
# STORES_WRITE: (exports directory)
# GATES: (none)
# INTERNAL: UNKNOWN

# Step 14: Create Track for GUI Implementation (Optional)
run maestro track add "Sprint 2: Implement File Menu" --start 2025-02-01
# EXPECT: Track track-001 created
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 15: Create Tasks from Workflow Nodes
run maestro phase add track-001 "P1: File Menu Actions"
# EXPECT: Phase phase-001 created
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

run maestro task add phase-001 "Implement File → New action"
run maestro task add phase-001 "Implement File → Open action"
run maestro task add phase-001 "Implement File → Export submenu"
# EXPECT: Tasks created from menu actions
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

echo ""
echo "EX-11 Outcome A: GUI menu structure modeled in runbooks, workflows extracted"
echo "Runbooks: ./docs/maestro/runbooks/gui-menu-{file,edit,help}.json"
echo "Workflows: ./docs/maestro/workflows/{file,edit}-menu-workflow.json"
echo "Value: Menu structure documented without implementation"
echo "Next: Optionally implement GUI code from runbook/workflow spec"
