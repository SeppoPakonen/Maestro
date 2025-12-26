# Command Taxonomy (v3 audit)

This taxonomy is derived from v2 runbook scripts. It reflects what the
examples actually call (and what they imply via TODO_CMD).
Command counts and example frequency are tracked in
`docs/workflows/v3/reports/command_frequency.csv` and
`docs/workflows/v3/reports/allowed_commands.normalized.txt`.

## Bootstrap (init/runbook/workflow)

Commands observed:
- `maestro init`, `maestro init --greenfield`, `maestro init --read-only`
- `maestro runbook add`, `maestro runbook step-add`, `maestro runbook export`
- `maestro workflow init`, `maestro workflow node add`, `maestro workflow edge add`
- `maestro workflow validate`, `maestro workflow export`, `maestro workflow render`

Core verbs present:
- init, add, export, validate, render

Holes:
- list/show/edit/rm for runbook/workflow
- workflow show/list (graph summary)
- workflow edge edit/rm

## Plan (track/phase/task/root)

Commands observed:
- `maestro track discuss`, `maestro phase add`, `maestro phase discuss`
- `maestro task add`, `maestro task complete`, `maestro task discuss`
- `maestro work task`

Core verbs present:
- add, discuss, complete

Holes:
- list/show/edit/rm for track/phase/task
- explicit task ordering and dependency ops
- task status transitions beyond complete

## Repo / Build / TU / Convert

Commands observed:
- `maestro repo resolve`, `maestro repo conf show`, `maestro repo conf select-default-target`
- `maestro repo show packages`, `maestro repo show entry-points`
- `maestro repo hub find package`
- `maestro build`, `maestro make --with-hub-deps`
- `maestro tu build`, `maestro tu query symbol`, `maestro tu refactor rename`, `maestro tu autocomplete`
- `maestro convert new`, `maestro convert plan`, `maestro convert run`

Core verbs present:
- resolve, conf, show, build, query, refactor, plan, run

Holes:
- repo conf list/validate
- build target selection and build status
- tu list/describe (targets, symbols)
- convert list/describe/update

## Governance (rules/issues/solutions)

Commands observed:
- `maestro rules list`, `maestro rules check`, `maestro rules apply`
- `maestro issues list`, `maestro issues add`, `maestro issues ignore`, `maestro issues accept`
- `maestro solutions match`

Core verbs present:
- list, check, apply, add, ignore, accept, match

Holes:
- issues update/close/reopen
- solution list/show/approve
- rules show/details

## AI / Discuss / Work / Wsession / Session

Commands observed:
- `maestro discuss`, `maestro discuss --engine`, `maestro discuss --resume`
- `maestro ai <engine>`
- `maestro work task`, `maestro work spawn`, `maestro work resume`, `maestro work close`
- `maestro wsession breadcrumb`, `maestro wsession show`
- `maestro session log`

Core verbs present:
- discuss, resume, spawn, breadcrumb, show, log

Holes:
- explicit session list/status
- work list/inspect
- wsession open/close and cookie renewal

## Observability / Ops / Settings

Commands observed:
- `maestro ops commit suggest`, `maestro ops commit create`
- `maestro settings set ai_stacking_mode managed`

Core verbs present:
- suggest, create, set

Holes:
- ops run/doctor
- settings show/list
- log retrieval beyond session log

## Coherence Check

Does this CLI feel like one product or six glued scripts?
- The verb families are consistent inside domains (repo/tu/convert), but
  the planning and session/discuss domains drift in syntax.
- A single, consistent verb set (list/show/add/edit/rm/run/discuss/export/render)
  is only partially present, which makes the CLI feel stitched together.
