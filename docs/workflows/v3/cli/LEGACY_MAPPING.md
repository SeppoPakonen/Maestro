# Legacy Mapping and Rename Plan

This mapping treats v3 as normative. Legacy commands map into v3 namespaces; aliases are temporary.

## Mapping table

| Legacy command | Canonical verb | v3 command | Legacy aliases | Deprecation behavior | Notes |
| --- | --- | --- | --- | --- | --- |
| `maestro build` | `make` | `maestro make` | `maestro build` | warn for 2 minor releases, then remove | Keep alias for 2 minor releases. |
| `maestro compile` | `make` | `maestro make` | `maestro compile` | warn for 2 minor releases, then remove | Only if legacy usage exists. |
| `maestro understand` | `resolve` | `maestro repo resolve` + `maestro runbook add|discuss` | `maestro understand` | warn for 1 minor release, then remove | Split into resolve + authoring flow. |
| `maestro rules` | `rules` | `maestro repo rules` | `maestro rules` | warn for 2 minor releases, then remove | Avoid separate namespace. |
| `maestro resume` | `resume` | `maestro work resume` | `maestro resume` | warn for 2 minor releases, then remove | `ai resume` only for engine session resumes. |
| `maestro session` | `wsession` | `maestro wsession` / `maestro ai` | `maestro session` | warn for 2 minor releases, then remove | Clarify work session vs AI engine session. |
| `maestro root` | `plan` | `maestro track|phase|task` | `maestro root` | warn for 2 minor releases, then remove | Root planning is covered by track/phase/task. |
| `maestro repo config show` | `show` | `maestro repo conf show` | `maestro repo config show` | warn for 2 minor releases, then remove | Standardize on `conf`. |
| `maestro repo show-config` | `show` | `maestro repo conf show` | `maestro repo show-config` | warn for 2 minor releases, then remove | Standardize on `conf`. |
| `maestro repo resolve --level deep` | `resolve` | `maestro repo resolve deep` | `maestro repo resolve --level deep` | warn for 1 minor release, then remove | Keyword-first, short verbs. |
| `maestro task complete` | `set` | `maestro task set status <id> done` | `maestro task complete` | warn for 2 minor releases, then remove | Status update is a set action. |
| `maestro issues link-solution` | `link` | `maestro issues link solution` | `maestro issues link-solution` | warn for 2 minor releases, then remove | Unify under `issues link`. |
| `maestro workflow accept` | `validate` | `maestro workflow validate` + `maestro runbook add` (or `plan` entrypoint) | `maestro workflow accept` | warn for 2 minor releases, then remove | Acceptance triggers should be explicit. |
| `maestro discuss --context` | `discuss` | `maestro discuss` (router) + `maestro <namespace> discuss` | `maestro discuss --context` | warn for 2 minor releases, then remove | Context dispatch becomes explicit. |

## Alias policy

- Aliases are allowed for a fixed window (2 minor releases) with warnings.
- Warnings should include the new command and the removal version.
- v3 prefers a soft transition, not a hard break.

## Warning format

- Example: `WARN: 'build' is deprecated; use 'maestro make'. Removal in v3.2.`
