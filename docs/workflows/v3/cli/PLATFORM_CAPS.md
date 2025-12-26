# v3 Platform Caps (Normative)

Platform capabilities describe what the current environment can provide (optionally via a selected toolchain). They are **not** a repo property and are **distinct** from toolchain selection.

## Command namespace

- `maestro platform caps detect [--toolchain <profile>] [--scope session|project|host]`
- `maestro platform caps list`
- `maestro platform caps show <cap>`
- `maestro platform caps prefer <cap> [--scope project|session]`
- `maestro platform caps require <cap> [--scope project|session]`
- `maestro platform caps unprefer <cap> [--scope project|session]`
- `maestro platform caps unrequire <cap> [--scope project|session]`
- `maestro platform caps export [--format json|env|cmake] [--out <path>]`

Aliases (optional):

- `maestro caps ...` (short alias for `platform caps`)

## Semantics

1. Capabilities are environment-facing and can be derived from:
   - host system installs
   - the currently selected toolchain profile (sysroot/SDK libs)
2. `detect` produces a set of caps with:
   - `present: true/false`
   - optional `version`
   - optional `provider` (system/toolchain/pkg-config/etc.)
   - `confidence` in `0..1`
   Detection is non-authoritative and can be wrong.
3. Prefer vs require:
   - `prefer`: if present, enable features; if absent, silently skip (optionally note).
   - `require`: if absent, hard gate (fail) and create an issue/task (conceptual).
4. Scopes:
   - `session`: ephemeral, used during active work
   - `project`: stored in repo truth to capture intent
   - `host`: cached detection + defaults, stored in `$HOME/.maestro`
5. Toolchain interaction:
   - capabilities view may change when a toolchain is selected
   - `detect --toolchain <profile>` previews caps under that toolchain
   - default detect uses the current selection if any

## Storage locations (spec)

Host hub:

- `$HOME/.maestro/platform/caps/detected.json`
- `$HOME/.maestro/platform/caps/detected.<toolchain>.json` (optional)
- `$HOME/.maestro/platform/caps/index.json` (optional)

Repo truth:

- `./docs/maestro/platform_caps.json` (policy only)
  - `prefer: [...]`
  - `require: [...]`
  - `notes: "..."`

Raw detection data stays in the hub; repo truth stores only policy.
