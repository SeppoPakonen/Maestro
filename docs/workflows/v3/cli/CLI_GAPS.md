# CLI Gap Index (Runbook-Driven)

This index normalizes `TODO_CMD` markers from v2 proposed runbooks into concrete capabilities, then maps each to v3.

## Gaps table

| Gap ID | Capability | Proposed v3 command | Evidence | Priority | Type | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| GAP-0001 | Read-only repo resolve for fingerprinting | `maestro repo resolve lite --readonly` | EX-03, EX-18 | P1 | needs_setting | Flag semantics must prevent writes to `./docs/maestro/**`. |
| GAP-0002 | Show detected packages | `maestro repo show packages` | EX-03 | P2 | missing_command | Read-only report of detected deps. |
| GAP-0003 | Show entry points / targets | `maestro repo show entrypoints` | EX-03 | P2 | missing_command | Normalize spelling to `entrypoints`. |
| GAP-0004 | Show repo conf (targets, compiler) | `maestro repo conf show` | EX-01 | P1 | naming_conflict | Avoid `repo conf --show` flag form. |
| GAP-0005 | Canonical build verb | `maestro make` | EX-01, EX-13 | P0 | naming_conflict | Keep `build` as alias; make is canonical. |
| GAP-0006 | Match solutions from build logs | `maestro solutions match --from-build-log <path>` | EX-01 | P1 | missing_command | Decide path vs auto-detect last build. |
| GAP-0007 | Create issue from solution | `maestro issues add --from-solution <id>` | EX-01 | P1 | missing_command | Needs consistent solution-id linkage. |
| GAP-0008 | Create task from issue with action | `maestro task add --issue <id> --action <action>` | EX-01 | P1 | missing_command | Action vocabulary must be defined. |
| GAP-0009 | Start work from task | `maestro work task <task-id>` | EX-01, EX-07 | P0 | inconsistent_verb | Normalize under `work start --task <id>` or `work task <id>`. |
| GAP-0010 | Discuss router transfer | `maestro discuss --transfer <context>` | EX-21, EX-05 | P1 | missing_command | Needs clear routing and session transfer rules. |
| GAP-0011 | Discuss resume/context selection | `maestro discuss --resume <id>` / `maestro discuss --context task <id>` | EX-05 | P1 | missing_command | Align with `work resume` and `ai resume`. |
| GAP-0012 | Workflow graph init and node add | `maestro workflow init <name>` / `workflow node add <id> --layer <layer> --label <text>` | EX-02, EX-11, EX-12 | P0 | missing_command | Must write `./docs/maestro/workflows/*.json`. |
| GAP-0013 | Workflow export/render | `maestro workflow export --format puml <id>` / `workflow render --format svg <id>` | EX-02, EX-11, EX-27 | P1 | missing_command | Export then render via PlantUML. |
| GAP-0014 | Workflow validate | `maestro workflow validate <id>` | EX-11, EX-12 | P1 | missing_command | Gate for graph invariants. |
| GAP-0015 | Runbook discuss and create | `maestro runbook discuss` / `maestro runbook add <name>` | EX-27 | P1 | missing_command | `add` is preferred over `create`. |
| GAP-0016 | Issues discuss/ignore/link | `maestro issues discuss` / `issues ignore <id> --reason <text>` / `issues link solution <issue> <solution>` | EX-26 | P1 | missing_command | Consolidate under `issues link`. |
| GAP-0017 | Task completion status | `maestro task set status <id> done` | EX-12 | P1 | inconsistent_verb | Prefer `set status` over `complete`. |
| GAP-0018 | Work spawn/resume/pause/close | `maestro work spawn --from-task <id>` / `work resume <wsession-id>` / `work pause <id>` / `work stop <id>` | EX-19, EX-20 | P0 | missing_command | Close vs pause semantics need to be explicit. |
| GAP-0019 | Wsession breadcrumbs | `maestro wsession breadcrumb add --cookie <cookie> --message <text>` / `wsession breadcrumb list --cookie <cookie>` | EX-07, EX-19 | P0 | inconsistent_verb | Standardize on `breadcrumb add|list`. |
| GAP-0020 | Repo hub queries and list | `maestro repo hub find package <name>` / `repo hub list` | EX-18 | P1 | missing_command | Hub store should be `HOME_HUB_REPO`. |
| GAP-0021 | Make with hub deps | `maestro make --with-hub-deps` | EX-18 | P2 | missing_command | Alternative: `repo conf set use-hub-deps true`. |
| GAP-0022 | TU build with hub resolve | `maestro tu build --target <t> --resolve-from-hub` | EX-18 | P2 | missing_command | Clarify TU store inputs. |
| GAP-0023 | Convert pipeline creation | `maestro convert add <name>` | EX-15, EX-17 | P1 | inconsistent_verb | Prefer `add` over `new`. |
| GAP-0024 | Repo discuss | `maestro repo discuss` | EX-21, EX-25 | P1 | missing_command | Discuss endpoints per namespace. |
| GAP-0025 | Settings for stacking mode | `maestro settings set ai_stacking_mode managed` | EX-19 | P2 | needs_setting | Standardize with `ai.stacking_mode`. |
| GAP-0026 | Ops commit helper | `maestro ops commit suggest|create --task <id>` | EX-20 | P2 | missing_command | Needs guard integration (dirty tree). |
| GAP-0027 | Ops git guard status | `maestro ops git status-guard` | EX-20 | P2 | missing_command | Optional command under ops/doctor. |

## Notes

- Evidence references are to v2 runbook examples in `docs/workflows/v2/runbooks/examples/proposed/`.
- Several gaps are naming conflicts (`build` vs `make`, `complete` vs `set status`). These are treated as normalization tasks rather than new features.
