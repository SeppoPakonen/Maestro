# P1 Sprint 1 TODO_CMD Mapping

This map captures TODO_CMD markers in the targeted runbooks and the concrete command needed to resolve each one.

## EX-01 (C++ CMake adopt/build/fix)

- `maestro repo conf --show` → `maestro repo conf show` (exists)
- `maestro build` → `maestro make` (exists; `build` is legacy alias)
- `maestro solutions match --from-build-log` → not implemented (needs solutions match subcommand)
- `maestro issues add --from-solution <id>` → not implemented (issues add/create from solution)
- `maestro task add --issue <id> --action <action>` → not implemented (task add supports only name/phase)
- `maestro work task <id>` → `maestro work task <id>` (exists)

## EX-03 (Python Poetry read-only inspect)

- `maestro repo resolve --readonly` → `maestro repo resolve --no-write` (exists; read-only hub cache is still missing)
- `maestro repo show packages` → `maestro repo pkg list` (exists)
- `maestro repo show entry-points` → not implemented (entry point discovery/output)

## EX-07 (work ↔ wsession, cookie/breadcrumb)

- `maestro wsession show <id>` → `maestro wsession show <id>` (exists)
- `maestro work --resume <id>` → not implemented (work resume)
- `maestro wsession breadcrumb <id> --cookie <cookie> --status <msg>` → `maestro wsession breadcrumb add --cookie <cookie> --prompt <msg>` (exists)
- `maestro work task <id> --allow-mutations` → not implemented (mutation mode)

## EX-13 (repo resolve levels + repoconf targets)

- `maestro repo conf show` → `maestro repo conf show` (exists)
- `maestro repo conf select-default-target <id>` → `maestro repo conf select-default target <id>` (exists)
- `maestro build` → `maestro make` (exists; `build` alias)
- `maestro repo resolve --level deep` → `maestro repo refresh all` (exists)

## EX-20 (git guard, commits)

- `maestro ops git status-guard` → not implemented (ops namespace)
- `maestro ops commit suggest --task <id>` → not implemented
- `maestro ops commit create --task <id>` → not implemented
- `maestro work close <id>` → `maestro wsession close <id>` (exists)
- `maestro work pause <id>` → not implemented (pause)

## EX-31 (toolchain + caps + repoconf)

- `maestro select toolchain set <profile> --scope project` → not implemented
- `maestro platform caps detect` → not implemented
- `maestro platform caps prefer vulkan --scope project` → not implemented
- `maestro repo resolve deep` → `maestro repo refresh all` (exists)
- `maestro repo conf select-default target <t>` → `maestro repo conf select-default target <t>` (exists)
- `maestro make` → `maestro make` (exists)
- `maestro tu build` → `maestro tu build` (exists; gated)
- `maestro platform caps require vulkan --scope project` → not implemented
- `maestro issues add --title "Missing cap: vulkan" --evidence <detect>` → not implemented (issues add)
- `maestro select toolchain set <profile-with-vulkan> --scope project` → not implemented
