# EX-11: Model an Existing GUI App Menu as Runbooks — Runbook→Workflow (Interface Layer)

**Scope**: Runbook-first UI/UX modeling (no code required initially)
**Build System**: N/A (modeling only)
**Languages**: N/A (conceptual modeling)
**Outcome**: Create runbooks modeling a hypothetical GUI menu tree, extract workflow showing interface layer nodes, demonstrate runbook value for design-first

---

## Scenario Summary

Product manager wants to document an existing desktop application's menu structure before refactoring it. Instead of jumping to code or wireframes, they use runbooks to model each menu action as user steps, then extract a workflow graph showing the interface layer structure.

This demonstrates **runbook-first for UI modeling**: you don't need implementation to capture user experience.

---

## Preconditions

- Maestro initialized
- No code exists yet (or existing GUI app being documented)
- Focus is on modeling menu structure and user flows

---

## Hypothetical GUI Menu Tree

```
MyTextEditor (Desktop App)
├── File
│   ├── New                 (Ctrl+N)
│   ├── Open...             (Ctrl+O)
│   ├── Save                (Ctrl+S)
│   ├── Save As...
│   ├── Export
│   │   ├── Export as PDF
│   │   ├── Export as HTML
│   │   └── Export as Markdown
│   └── Exit                (Ctrl+Q)
├── Edit
│   ├── Undo                (Ctrl+Z)
│   ├── Redo                (Ctrl+Y)
│   ├── Cut                 (Ctrl+X)
│   ├── Copy                (Ctrl+C)
│   └── Paste               (Ctrl+V)
└── Help
    ├── Documentation
    ├── About
    └── Check for Updates
```

---

## Runbook Steps

### Step 1: Initialize Maestro

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro init` | Create repo truth | `./docs/maestro/**` created |

### Step 2: Create Runbook for File Menu

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro runbook add --title "GUI Menu: File" --scope ui --tag menu` | Model File menu | Runbook `gui-menu-file.json` created |

### Step 3: Add File Menu Steps

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro runbook step-add gui-menu-file --actor manager --action "Define File menu structure" --expected "Menu items documented"` | Manager intent | Step added |
| `maestro runbook step-add gui-menu-file --actor user --action "Click File → New (or Ctrl+N)" --expected "New document created"` | User action | Step added |
| `maestro runbook step-add gui-menu-file --actor user --action "Click File → Open (or Ctrl+O)" --expected "File picker dialog opens"` | User action | Step added |
| `maestro runbook step-add gui-menu-file --actor user --action "Click File → Save (or Ctrl+S)" --expected "Document saved to disk"` | User action | Step added |
| `maestro runbook step-add gui-menu-file --actor user --action "Click File → Export → Export as PDF" --expected "PDF export dialog opens"` | User action (submenu) | Step added |

### Step 4: Create Runbook for Edit Menu

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro runbook add --title "GUI Menu: Edit" --scope ui --tag menu` | Model Edit menu | Runbook `gui-menu-edit.json` created |

### Step 5: Add Edit Menu Steps

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro runbook step-add gui-menu-edit --actor user --action "Click Edit → Undo (or Ctrl+Z)" --expected "Last action undone"` | User action | Step added |
| `maestro runbook step-add gui-menu-edit --actor user --action "Click Edit → Copy (or Ctrl+C)" --expected "Selection copied to clipboard"` | User action | Step added |

### Step 6: Create Runbook for Help Menu

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro runbook add --title "GUI Menu: Help" --scope ui --tag menu` | Model Help menu | Runbook `gui-menu-help.json` created |

### Step 7: Add Help Menu Steps

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro runbook step-add gui-menu-help --actor user --action "Click Help → About" --expected "About dialog displays app version"` | User action | Step added |
| `maestro runbook step-add gui-menu-help --actor user --action "Click Help → Check for Updates" --expected "Update check runs, reports status"` | User action | Step added |

---

## Workflow Extraction (Runbook → Workflow)

### Step 8: Create Workflow for File Menu

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro workflow init file-menu-workflow --from-runbook gui-menu-file` | Extract File menu workflow | Workflow JSON created |

### Step 9: Add Workflow Nodes (Interface Layer)

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro workflow node add file-menu-workflow --layer manager_intent --label "Manager defines File menu structure"` | Manager intent | Node added |
| `TODO_CMD: maestro workflow node add file-menu-workflow --layer user_intent --label "User wants to create/open/save/export files"` | User intent | Node added |
| `TODO_CMD: maestro workflow node add file-menu-workflow --layer interface --label "Menu: File → New/Open/Save/Export"` | Interface layer (menu tree) | Node added |

**Key Point:** Interface layer captures menu structure without implementation details.

### Step 10: Create Workflow for Edit Menu

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro workflow init edit-menu-workflow --from-runbook gui-menu-edit` | Extract Edit menu workflow | Workflow JSON created |

### Step 11: Add Interface Nodes for Edit

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro workflow node add edit-menu-workflow --layer interface --label "Menu: Edit → Undo/Redo/Cut/Copy/Paste"` | Interface layer | Node added |

### Step 12: Validate Workflows

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro workflow validate file-menu-workflow` | Validate File menu workflow | Passes |
| `TODO_CMD: maestro workflow validate edit-menu-workflow` | Validate Edit menu workflow | Passes |

### Step 13: Render Workflows

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro workflow render file-menu-workflow --format puml` | Generate PlantUML | `.puml` and `.svg` created |

---

## Plan Creation (Optional — If Implementing GUI)

### Step 14: Create Track for GUI Implementation

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro track add "Sprint 2: Implement File Menu" --start 2025-02-01` | Create implementation track | Track `track-001` created |

### Step 15: Create Tasks from Workflow Nodes

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro phase add track-001 "P1: File Menu Actions"` | Add phase | Phase created |
| `maestro task add phase-001 "Implement File → New action"` | Task for New | Task created |
| `maestro task add phase-001 "Implement File → Open action"` | Task for Open | Task created |
| `maestro task add phase-001 "Implement File → Export submenu"` | Task for Export | Task created |

---

## AI Perspective (Heuristic)

**What AI notices:**
- Runbook steps are all `actor: user` with menu click actions
- No code layer nodes in workflow → pure interface modeling
- Menu structure forms a tree (File/Edit/Help with submenus)

**What AI tries:**
- Extract menu hierarchy from runbook steps
- Create workflow interface layer nodes mirroring menu structure
- Suggest implementation tasks based on menu actions

**Where AI tends to hallucinate:**
- May assume specific GUI framework (Qt/GTK/Electron) when none specified
- May generate code stubs when modeling-only was requested
- May conflate "Export → PDF" with full PDF rendering implementation

---

## Outcomes

### Outcome A: Success — Menu Modeled, Workflow Extracted

**Result:** All menus documented as runbooks, workflows created showing interface layer structure

**Artifacts:**
- Runbooks: `./docs/maestro/runbooks/gui-menu-file.json`, `gui-menu-edit.json`, `gui-menu-help.json`
- Workflows: `./docs/maestro/workflows/file-menu-workflow.json`, etc.
- No code written (modeling complete)

**Value:**
- Product team can review menu structure without implementation
- Workflow graphs serve as UI specification
- Implementation can proceed later with clear requirements

### Outcome B: Ambiguity in Menu Actions → Runbook Revised

**Result:** During workflow extraction, team realizes "Export" submenu needs more detail

**Recovery:**
1. Revise runbook: add steps for each export format (PDF/HTML/Markdown)
2. Re-extract workflow with updated steps
3. Workflow now includes distinct interface nodes per export type

### Outcome C: Implementation Triggered

**Result:** After modeling, team decides to implement File menu first

**Flow:**
1. Create track/phase/task from workflow nodes
2. Start `maestro work` with runbook/workflow context
3. AI generates GUI code (e.g., Python + tkinter) based on menu structure from runbooks

---

## Minimal Code (Optional — If Implementing)

**Python + tkinter stub** (generated from runbook if implementation requested):

```python
import tkinter as tk
from tkinter import filedialog, messagebox

class TextEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("MyTextEditor")

        # Create menu bar
        menubar = tk.Menu(root)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New", command=self.file_new, accelerator="Ctrl+N")
        file_menu.add_command(label="Open...", command=self.file_open, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self.file_save, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=root.quit, accelerator="Ctrl+Q")
        menubar.add_cascade(label="File", menu=file_menu)

        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo", command=self.edit_undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Copy", command=self.edit_copy, accelerator="Ctrl+C")
        menubar.add_cascade(label="Edit", menu=edit_menu)

        root.config(menu=menubar)

        # Text widget
        self.text = tk.Text(root)
        self.text.pack(fill=tk.BOTH, expand=True)

    def file_new(self):
        self.text.delete("1.0", tk.END)

    def file_open(self):
        filename = filedialog.askopenfilename()
        if filename:
            with open(filename, 'r') as f:
                self.text.delete("1.0", tk.END)
                self.text.insert("1.0", f.read())

    def file_save(self):
        messagebox.showinfo("Save", "Save functionality here")

    def edit_undo(self):
        self.text.edit_undo()

    def edit_copy(self):
        self.text.event_generate("<<Copy>>")

if __name__ == '__main__':
    root = tk.Tk()
    app = TextEditor(root)
    root.mainloop()
```

**Note:** Code generation is optional. The runbook-first value is in modeling before implementation.

---

## CLI Gaps / TODOs

```yaml
cli_gaps:
  - "TODO_CMD: maestro workflow init <name> --from-runbook <id>"
  - "TODO_CMD: maestro workflow node add <id> --layer interface --label <text>"
  - "TODO_CMD: maestro workflow validate <id>"
  - "TODO_CMD: maestro workflow render <id> --format puml"
```

---

## Trace Block (YAML)

```yaml
trace:
  - user: "maestro runbook add --title 'GUI Menu: File' --scope ui --tag menu"
    intent: "Model GUI File menu structure without code"
    gates: ["REPOCONF_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "high"

  - user: "maestro runbook step-add gui-menu-file --actor user --action 'Click File → New (or Ctrl+N)' ..."
    intent: "Document user action for File → New"
    gates: ["REPOCONF_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "high"

  - user: "maestro workflow init file-menu-workflow --from-runbook gui-menu-file"
    intent: "Extract workflow from runbook menu structure"
    gates: ["REPOCONF_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro workflow node add file-menu-workflow --layer interface --label 'Menu: File → New/Open/Save/Export'"
    intent: "Create interface layer node for menu tree"
    gates: ["REPOCONF_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "low"  # TODO_CMD
```

---

**Related:** UI/UX modeling, design-first development, interface layer workflows
**Status:** Proposed
