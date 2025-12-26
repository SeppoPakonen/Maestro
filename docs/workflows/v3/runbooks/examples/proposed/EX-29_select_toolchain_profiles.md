# EX-29: Select Toolchain Profiles (Toolchain-Local Libraries)

**Scope**: Select toolchain profiles that bundle their own SDK/sysroot
**Outcome**: Show project-scoped selection, export of env snippet, and build execution

---

## Preconditions

- Repo truth is JSON under `./docs/maestro/**`
- Repo initialized
- Toolchain profiles exist in hub or are detectable

## Gates / IDs / Stores

- Gates: `REPO_TRUTH_FORMAT_IS_JSON`, `TOOLCHAIN_PROFILE_EXISTS`, `REPOCONF_GATE`
- IDs/cookies/resume tokens: none
- Stores: `REPO_TRUTH_DOCS_MAESTRO`, `HOME_HUB_REPO`

---

## Runbook Steps

| Step | Command | Intent | Expected | Gates | Stores |
|------|---------|--------|----------|-------|--------|
| 1 | `maestro select toolchain set system --scope project` | Use system toolchain for baseline | Toolchain profile recorded in repo truth | `REPO_TRUTH_FORMAT_IS_JSON` | `REPO_TRUTH_DOCS_MAESTRO` |
| 2 | `maestro select toolchain show --scope project` | Confirm selection | Active toolchain profile shown | `TOOLCHAIN_PROFILE_EXISTS` | `REPO_TRUTH_DOCS_MAESTRO` |
| 3 | `maestro select toolchain export --format env --out ./docs/maestro/toolchain.env` | Generate env snippet | Exported env contains include/lib paths | `TOOLCHAIN_PROFILE_EXISTS` | `REPO_TRUTH_DOCS_MAESTRO` |
| 4 | `maestro make` | Build with baseline toolchain | Build succeeds | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO` |
| 5 | `maestro select toolchain set android_ndk_r25 --scope project` | Switch to SDK toolchain | Project selection updated | `TOOLCHAIN_PROFILE_EXISTS` | `REPO_TRUTH_DOCS_MAESTRO` |
| 6 | `maestro select toolchain export --format env --out ./docs/maestro/toolchain-android.env` | Verify SDK paths | Export includes NDK sysroot paths | `TOOLCHAIN_PROFILE_EXISTS` | `REPO_TRUTH_DOCS_MAESTRO` |
| 7 | `maestro make` | Build with SDK toolchain | Build uses toolchain-local libs | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO` |

---

## AI Perspective (Heuristic)

- Prefer project-scoped toolchain selection for reproducible builds
- Use export output to validate include/lib paths before running make
- If profile missing, prompt detect or hub scan

---

## Outcomes

### Outcome A: Success (Toolchain profile present)

- Build completes using toolchain-local sysroot/SDK
- Repo truth records the selected profile name

### Outcome B: Missing Profile

- Selection fails with a suggested next step: `maestro select toolchain detect`
- User can install or create the profile in the hub

---

## CLI Gaps / TODOs

- `TODO_CMD: maestro select toolchain detect`
- `TODO_CMD: maestro select toolchain export --format env --out <path>`

---

## Trace (YAML)

```yaml
trace:
  example: EX-29
  steps:
    - step: select_system_toolchain
      command: "maestro select toolchain set system --scope project"
      gates: [REPO_TRUTH_FORMAT_IS_JSON]
      stores: [REPO_TRUTH_DOCS_MAESTRO]
    - step: export_env
      command: "maestro select toolchain export --format env --out ./docs/maestro/toolchain.env"
      gates: [TOOLCHAIN_PROFILE_EXISTS]
      stores: [REPO_TRUTH_DOCS_MAESTRO]
    - step: build_with_toolchain
      command: "maestro make"
      gates: [REPOCONF_GATE]
      stores: [REPO_TRUTH_DOCS_MAESTRO]
  stores_considered:
    - REPO_TRUTH_DOCS_MAESTRO
    - HOME_HUB_REPO
cli_gaps:
  - "maestro select toolchain detect"
  - "maestro select toolchain export --format env --out <path>"
```
