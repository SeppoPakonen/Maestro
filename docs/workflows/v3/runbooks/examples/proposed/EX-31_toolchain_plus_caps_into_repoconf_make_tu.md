# EX-31: Toolchain + Caps + RepoConf Into Make/TU (Full Chain)

**Scope**: Toolchain selection, caps detection/policy, repoconf target, build + TU
**Outcome**: Opportunistic success with prefer; strict require blocks and raises an issue

---

## Preconditions

- Repo truth is JSON under `./docs/maestro/**`
- Toolchain profiles exist in hub
- Optional: repo already resolved

---

## Runbook Steps

| Step | Command | Intent | Expected | Gates | Stores |
|------|---------|--------|----------|-------|--------|
| 1 | `maestro init` | Initialize repo truth | Repo truth created | `REPO_TRUTH_FORMAT_IS_JSON` | `REPO_TRUTH_DOCS_MAESTRO` |
| 2 | `maestro select toolchain set <profile> --scope project` | Choose toolchain profile | Toolchain reference stored in repo | `GATE_TOOLCHAIN_SELECTED` | `REPO_TRUTH_DOCS_MAESTRO`, `HOME_HUB_REPO` |
| 3 | `maestro platform caps detect` | Detect capabilities under toolchain | Detection cached in hub | `GATE_CAPS_DETECTED` | `HOME_HUB_REPO` |
| 4 | `maestro platform caps prefer vulkan --scope project` | Prefer optional Vulkan | Policy stored; missing OK | `REPO_TRUTH_FORMAT_IS_JSON` | `REPO_TRUTH_DOCS_MAESTRO` |
| 5 | `maestro repo resolve --level deep` | Resolve repo context | Repo resolved to targets | `REPO_TRUTH_FORMAT_IS_JSON` | `REPO_TRUTH_DOCS_MAESTRO`, `HOME_HUB_REPO` |
| 6 | `maestro repo conf select-default target <t>` | Select target configuration | RepoConf present | `GATE_REPOCONF_PRESENT` | `REPO_TRUTH_DOCS_MAESTRO` |
| 7 | `maestro make` | Build with prefer policy | Build succeeds; Vulkan enabled if present | `GATE_BUILD_OK` | `REPO_TRUTH_DOCS_MAESTRO` |
| 8 | `maestro tu build` | Generate TU/AST artifacts | TU build succeeds | `GATE_TU_READY` | `REPO_TRUTH_DOCS_MAESTRO` |
| 9 | `maestro platform caps require vulkan --scope project` | Switch to strict gating | Policy stored; missing blocks | `REPO_TRUTH_FORMAT_IS_JSON` | `REPO_TRUTH_DOCS_MAESTRO` |
| 10 | `maestro make` | Build with required caps | Missing Vulkan gates + issue | `GATE_REQUIRE_CAPS_SATISFIED` | `REPO_TRUTH_DOCS_MAESTRO` |

---

## AI Perspective (Heuristic)

- Prefer caps for adaptable builds; require only when the feature is truly mandatory
- Re-run detect after changing toolchain or host
- Keep repo conf aligned with the chosen toolchain profile to avoid mismatches

---

## Outcomes

### Outcome A: Prefer path succeeds

- Build and TU run without Vulkan if it is absent
- Optional feature flags are applied only when detection says present

### Outcome B: Require path blocks

- Missing Vulkan triggers a gate and creates an issue with detection evidence
- User can select a different toolchain profile and re-run detect

### Outcome C: Toolchain switch fixes caps

- Switching to a toolchain profile with Vulkan in its sysroot satisfies the require gate

---

## CLI Gaps / TODOs

- `TODO_CMD: maestro select toolchain set <profile> --scope project`
- `TODO_CMD: maestro platform caps detect`
- `TODO_CMD: maestro platform caps prefer vulkan --scope project`
- `TODO_CMD: maestro repo resolve --level deep`
- `TODO_CMD: maestro repo conf select-default target <t>`
- `TODO_CMD: maestro make`
- `TODO_CMD: maestro tu build`
- `TODO_CMD: maestro platform caps require vulkan --scope project`
- `TODO_CMD: maestro issues add --title "Missing cap: vulkan" --evidence <detect>`

---

## Trace (YAML)

```yaml
trace:
  example: EX-31
  steps:
    - step: select_toolchain
      command: "maestro select toolchain set <profile> --scope project"
      gates: [GATE_TOOLCHAIN_SELECTED]
      stores: [REPO_TRUTH_DOCS_MAESTRO, HOME_HUB_REPO]
    - step: detect_caps
      command: "maestro platform caps detect"
      gates: [GATE_CAPS_DETECTED]
      stores: [HOME_HUB_REPO]
    - step: prefer_vulkan
      command: "maestro platform caps prefer vulkan --scope project"
      gates: [REPO_TRUTH_FORMAT_IS_JSON]
      stores: [REPO_TRUTH_DOCS_MAESTRO]
    - step: repo_resolve
      command: "maestro repo resolve --level deep"
      gates: [REPO_TRUTH_FORMAT_IS_JSON]
      stores: [REPO_TRUTH_DOCS_MAESTRO, HOME_HUB_REPO]
    - step: repoconf_select
      command: "maestro repo conf select-default target <t>"
      gates: [GATE_REPOCONF_PRESENT]
      stores: [REPO_TRUTH_DOCS_MAESTRO]
    - step: build_prefer
      command: "maestro make"
      gates: [GATE_BUILD_OK]
      stores: [REPO_TRUTH_DOCS_MAESTRO]
    - step: tu_build
      command: "maestro tu build"
      gates: [GATE_TU_READY]
      stores: [REPO_TRUTH_DOCS_MAESTRO]
    - step: require_vulkan
      command: "maestro platform caps require vulkan --scope project"
      gates: [REPO_TRUTH_FORMAT_IS_JSON]
      stores: [REPO_TRUTH_DOCS_MAESTRO]
    - step: build_require
      command: "maestro make"
      gates: [GATE_REQUIRE_CAPS_SATISFIED]
      stores: [REPO_TRUTH_DOCS_MAESTRO]
  stores_considered:
    - REPO_TRUTH_DOCS_MAESTRO
    - HOME_HUB_REPO
cli_gaps:
  - "maestro select toolchain set <profile> --scope project"
  - "maestro platform caps detect"
  - "maestro platform caps prefer vulkan --scope project"
  - "maestro repo resolve --level deep"
  - "maestro repo conf select-default target <t>"
  - "maestro make"
  - "maestro tu build"
  - "maestro platform caps require vulkan --scope project"
  - "maestro issues add --title \"Missing cap: vulkan\" --evidence <detect>"
```
