# v3 Select Toolchain (Normative)

Toolchain selection is a first-class choice layer that is **local to the toolchain** and not a global statement about host libraries.

## Command namespace

- `maestro select toolchain list`
- `maestro select toolchain show`
- `maestro select toolchain set <profile> [--scope session|project|host]`
- `maestro select toolchain unset [--scope session|project|host]`
- `maestro select toolchain detect`
- `maestro select toolchain export [--format env|cmake|json] [--out <path>]`

Aliases:

- `maestro select tc ...`

## Semantics

1. A toolchain profile is a **bundle** that may include:
   - compiler + linker
   - sysroot / SDK paths
   - bundled libs (not necessarily installed system-wide)
   - default flags (CFLAGS/CXXFLAGS/LDFLAGS)
   - target triple(s)
2. Toolchain selection affects:
   - `repo conf` defaults
   - `make`/`build` and `tu` execution environment
3. Toolchain selection is **not** a claim about what the host system globally provides.
4. Scopes:
   - `session`: current work session or invocation
   - `project`: stored in repo truth
   - `host`: stored in hub as a default suggestion
5. Precedence:
   - `session` > `project` > `host`

## Storage locations (spec)

Host hub:

- `$HOME/.maestro/select/toolchain/profiles/<name>.json`
- `$HOME/.maestro/select/toolchain/default.json`

Repo truth:

- `./docs/maestro/repoconf.json` references toolchain by name (string), not by copying full profile

## Relationship to platform capabilities (forward note)

Platform capabilities are modeled separately (Task 2/3). Toolchain selection may change the capability view because the toolchain can bring its own libraries.
