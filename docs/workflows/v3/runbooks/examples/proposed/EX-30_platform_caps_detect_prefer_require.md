# EX-30: Platform Caps Detect + Prefer/Require (Capability-Driven Build)

**Scope**: Detect platform capabilities and use prefer vs require gating
**Outcome**: Optional features enable opportunistically; strict gating creates issues

---

## Preconditions

- Repo truth is JSON under `./docs/maestro/**`
- Repo initialized
- Optional toolchain selection may be active

---

## Runbook Steps

| Step | Command | Intent | Expected | Gates | Stores |
|------|---------|--------|----------|-------|--------|
| 1 | `maestro init` | Initialize repo truth | Repo truth created | `REPO_TRUTH_FORMAT_IS_JSON` | `REPO_TRUTH_DOCS_MAESTRO` |
| 2 | `maestro platform caps detect` | Detect environment capabilities | Detected caps cached in hub | `CAP_DETECT` | `HOME_HUB_REPO` |
| 3 | `maestro platform caps prefer vulkan --scope project` | Enable optional Vulkan if present | Policy stored; missing is OK | `REPO_TRUTH_FORMAT_IS_JSON` | `REPO_TRUTH_DOCS_MAESTRO` |
| 4 | `maestro make` | Build with opportunistic caps | Build uses Vulkan only if present | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO` |
| 5 | `maestro platform caps require vulkan --scope project` | Switch to strict gating | Policy stored; missing will gate | `REPO_TRUTH_FORMAT_IS_JSON` | `REPO_TRUTH_DOCS_MAESTRO` |
| 6 | `maestro make` | Build with strict requirement | Missing Vulkan creates issue/task | `CAP_REQUIRE` | `REPO_TRUTH_DOCS_MAESTRO` |

---

## AI Perspective (Heuristic)

- Prefer caps for adaptive builds; only require when the feature is mandatory
- Re-run detect when toolchain selection changes
- Use policy in repo truth so collaborators share the same intent

---

## Outcomes

### Outcome A: Prefer path succeeds

- Build completes even if Vulkan is absent
- Optional flags are only enabled when detection reports present

### Outcome B: Require path blocks

- Missing Vulkan triggers a gate and a new issue/task
- User can either install Vulkan or unrequire the cap

---

## CLI Gaps / TODOs

- `TODO_CMD: maestro platform caps detect`
- `TODO_CMD: maestro platform caps prefer vulkan --scope project`
- `TODO_CMD: maestro platform caps require vulkan --scope project`
- `TODO_CMD: maestro make --cap-report` (optional visibility for caps usage)

---

## Trace (YAML)

```yaml
trace:
  example: EX-30
  steps:
    - step: detect_caps
      command: "maestro platform caps detect"
      gates: [CAP_DETECT]
      stores: [HOME_HUB_REPO]
    - step: prefer_vulkan
      command: "maestro platform caps prefer vulkan --scope project"
      gates: [REPO_TRUTH_FORMAT_IS_JSON]
      stores: [REPO_TRUTH_DOCS_MAESTRO]
    - step: build_opportunistic
      command: "maestro make"
      gates: [REPOCONF_GATE]
      stores: [REPO_TRUTH_DOCS_MAESTRO]
    - step: require_vulkan
      command: "maestro platform caps require vulkan --scope project"
      gates: [REPO_TRUTH_FORMAT_IS_JSON]
      stores: [REPO_TRUTH_DOCS_MAESTRO]
    - step: build_strict
      command: "maestro make"
      gates: [CAP_REQUIRE]
      stores: [REPO_TRUTH_DOCS_MAESTRO]
  stores_considered:
    - REPO_TRUTH_DOCS_MAESTRO
    - HOME_HUB_REPO
cli_gaps:
  - "maestro platform caps detect"
  - "maestro platform caps prefer vulkan --scope project"
  - "maestro platform caps require vulkan --scope project"
  - "maestro make --cap-report"
```
