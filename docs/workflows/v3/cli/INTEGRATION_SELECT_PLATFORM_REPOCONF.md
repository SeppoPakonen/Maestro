# v3 Integration: Select Toolchain + Platform Caps + RepoConf (Normative)

This document defines the integration contract between toolchain selection, platform capability detection/policy, and repo configuration for build and TU flows.

## 1) Data flow graph (narrative)

- Toolchain selection establishes the **execution environment** (compiler, sysroot, flags).
- Platform caps detection observes the environment (host + toolchain) and records what is present.
- Cap policy (prefer/require) is **project intent** stored in repo truth.
- RepoConf selects targets and maps:
  - target -> toolchain profile reference
  - target -> cap policy reference (or inline policy)
- Make/TU runs consume:
  - toolchain export artifacts (env/cmake/json)
  - caps export artifacts (env/json)
  - repo conf target definition

## 2) Precedence rules (hard)

- Session scope overrides everything:
  - session toolchain override
  - session cap policy override (rare but allowed)
- Otherwise:
  - project toolchain reference wins over host default
  - project cap policy wins over host detected hints
- Detection results never override policy.

## 3) Gates

- `GATE_TOOLCHAIN_SELECTED`: a toolchain is selected or project default exists.
- `GATE_CAPS_DETECTED`: detection data exists for current toolchain/host.
- `GATE_REPOCONF_PRESENT`: target config exists.
- `GATE_REQUIRE_CAPS_SATISFIED`: all required caps are present.
- `GATE_BUILD_OK`: build passes.
- `GATE_TU_READY`: TU prerequisites met.

## 4) Export artifacts (spec)

### Toolchain export

- `maestro select toolchain export --format env` produces:
  - `MAESTRO_TC_*` env vars (paths, sysroot, compiler, flags)
- `--format cmake` produces a toolchain file.
- `--format json` produces a machine-readable profile.

### Caps export

- `maestro platform caps export --format env` produces:
  - `MAESTRO_CAP_<NAME>=1`
  - optional `MAESTRO_CAP_<NAME>_VERSION=...`
- `--format json` includes provider + confidence.

### RepoConf consumption

`maestro make` and `maestro tu` must:

- load toolchain export
- load caps export
- apply them to the build invocation in a deterministic order

## 5) "Don't complain until required" policy

- `prefer` caps can be missing silently.
- `require` caps missing must:
  - block the run
  - create an issue with evidence from detection
  - optionally suggest `select toolchain` alternatives

## 6) OPS alignment (link only)

- Toolchain ops: `select.toolchain.set`, `select.toolchain.export`
- Caps ops: `platform.caps.detect`, `platform.caps.prefer`, `platform.caps.require`, `platform.caps.export`
- RepoConf ops: `repo.conf.select_target`, `repo.conf.set_toolchain`, `repo.conf.set_caps`

Reference: `docs/workflows/v2/reports/discuss_ops_contract.md`.
