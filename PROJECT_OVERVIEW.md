# PROJECT_OVERVIEW.md

## A. High-level Identity

### What the project is
Maestro is a command-line AI Task Orchestrator designed to manage complex software projects by coordinating multiple AI models. It acts as a "conductor," guiding a variety of AI "instruments" (planners, workers, refiners) to compose a project organically. The core philosophy is that creativity and development are branching, non-linear processes, and Maestro is built to support this through conversational planning and a tree-like project structure.

### What it explicitly is *not*
Maestro is not a simple, linear pipeline that pushes tasks from one stage to the next. It is also not a fully autonomous system that removes the human from the loop. Instead, it is a collaborative tool that positions the human as the ultimate creative director, with AI acting as a powerful, versatile ensemble. It is not a tool for developers who want a "fire-and-forget" solution.

### Primary design philosophy
The primary design philosophy of Maestro is that complex projects are "composed," not just built. This is reflected in the use of musical metaphors (conductor, orchestra, composition, motifs, movements). The system is designed to embrace the messy, iterative, and branching nature of creative work. It prioritizes human intuition and guidance while leveraging AI for execution and exploration.

## B. Structural Map

### Tracks / Phases / Tasks
The project is organized into a hierarchy of Tracks, Phases, and Tasks.
- **Tracks** represent high-level themes or workstreams.
- **Phases** break down Tracks into manageable stages.
- **Tasks** are the individual work items within a Phase.

This structure is explicitly managed through CLI commands and is reflected in the JSON store under `docs/maestro/`.

### Major directories and their roles
- **`maestro/`**: The core application logic.
- **`docs/`**: The "single source of truth" for project state, configuration, and documentation. This directory is critical and contains:
    - **`config.md`**: Project configuration.
    - **`maestro/`**: JSON store for tracks, phases, and tasks.
    - **`repo/`**: The state of the scanned repository.
    - **`discussions/`**: The history of AI conversations.
- **`.maestro/`**: A legacy directory, partially migrated to `docs/`, which still contains build artifacts and other runtime data.
- **`tests/`**: The project's test suite.
- **`external/`**: Git submodules for external AI agent CLIs.

### Where “truth” lives (docs vs code vs config)
The project stores its "single source of truth" in JSON under `docs/maestro/`, keeping state structured, version-controllable, and easy to audit.

## C. Temporal Model

### How TODO, DONE, history, and future intent are represented
- **TODO**: Active tracks, phases, and tasks are stored in `docs/maestro/` and marked by status fields.
- **DONE**: Completed work is represented by status fields in the JSON store.
- **History**: The project's history is captured in several places:
    - The git history of the `docs/` directory provides a complete audit trail of project state changes.
    - `sessions/<session>/inputs/` and `sessions/<session>/outputs/` store the raw prompts and responses from AI interactions.
    - `docs/discussions/` stores the history of AI conversations in a more structured format.
- **Future Intent**: Future intent is represented by the "planners" and the "conversational planning" feature. The user and AI collaborate to define the project's future direction, which is then captured in `docs/maestro/`.

### What constitutes “state” in this project
The state of the project is a combination of:
- The content of the `docs/` directory (the "source of truth").
- The state of the scanned repository, as captured in `docs/repo/`.
- The history of AI interactions, stored in `sessions/` and `docs/discussions/`.
- The current context (`current_track`, `current_phase`, `current_task`), which is stored in `docs/config.md`.

## D. Interaction Model

### How humans interact with the system
Humans interact with Maestro primarily through the command-line interface (CLI). The CLI provides a rich set of commands for:
- Session management.
- Planning (interactive and one-shot).
- Resuming execution.
- Managing tracks, phases, and tasks.
- Managing configuration.
- Interacting with the AI discussion system.

A Text-based User Interface (TUI) is planned but not yet implemented. The `feature_matrix.md` clearly indicates that the CLI is the mature and stable interface.

### How AI services interact with the system
AI services interact with the system in a highly structured and controlled manner:
- **Prompt Contract**: All AI prompts must adhere to a strict 5-section contract.
- **Centralized Builder**: A `build_prompt()` function ensures all prompts are created consistently.
- **Engine Roles**: Each AI engine has a defined role (planner, worker, or both).
- **No Direct Mutation**: A critical architectural rule is that **AI never directly mutates project state**. Instead, AI proposes changes as structured JSON operations, which must be explicitly approved by the user.
- **Persistence**: All AI interactions are logged for traceability and debugging.

### Where responsibility boundaries are drawn
- **Human**: The human is the creative director. They are responsible for guiding the project, making decisions, and approving all changes to the project state.
- **Maestro**: Maestro is the orchestrator. It is responsible for managing the project state, interacting with the user, and coordinating the AI engines.
- **AI**: The AI engines are the "instruments." They are responsible for executing tasks as directed by Maestro and the user, but they are not given the authority to make unilateral decisions or changes.
