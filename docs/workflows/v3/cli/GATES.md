# v3 Gates Registry (Canonical)

Gate names are stable identifiers used across runbooks and CLI validation. If a new gate is needed, add it here first.

| Gate | Meaning |
| --- | --- |
| `GATE_TOOLCHAIN_SELECTED` | A toolchain profile is selected for the current scope (session/project/host). |
| `GATE_CAPS_DETECTED` | Capability detection data exists for the current host/toolchain. |
| `GATE_REPOCONF_PRESENT` | RepoConf exists and includes a selected target. |
| `GATE_REQUIRE_CAPS_SATISFIED` | All required caps are present (no missing required caps). |
| `GATE_BUILD_OK` | Build passes successfully. |
| `GATE_TU_READY` | TU prerequisites are met (repoconf + toolchain + build context). |
