---
id: WF-10
title: Repo Resolve levels — Lite vs Deep, convention acceptance, and violation policy
tags: [repo-resolve, detection, lite, deep, conventions, violations, issues, waivers, policy]
entry_conditions: "Operator requests `repo resolve` or another workflow triggers it."
exit_conditions: "Resolve completes (either Lite or Deep), results are stored, and any required user interactions (like acceptance) are complete or pending."
artifacts_created: "Updated Repo Truth Store (`./docs/maestro/`) with resolved model, conventions, violations, and waivers. New issues created in the issue tracking system."
failure_semantics: "Failure to detect a build driver in Lite mode is reported. Ambiguous conventions in Deep mode require user selection."
links_to: [WF-05, WF-09]
related_commands: "Proposed: `maestro repo resolve --level <lite|deep>`, `maestro repo conventions accept <pack>`, `maestro issues waive <id>`"
---

# WF-10: Repo Resolve Levels and Convention Policy

This workflow defines the different levels of repository resolution, the process for accepting inferred conventions, and the policy for handling violations. It serves as the canonical reference for how Maestro understands and governs repository structure.

## 1. Definitions: Resolve Levels

Repo Resolve operates at two distinct levels, serving different purposes.

### 1.1. Resolve Lite (Build-Enabling)

**Purpose:**
Resolve Lite is a fast, shallow scan designed to gather the minimum information required to configure, build, and test a repository. Its primary goal is to enable core development operations.

*   **Identify Packages/Assemblies:** Detects the fundamental code groupings within the repo.
*   **Detect Language(s):** Determines the programming languages in use.
*   **Detect Build System(s):** Identifies the build tools and drivers (e.g., Make, CMake, Maven).
*   **Enumerate Buildable Targets:** Lists the minimal set of targets or configurations required for `RepoConf` and subsequent build/test actions (see WF-07).

**Outputs:**
*   A minimal resolved model stored in the Repo Truth Store (per WF-09).
*   A list of buildable targets.
*   A set of candidate build drivers for selection.

**Hard Stops:**
*   The process halts if it cannot identify any build driver and no manual `RepoConf` exists to guide it. This would trigger a failure requiring manual intervention (see WF-11/WF-12, forthcoming).

### 1.2. Resolve Deep (Governance and Enforcement)

**Purpose:**
Resolve Deep is a comprehensive analysis that builds on Resolve Lite. It infers architectural conventions and enforces structural rules, enabling advanced governance and maintenance.

*   **Infer Conventions/Frameworks:** Detects project conventions (e.g., naming, directory structure) and framework-specific fingerprints (e.g., Qt, U++) as inferences with associated confidence scores.
*   **Apply Rule Packs:** Selects and applies convention libraries (rule packs) based on inferred conventions.
*   **Detect Structural Violations:** Identifies deviations from the active rule pack, such as incorrect file names, misplaced files, or prohibited co-location of certain components.
*   **Build Richer Dependency Graphs:** Constructs detailed dependency graphs between packages, libraries, and modules.

**Outputs:**
*   A detailed convention inference report, including confidence scores.
*   The selected or proposed rule pack(s).
*   A list of all detected violations.

**Hard Stops:**
*   Resolve Deep does not fail purely due to "unknown conventions." Instead, it falls back to an "unknown" state and may generate advisory issues, unless a specific policy mandates strict convention adherence.

## 2. Convention Acceptance / Lock-In

**Policy / Planned Feature**

To prevent erroneous enforcement, inferred conventions must be explicitly accepted by an operator before they are "locked-in."

**Rules:**
1.  **Proposal:** After a Deep Resolve, Maestro proposes a set of candidate convention rule packs that best match the repository.
2.  **Acceptance:** An operator must explicitly accept one of the proposed rule packs (or provide an alternative). This action is recorded in the Repo Truth Store.
3.  **Violation Status:**
    *   **Before Acceptance:** All detected violations are recorded as `Issues` but are marked with a status like `unconfirmed` or `candidate`. They are advisory and do not block builds or other workflows.
    *   **After Acceptance:** Upon lock-in, all existing and future violations of the accepted rule pack are marked as `confirmed`. Their enforcement (e.g., blocking a build) is determined by the project's policy.

## 3. Violations become Issues; Enforcement is Policy-Driven

**Rules:**
1.  **Issues are Always Created:** Every detected convention violation, whether `candidate` or `confirmed`, automatically generates an `Issue`.
2.  **Waivers:** Operators can choose to waive or ignore specific issues.
    *   Waivers are persistent and stored in the Repo Truth Store, as defined in **WF-09**.
    *   Waivers are stored in a designated file (e.g., `./docs/maestro/waivers.json`) and must reference the unique ID of the issue they apply to.
3.  **Enforcement is Policy-Driven:** A `confirmed` violation will only block a workflow (e.g., a build or merge) if the governing policy requires it AND the corresponding issue is not waived.

**Proposed Waiver Schema (`./docs/maestro/waivers.json`):**
```json
[
  {
    "issue_id": "VIOLATION-NAMING-001",
    "waived_by": "username",
    "waived_at": "2025-12-26T10:00:00Z",
    "reason": "Legacy module; scheduled for deprecation and not worth fixing."
  }
]
```

## 4. Integration Points

*   **WF-01 (Run Workflow) / WF-03 (Build Project):** The "detect build system" step in these workflows maps directly to **Resolve Lite**.
*   **WF-05 (Resolve Repo):** This workflow remains the canonical implementation surface for both Lite and Deep resolve operations. Other workflows should reference WF-10 for the *definition* of resolve levels.
*   **WF-07 (Analyze TU/AST):** The prerequisites for any TU-level analysis require, at a minimum, a successful **Resolve Lite** and a valid `RepoConf`.

## 5. Command Contracts

The following CLI commands are **Proposed** to implement this workflow.

*   `maestro repo resolve --level lite`: Performs a fast, build-enabling scan.
*   `maestro repo resolve --level deep`: Performs a full convention and violation analysis.
*   `maestro repo conventions accept <pack>`: Locks in a specific rule pack for convention enforcement.
*   `maestro issues waive <id> --reason "..."`: Creates a persistent waiver for a violation issue.

## 6. Failure Semantics

*   **Resolve Lite:** If no build driver can be detected, the process reports the failure and advises the operator on next steps (e.g., manual `RepoConf` creation).
*   **Resolve Deep:** If multiple convention packs are identified as equally likely candidates, the process requires explicit user selection and will not silently pick one unless a policy dictates otherwise.

## 7. Tests Implied by WF-10

### Unit Tests
*   `test_resolve_lite_produces_minimal_model`: Verify Lite scan correctly identifies build drivers and targets.
*   `test_resolve_deep_produces_conventions_and_violations`: Verify Deep scan infers conventions and lists violations.
*   `test_acceptance_gate_flips_violation_status`: Ensure `maestro repo conventions accept` changes violations from `candidate` to `confirmed`.
*   `test_waiver_prevents_blocking`: Test that a waived issue does not block a policy-enforced workflow.

### Integration Fixtures
*   A repository with clear, distinct conventions (e.g., one using Qt, another using U++) to test inference accuracy.
*   A repository with intentional naming and structural violations to test detection.
*   A repository with ambiguous or mixed conventions to ensure the acceptance gate is triggered.
