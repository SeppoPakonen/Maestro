![Banner](docs/banner.jpg)

# **Maestro — AI Task Orchestrator**

Copyright 2025 Seppo Pakonen

### *AI–Driven Project Composition & Branching Workflow Conductor*

Maestro is a command-line tool for composing complex projects with multiple AI models.
Rather than pushing tasks through a linear pipeline, Maestro behaves like a *conductor* guiding an orchestra of models — planners, workers, refiners — each an instrument with its own voice.

A project planned with Maestro grows organically, like a living composition:
themes develop, branches emerge, variations unfold, and motifs resolve across multiple voices.

Maestro helps humans and AIs work together to **shape, refine, and restructure** ambitious ideas — one movement at a time.

---

## Features

### **1. Conversational Planning (The Opening Movement)**

Plans don't appear fully formed  they are *composed*.
Maestro lets you **talk** with its planning AIs:

* Discuss, revise, and sculpt the plan
* Rewrite or clean" the root task
* Break the project into subtasks
* Control how much of the root task is given to each worker

You can conduct this process in two modes:

* **Interactive planning** (`--discuss-plan`)
  Talk with the AI until the structure feels right.

* **One-shot planning** (`--one-shot-plan`)
  Produce a clean JSON plan in a single gesture.

If neither mode is specified, Maestro politely asks which style you prefer.

---

### **2. Branching Plans (Fugues, Variations, and Development)**

Real projects don't move in straight lines — they branch.
Maestro treats planning as a **tree of musical ideas**:

* Every plan is a *motif*: a node in a branching structure
* You can create new branches mid-project
* Old branches remain as "dead ends" or alternative interpretations
* You can freely switch focus between branches
* A plan tree can be printed as colored ASCII score-like structure:

```
[*] P1  Main Theme (active)
 ├─ P2  Variant: Split Backend
 │    └─ P3  Variant: Minimal API (dead)
 └ P4  Variant: Test-Driven Rewrite
```

Each branch represents a different interpretation of your original composition.

---

### **3. Multi-Engine Orchestration (Your Orchestra of AIs)**

Maestro assigns roles according to each model's strengths:

**Planners**

* **Codex** – architectural motifs, structural design, advanced debugging
* **Claude** – deep reasoning, complex refinement, expressive thought

**Workers**

* **Qwen** – implementation, coding, straightforward bugfixing
* **Gemini** – natural-language heavy tasks, research, summarization

Each subtask receives a carefully crafted prompt with:

* cleaned root task excerpt
* relevant categories (like instrumental sections)
* context from previous movements
* optional partial outputs from interrupted runs

---

### **4. Intelligent Root Task Handling (From Sketch to Score)**

Instead of shoving the raw root task into every prompt, Maestro:

* rewrites your root task into a **clean, musical score**
* extracts conceptual **categories** (sections, voices, instruments)
* assigns only the relevant sections to each subtask
* optionally produces excerpts for workers

This keeps prompts focused, reducing noise and creative drift.

---

### **5. Graceful Interrupts (The Pause Between Movements)**

If you press **Ctrl+C**, Maestro behaves like a seasoned conductor:

* Stops the current AI subprocess gently
* Captures all partial output
* Saves it as part of the project history
* Marks the subtask as *interrupted*
* Allows a later continuation, including partial context in the next prompt

No stack traces. No lost work. No broken flow.

---

### **6. Rich Session State & Continuity (The Concert Archive)**

Maestro stores:

* root task raw + cleaned version
* categories + excerpts
* plan tree nodes
* subtask statuses
* all input prompts
* all raw AI outputs
* partial results
* user-facing summaries

Maestro ensures that every run is reproducible — every rehearsal preserved.

---

## Installation

```bash
git clone https://github.com/OuluBSD/maestro.git
cd maestro
pip install -r requirements.txt
```

If you want the forked AI agent CLIs used by Maestro, clone with submodules:

```bash
git clone --recurse-submodules git@github.com:OuluBSD/maestro.git
```

Or initialize them later:

```bash
git submodule update --init --recursive
```

Submodules live under `external/ai-agents/`:

```text
external/ai-agents/qwen-code
external/ai-agents/gemini-cli
```

Or editable install:

```bash
pip install -e .
```

For running the full test/TU suite and GUI completion helper, install dev extras in your virtualenv:

```bash
python -m venv venv
./venv/bin/pip install -r requirements-dev.txt
```

If libclang is not discovered automatically, point to it (e.g. on clang 21):

```bash
export LIBCLANG_PATH=/usr/lib/llvm/21/lib64/libclang.so
```

Legacy root smoke/semantic integrity harnesses are kept as `_legacy.py` to avoid pytest duplicate-module clashes; run the maintained suites under `tests/`.

---

## Usage

### Create a new session:

```bash
echo "Build a MIDI-driven sandbox game engine" \
  | maestro --session sessions/game.json --new
```

### Start planning:

```bash
maestro --session sessions/game.json --plan
```

(defaults to interactive discussion)

### Or produce a plan in one gesture:

```bash
maestro -s sessions/game.json --one-shot-plan
```

### Resume execution:

```bash
maestro -s sessions/game.json --resume
```

### Show the branching plan tree:

```bash
maestro -s sessions/game.json --show-plan-tree
```

### Shift the conductor's focus:

```bash
maestro -s sessions/game.json --focus-plan P4
```

---

## Philosophy

> *To compose is to discover.*
> And discovery is rarely linear.

Maestro assumes:

* Creativity grows through branching ideas
* Plans evolve like musical themes  explored, revisited, refined
* AI is best used as a collaborative instrument, not a silent worker
* Human intuition guides the music; AI provides the ensemble
* Every project is a symphony in progress

Maestro exists to ensure your composition — technical or artistic — can unfold freely, gracefully, and intelligently.

---

## Automation, Autonomy, and Assertive Control

Maestro is designed to facilitate powerful AI-driven workflows, including those that are fully automated and operate autonomously. The system’s safety and reliability stem from a robust **rule-based assertive validation layer**, rather than a blanket restriction on AI action.

*   **Configurable Autonomy**: AI can operate autonomously when configured to do so, for example, in scenarios like stress-testing, automated refactoring, or continuous integration pipelines. This is not the default mode but is a fully supported and intentional capability.
*   **Safety Through Rules**: All AI-initiated actions, whether proposed for human review or executed autonomously, are funneled through Maestro’s validation mechanisms. These mechanisms enforce structural, syntactic, and semantic correctness, ensuring that only valid and coherent changes are applied to the project state.
*   **Controlled Mutation**: AI *may* mutate project state when these actions are mediated and validated by Maestro. The system resists *uncontrolled* automation, guaranteeing that every change is auditable and adheres to predefined rules. This ensures predictability and maintains the integrity of the project.

---

## Prompt Contract Enforcement

Maestro enforces a **strict, auditable prompt contract** for all AI invocations to ensure:

* Every AI invocation is structurally predictable
* Missing context is explicit, not accidental
* Prompt drift is prevented across refactors
* Debugging becomes mechanical instead of interpretive

### Required Structure

Every AI prompt must include 5 required sections in exact order:

```
[GOAL]
[CONTEXT]
[REQUIREMENTS]
[ACCEPTANCE CRITERIA]
[DELIVERABLES]
```

### Validation

All prompts undergo validation before AI invocation:
* All required sections must exist
* Sections must be in correct order
* No section may be empty
* If validation fails, operation is aborted

### Persistence

All AI interactions are logged:
* Input prompts saved to: `sessions/<session>/inputs/`
* AI outputs saved to: `sessions/<session>/outputs/`
* Includes complete structured prompts and raw responses

For full technical details, see `docs/prompt_contract.md`.

---

## License

New BSD

## Confidence Scoring System

Maestro includes a comprehensive confidence scoring system that provides numeric confidence scores for conversion runs, enabling data-driven decisions about conversion quality and readiness for deployment.

### Overview

The confidence scoring system assigns a numeric score (0-100) and letter grade (A-F) to each conversion run based on multiple quality indicators:

- Semantic integrity results
- Cross-repo semantic diff analysis
- Idempotency and drift detection
- Checkpoint activity
- Arbitration outcomes
- Arbitration Arena TUI for comparing competing AI outputs
- Open issues and warnings
- Validation results

### Configuration

The scoring model is configured via `.maestro/convert/scoring/model.json`:

```json
{
  "version": "1.0",
  "scale": [0, 100],
  "weights": {
    "semantic_integrity": 0.35,
    "semantic_diff": 0.20,
    "drift_idempotency": 0.20,
    "checkpoints": 0.10,
    "open_issues": 0.10,
    "validation": 0.05
  },
  "penalties": {
    "semantic_low": 40,
    "semantic_medium": 15,
    "semantic_unknown": 8,
    "lost_concept": 3,
    "checkpoint_blocked": 10,
    "checkpoint_overridden": 6,
    "idempotency_failure": 20,
    "drift_detected": 15,
    "non_convergent": 25,
    "open_issue": 2,
    "validation_fail": 25
  },
  "floors": {
    "any_semantic_low": 30
  }
}
```

### CLI Commands

#### Show Confidence for a Run

```bash
maestro convert confidence show           # Show most recent run
maestro convert confidence show --run-id run_1234567890  # Show specific run
```

#### Confidence History

```bash
maestro convert confidence history       # Show last 10 runs
maestro convert confidence history --limit 20  # Show last 20 runs
```

#### CI Gate

```bash
maestro convert confidence gate --min-score 75  # Gate with minimum score
```

#### Batch Confidence

```bash
maestro convert batch report --spec batch.json  # Include confidence in report
maestro convert batch gate --spec batch.json --min-score 75 --aggregate min  # Batch gate
```

#### Promotion with Confidence Check

```bash
maestro convert promote --min-score 80        # Promote with confidence check
maestro convert promote --force-promote       # Force promotion regardless of score
```

### Integration

Confidence scores are automatically computed after each successful conversion run and stored in `.maestro/convert/runs/<run_id>/confidence.json` and `.maestro/convert/runs/<run_id>/confidence.md`.

Batch jobs also compute confidence scores, and batch-level confidence can be aggregated using mean, median, or min methods.

---

## Semantic Integrity Panel (TUI Feature)

The Semantic Integrity Panel is a dedicated TUI screen that makes semantic risks visible, understandable, and actionable by humans during code conversion. It addresses the critical question:

> "Yes, the code was converted — but did the intent survive?"

### Accessing the Panel

The Semantic Integrity Panel can be accessed through:

* **TUI Navigation**: Press `i` or click "Integrity" in the navigation menu
* **Command Palette**: `Ctrl+P` then select "Go to semantic integrity panel"
* **Keyboard Shortcut**: Direct access via `Ctrl+I` (in TUI)

### Three-Panel Layout

The panel features a three-panel layout for efficient workflow:

#### Left: Risk Summary
* Overall semantic health score (0-100%)
* Risk distribution: High, Medium, Low
* Status counts: Accepted, Rejected, Blocking
* Active gates/checkpoints (if any)

#### Center: Findings List
* Task ID, affected files, equivalence level
* Risk flags and current status
* Visual indicators for risk level
* Selectable with keyboard navigation

#### Right: Finding Details
* Detailed explanation from semantic analysis
* Before/after conversion evidence
* Current disposition and decision reason
* Impact assessment: blocks pipeline? checkpoint ID

### Human Action Controls

Each finding supports four human actions with safety measures:

* **Accept (A)**: Mark as reviewed and accepted (with confirmation)
* **Reject (R)**: Mark as rejected with required reason (blocks pipeline)
* **Defer (D)**: Leave unresolved, keeps gate (with confirmation)
* **Explain (E)**: Show detailed rationale history

### Command Palette Integration

Semantic operations are also available via command palette (`Ctrl+P`):

* `semantic list` - Show summary of all findings
* `semantic show <id>` - Show detailed finding information
* `semantic accept <id>` - Accept a specific finding
* `semantic reject <id>` - Reject a specific finding with reason
* `semantic defer <id>` - Defer a specific finding

### Gate & Checkpoint Integration

The panel integrates directly with the conversion pipeline:
* Shows which findings are currently blocking
* Displays associated checkpoint IDs
* Updates pipeline status immediately when findings are resolved
* Maintains audit trail of all human decisions

---

## Architectural Principle: Rule-Enforced AI Control and Mutation Boundaries

Maestro operates under a critical architectural principle: **AI actions on project state are always mediated and validated by Maestro's assertive control layer.** This means AI does not *bypass* Maestro to make changes. Instead, it interacts through structured mechanisms that enforce deterministic, reviewable changes and maintain project integrity.

### How It Works

1. **AI Initiates Actions**: AI models generate structured JSON operations (e.g., via the DiscussionRouter) that represent desired changes or proposals.
2. **Maestro's Validation Layer**: All AI-initiated operations are subjected to Maestro's rule-based validation. This layer rigorously checks for structural, syntactic, and semantic correctness against predefined contracts and project rules. Invalid operations are rejected.
3. **Controlled Application**: Depending on configuration (e.g., manual approval, `ai_dangerously_skip_permissions` setting), valid operations are either:
    *   **Proposed for Human Review**: Displayed as a diff-like preview requiring explicit user approval before application. This is the default for interactive workflows.
    *   **Applied Autonomously**: Executed directly by Maestro if configured for autonomous mode (e.g., in CI/CD, stress testing). This leverages Maestro's validation to ensure safety even without immediate human oversight.
4. **Audit Trail**: All discussions, proposed operations, and applied changes are logged with metadata, ensuring full auditability.

### JSON Patch Contracts

Each discussion scope has specific allowed operations that define what the AI can initiate and what Maestro will validate:

*   **Track Contract**: `add_track`, `add_phase`, `add_task`, `mark_done`, `mark_todo`
*   **Phase Contract**: `add_phase`, `add_task`, `move_task`, `edit_task_fields`, `mark_done`, `mark_todo`
*   **Task Contract**: `add_task`, `move_task`, `edit_task_fields`, `mark_done`, `mark_todo`

This structured approach ensures AI proposals are constrained to appropriate scopes and operations, and are always processed through Maestro's assertive control.
