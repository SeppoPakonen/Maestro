# UNDERSTANDING.md

This document contains a list of assumptions and decisions that are not always explicitly stated, but are evident in the project's behavior, structure, and evolution.

## User Assumptions

### Who the user is assumed to be
*   **A technically proficient developer or project manager.** The user is expected to be comfortable with the command line, git, and Markdown. They are not a casual user.
    *   **Evidence**: The entire interface is a CLI. The data is stored in Markdown files that the user is expected to be able to read and even edit. The `DEV_WORKFLOW.md` file outlines a git workflow that assumes a high degree of git proficiency.
    *   **Impact**: If the user is not comfortable with these technologies, they will find Maestro difficult to use.

### What the user is assumed to know
*   **The project's "musical" philosophy.** The user is expected to understand the metaphors of "composition," "conductor," "orchestra," etc., that are used throughout the project.
    *   **Evidence**: The `README.md` is filled with these metaphors, and they are not explained in a way that would be accessible to someone who is not already familiar with them.
    *   **Impact**: If the user does not understand these metaphors, they may find the project's documentation and a lot of the naming confusing.

### What the user is *not* protected from
*   **Making manual changes that break the data format.** While the system has a structured way of interacting with the data, the user is free to edit the Markdown files directly. If they make a mistake, they can break the system.
    *   **Evidence**: The `DATA_FORMAT.md` file explicitly states that the files are "Human-readable" and can be edited directly. The error handling section of the same document describes what happens when a parsing error occurs, which implies that such errors are expected.
    *   **Impact**: This gives the user a lot of power and flexibility, but it also means that they can easily shoot themselves in the foot.

## AI Assumptions

### Expected AI capabilities
*   **The ability to follow structured prompts.** The entire AI interaction model is based on the idea that the AI will follow the 5-section prompt contract.
    *   **Evidence**: `docs/prompt_contract.md` and `tests/test_ai_discuss_router.py`.
    *   **Impact**: If the AI does not follow the prompt contract, the system will not be able to parse its response and the interaction will fail.
*   **The ability to generate JSON.** The AI is expected to generate JSON that conforms to the `JsonContract` for the current discussion scope.
    *   **Evidence**: `maestro/commands/discuss.py` and `tests/test_ai_discuss_router.py`.
    *   **Impact**: If the AI does not generate valid JSON, the system will not be able to extract the proposed changes.
*   **The ability to engage in a "discussion."** The conversational planning and discussion features assume that the AI can hold a coherent conversation with the user.
    *   **Evidence**: The `README.md` and the `maestro/commands/discuss.py` file.
    *   **Impact**: If the AI is not a good conversationalist, the user will have a frustrating experience.

### Trust boundaries
*   **AI may mutate project state through Maestro's rule-based assertive validation layer.** AI is not categorically prevented from acting independently; rather, its actions are channeled through Maestro's rigorous validation and enforcement mechanisms. Direct manual edits to `docs/*.md` are generally avoided by users (unless performing explicit corrections) not because AI is fundamentally untrusted, but because Maestro provides a robust, rule-based layer that:
    *   **Enforces structural, syntactic, and semantic correctness.** Any proposed change that violates these rules will block continuation, ensuring project integrity.
    *   **Guarantees auditability and predictability.** All changes are mediated and validated, allowing for clear understanding of "why" and "how" a change occurred.
    *   **Evidence**: The `maestro/commands/discuss.py` file demonstrates this by processing `PatchOperation` objects and requiring explicit confirmation *after* Maestro's internal validation. The `README.md` alludes to "Prompt Contract Enforcement" and "Architectural Rule: AI Never Mutates Project State Directly" (which is now clarified to mean "directly by the AI, bypassing Maestro's rules"). Autonomy is project-dependent and configurable via settings like `ai_dangerously_skip_permissions`, indicating that independent action can be enabled under specific, controlled conditions.
    *   **Impact**: This design allows AI to be a powerful agent of change while maintaining project integrity and human oversight via clearly defined rules, not passive prevention.

### Failure modes that are tolerated vs unacceptable
*   **Non-conformant AI responses are a hard stop and block progress.** If the AI generates a response that does not conform to the expected JSON contract or is syntactically invalid, this is **not tolerated** and results in a hard stop. The system is designed to immediately surface such failures to the user.
    *   **Evidence**: The `maestro/commands/discuss.py` file, in `run_discussion_with_router`, implicitly relies on the `JsonContract` to validate the AI's output. Any failure to parse or validate the JSON output would prevent the creation of `PatchOperation` objects, thereby blocking any proposed changes. The `DATA_FORMAT.md` file's description of error handling for parsing errors reinforces this: "Stop the operation immediately", "Display the error", "Offer two options: Manual fix, AI fix". This behavior is intentional, designed to **surface AI failure early** and prevent silent continuation with incorrect data. Recovery is manual or requires an explicit retry/re-prompt.
*   **Unacceptable**: The AI directly mutating project state. This is prevented by the architecture.

## Usage Intent

### Intended workflows
*   **Iterative, branching project development.** The system is designed to support a workflow where the user and AI collaborate to explore different ideas and approaches. The "branching plans" feature is a key part of this.
    *   **Evidence**: The `README.md`'s description of "Branching Plans" and the project's overall philosophy.
*   **Human-in-the-loop AI-assisted development.** The user is always in control, and the AI is there to assist, not to replace.
    *   **Evidence**: The "AI Never Mutates Project State Directly" rule and the conversational planning feature.

### Anti-goals (what this system resists or refuses to optimize for)
*   **Uncontrolled automation.** While Maestro supports fully automated, long-running, single-command initiated workflows (which are valuable for stress-testing and feature validation), it resists *uncontrolled* automation. The system is designed to enable powerful AI-driven workflows but always within defined rules and explicit oversight, rather than operating as a "magic bullet" without boundaries. These automated workflows are not the default mode of operation but are intentionally supported and necessary.
*   **Simplicity at the expense of power.** The system is complex, but this complexity is a necessary trade-off for the power and flexibility it provides.
*   **A user-friendly graphical interface.** The focus is on a powerful and scriptable CLI. A TUI is planned, but it is not a priority.

## Evolved Decisions

### Assumptions that appear to have changed over time
*   **Data storage format.** The project is in the process of migrating from a JSON-based data format to a Markdown-based format. This is a major change that affects the entire system.
    *   **Evidence**: The `docs/DATA_FORMAT.md` file explicitly describes the migration strategy. The presence of both `.maestro/` and `docs/` directories, and the migration tests (`test_discussion_migration.py`, `test_settings_migration.py`) confirm this.
*   **Qwen integration.** The Qwen AI engine was originally integrated in a different way, and there is legacy code to support the old integration.
    *   **Evidence**: The `qwen-old` command in `maestro/commands/ai.py`.
*   **TUI development.** The presence of `tui_backup` and `tui_mc2_backup` directories, and the large number of TUI-related tests, suggest that the TUI has been a focus of development in the past, but is not currently being actively developed. The `feature_matrix.md` confirms this.

### Evidence of refinement or correction
*   **The move to a Markdown-based data format.** This is a clear example of the project evolving to better meet its goals of being human-readable, version-controllable, and AI-friendly.
*   **The introduction of the unified AI engine manager.** This is a refinement that makes the system more modular and easier to extend with new AI engines.
*   **The strict prompt contract.** This is a correction to the ad-hoc way that prompts were likely handled in the past.

### Areas where earlier code/docs likely no longer reflect current intent
*   **Anything related to the old JSON-based data format.** Any code or documentation that refers to the `.maestro/` directory as the primary source of truth is likely outdated.
*   **The old Qwen integration.** Any code or documentation that refers to the old way of integrating with Qwen is likely outdated.
*   **TUI documentation.** Any documentation that describes the TUI as being fully implemented is outdated. The `feature_matrix.md` is the most up-to-date source of information on the TUI's status.
