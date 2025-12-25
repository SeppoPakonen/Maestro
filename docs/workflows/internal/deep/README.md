# Deep Internal Topology Documentation

This directory contains deep internal documentation for the Maestro CLI, detailing the execution topology and persistent state interactions for each top-level command and key cross-cutting subsystems.

## Conventions

*   **Call Chain Notation:** Call chains are represented as `module.py:function()` → `module2.py:Class.method()`. Each step includes a brief purpose.
*   **Persistent Store Representation:**
    *   `docs/` truth files: Markdown files within the `docs/` directory, representing the canonical source of project information (e.g., TODOs, DONEs, plans).
    *   Session JSON: The JSON file used to store the current working session state (`--session` argument).
    *   `$HOME/.maestro` registry/caches: Configuration, credentials, and cached data stored in the user's home directory.
    *   Deprecated `.maestro/` usage: Any legacy usage of `.maestro/` within the project directory.
*   **Global State / Configuration:** Listed with their origin (where set) and consumption points.
*   **PlantUML Diagrams:** Diagrams use PlantUML for visual representation of call graphs and data flow. Refer to `_shared.puml` for common styling and macros.

## PlantUML Interpretation

*   **Modules/Files:** Represented as packages or components.
*   **Functions:** Represented as nodes within modules.
*   **Arrows:** Indicate function calls.
*   **Special Nodes for Stores:** Distinct shapes/colors for persistent data stores (Docs Truth, Session Store, Home Registry, Cache).
*   **Annotated Edges:** Labels on arrows indicate data read/write operations, validation gates, or subprocess invocations.
*   **"Helper Cluster" Nodes:** To maintain legibility, deeply repeated or generic helper calls might be collapsed into these nodes.
*   **Labels:** Key elements like entrypoints, decision branches, and hard-stop points are explicitly labeled.
