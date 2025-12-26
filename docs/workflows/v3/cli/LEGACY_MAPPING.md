# Legacy Mapping and Rename Plan

This mapping treats v3 as normative. Legacy commands map into v3 namespaces; aliases are temporary.

## Mapping table

| Legacy command | v3 command | Decision | Notes |
| --- | --- | --- | --- |
| `maestro build` | `maestro make` | alias -> deprecate | Keep alias for 2 minor releases. |
| `maestro compile` | `maestro make` | alias -> deprecate | Only if legacy usage exists. |
| `maestro understand` | `maestro repo resolve` + `maestro runbook add|discuss` | fold into | Split into resolve + authoring flow. |
| `maestro rules` | `maestro repo rules` | fold into | avoid separate namespace. |
| `maestro resume` | `maestro work resume` | fold into | `ai resume` only for engine session resumes. |
| `maestro session` | `maestro wsession` / `maestro ai` | deprecate | Clarify work session vs AI engine session. |
| `maestro root` | `maestro track|phase|task` | deprecate | Root planning is covered by track/phase/task. |
| `maestro repo config show` | `maestro repo conf show` | rename | Standardize on `conf`. |
| `maestro repo show-config` | `maestro repo conf show` | rename | Standardize on `conf`. |
| `maestro repo resolve --level deep` | `maestro repo resolve deep` | rename | Keyword-first, short verbs. |
| `maestro task complete` | `maestro task set status <id> done` | rename | Status update is a set action. |
| `maestro issues link-solution` | `maestro issues link solution` | rename | Unify under `issues link`. |
| `maestro workflow accept` | `maestro workflow validate` + `maestro runbook add` (or `plan` entrypoint) | deprecate | Acceptance triggers should be explicit. |
| `maestro discuss --context` | `maestro discuss` (router) + `maestro <namespace> discuss` | fold into | Context dispatch becomes explicit. |

## Alias policy

- Aliases are allowed for a fixed window (2 minor releases) with warnings.
- Warnings should include the new command and the removal version.
- v3 prefers a soft transition, not a hard break.

## Warning format

- Example: `WARN: 'build' is deprecated; use 'maestro make'. Removal in v3.2.`
