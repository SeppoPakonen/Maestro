# Maestro Workflow Scenario Index

This index provides quick access to all documented workflow scenarios. Each scenario represents a complete operational workflow showing how users and Maestro interact over time.

---

## Scenario Table

| ID | Title | Tags | Entry Conditions | Exit Conditions | Artifacts | Links |
|----|-------|------|------------------|-----------------|-----------|-------|
| **WF-01** | Existing Repo Bootstrap (Single Main, Compiled) | `bootstrap`, `retrofit`, `compile`, `issues`, `tasks` | • Existing git repo<br>• Single main branch<br>• Compiled language<br>• No Maestro yet | • Maestro initialized<br>• Past work reconstructed<br>• Clean build OR<br>• Issues/tasks created | • `docs/` structure<br>• Issues from build errors<br>• Tasks with dependencies<br>• Initial plan | [Markdown](scenario_01_existing_repo_single_main.md)<br>[PlantUML](scenario_01_existing_repo_single_main.puml) |
| **WF-02** | New Project from Empty Directory (Manual Planning) | `bootstrap`, `greenfield`, `manual-planning`, `work-loop`, `track-phase-task` | • Empty or new directory<br>• Clear plan/requirements<br>• Manual planning preferred<br>• No git repo yet<br>• No Maestro yet | • Maestro initialized<br>• Tracks, phases, tasks created<br>• Work loop operational<br>• Initial work complete/in progress | • `.git/` repository<br>• `docs/maestro/tracks/*.json`<br>• `docs/maestro/phases/*.json`<br>• `docs/maestro/tasks/*.json`<br>• Source files from work | [Markdown](scenario_02_new_project_manual_plan.md)<br>[PlantUML](scenario_02_new_project_manual_plan.puml) |

---

## Scenario Status Legend

- **Published**: Complete, tested, ready for use
- **Draft**: In progress, subject to change
- **Proposed**: Planned but not yet started
- **Deprecated**: Superseded by newer scenario

Current status:
- **WF-01**: Published (first release)
- **WF-02**: Published

---

## Planned Scenarios (Roadmap)

The following scenarios are planned but not yet documented:

### Repository Types
- **WF-02**: Existing Repo with Feature Branches
  - Tags: `bootstrap`, `branches`, `merge-conflicts`
  - Handles multi-branch workflows, stale branches, merge conflicts

- **WF-03**: New Greenfield Repo
  - Tags: `bootstrap`, `new-project`, `scaffolding`
  - Starting from scratch with Maestro from day one

- **WF-06**: Multi-Language Monorepo
  - Tags: `bootstrap`, `monorepo`, `multi-toolchain`
  - Polyglot projects with multiple build systems

### Error Handling Workflows
- **WF-04**: Runtime Error Workflow
  - Tags: `runtime`, `debugging`, `log-analysis`
  - App runs but produces errors at runtime; log scanning and issue generation

- **WF-07**: Warning Policy Workflow
  - Tags: `warnings`, `policy`, `thresholds`
  - Handling compiler/linter warnings with configurable thresholds

- **WF-08**: Test Failure Workflow
  - Tags: `testing`, `ci-cd`, `regression`
  - Test suite fails; analyzing failures, creating targeted fix tasks

### Enhancement Workflows
- **WF-05**: Feature Request Workflow
  - Tags: `enhancement`, `planning`, `ai-discuss`
  - User requests new feature; AI discusses, creates plan, generates tasks

- **WF-09**: Refactoring Workflow
  - Tags: `refactor`, `tech-debt`, `safety`
  - Planned refactoring with test coverage validation

### Advanced Scenarios
- **WF-10**: Dependency Update Workflow
  - Tags: `dependencies`, `security`, `compatibility`
  - Updating external dependencies; handling breaking changes

- **WF-11**: Performance Optimization Workflow
  - Tags: `performance`, `profiling`, `benchmarks`
  - Profile-guided optimization with before/after metrics

- **WF-12**: Security Audit Workflow
  - Tags: `security`, `audit`, `vulnerabilities`
  - Security scanning and vulnerability remediation

---

## Scenario Trigger Mapping

This table shows which scenarios are triggered by which conditions:

| Trigger Condition | Applicable Scenarios |
|-------------------|---------------------|
| No Maestro initialized | WF-01, WF-02, WF-03, WF-06 |
| Build fails | WF-01, WF-02, WF-06 |
| Runtime error detected | WF-04 |
| Tests fail | WF-08 |
| New feature requested | WF-05 |
| Warnings exceed threshold | WF-07 |
| Dependency alert | WF-10 |
| Performance regression | WF-11 |
| Security scan alert | WF-12 |

---

## Cross-Scenario Flow Examples

Scenarios can chain together in real workflows:

### Example 1: Fresh Bootstrap → Feature Work
1. **WF-01**: Existing Repo Bootstrap
   - User runs `maestro init` on existing codebase
   - Build errors found, issues/tasks created
   - Exit: Clean build achieved
2. **WF-05**: Feature Request Workflow
   - User requests new feature
   - AI discusses approach, creates plan
   - Tasks generated with dependencies

### Example 2: Bootstrap → Ongoing Maintenance
1. **WF-01**: Existing Repo Bootstrap
2. **WF-08**: Test Failure Workflow (tests start failing)
3. **WF-10**: Dependency Update Workflow (update causes new issues)
4. **WF-05**: Feature Request Workflow (add related feature)

### Example 3: Runtime Debugging → Performance Optimization
1. **WF-04**: Runtime Error Workflow
   - Logs show errors and performance issues
2. **WF-11**: Performance Optimization Workflow
   - Profile and optimize hotspots
3. **WF-08**: Test Failure Workflow
   - Regression tests catch optimization bug

---

## Quick Reference: Metadata Fields

All scenario metadata blocks include:

- **id**: Scenario identifier (WF-##)
- **title**: Human-readable short title
- **tags**: Categorization tags
- **entry_conditions**: Prerequisites to start this scenario
- **exit_conditions**: Success criteria for completion
- **artifacts_created**: Files/data produced by this scenario
- **failure_semantics**: Hard stops vs recoverable failures
- **follow_on_scenarios**: IDs of scenarios that may logically follow

See [README.md](README.md) for full metadata schema documentation.

---

## Command Workflows

In addition to scenario workflows, this directory contains **command-specific workflow documentation** that describes the internal implementation of individual Maestro commands.

### Command Workflow Table

| Command | Documentation | Diagram | Purpose | Status |
|---------|---------------|---------|---------|--------|
| `maestro work` | [command_work.md](command_work.md) | [command_work.puml](command_work.puml) | Work execution interface - select and execute work items (tracks, phases, issues, tasks) | Published |

### Difference from Scenarios

- **Scenarios** document complete user journeys (e.g., "bootstrap existing repo")
- **Command workflows** document the internal logic of a single command
- Command workflows are referenced BY scenarios as implementation details
- See [README.md#command-workflows](README.md#command-workflows) for more information

---

## Usage Notes

### For Users
- Find the scenario that matches your current situation using the "Scenario Trigger Mapping" table
- Follow the linked Markdown file as a step-by-step playbook
- Use the PlantUML diagram for a visual overview

### For Developers
- Use scenarios to understand command contracts and requirements
- Extract test cases from the "Tests implied by this scenario" sections
- Create fixture repos based on scenario entry conditions

### For Documentation Writers
- Follow the conventions in [README.md](README.md)
- Ensure new scenarios are merge-friendly (callable procedures, labeled entry/exit points)
- Update this index when adding new scenarios

---

## Diagram Assembly

All scenario PlantUML files are designed to be assembled into a single massive conditional workflow diagram:

```plantuml
!include _shared.puml
!include scenario_01_existing_repo_single_main.puml
!include scenario_02_feature_branches.puml
... etc ...

@startuml Master_Maestro_Workflow
(*) --> [User starts] Analyze_Context

if "Maestro initialized?" then
  if "Build failing?" then
    --> WF_01()
  else
    --> WF_05()
  endif
else
  if "Greenfield?" then
    --> WF_03()
  else
    --> WF_01()
  endif
endif

@enduml
```

See [README.md#diagram-strategy](README.md#diagram-strategy) for details.

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2025-12-25 | Initial creation with WF-01 | Claude Sonnet 4.5 |
| 2025-12-25 | Actor model refactor (Operator model), add WF-02, add command workflows | Claude Sonnet 4.5 |

---

## Related Documentation

- [README.md](README.md) - Workflow documentation conventions and strategy
- [_shared.puml](_shared.puml) - Shared PlantUML macros and styles
- [../CLAUDE.md](../CLAUDE.md) - Agent instructions and policy requirements
- Active tasks tracked in JSON storage
- Completed tasks tracked in JSON storage
