# New Example Candidates (EX-32..EX-39)

## Reserved (Already Claimed in v3)

- EX-29: Select toolchain profiles (v3 select toolchain)
- EX-30: Platform capabilities (detect + prefer/require)
- EX-31: Integration chain (toolchain + caps → repoconf → make/tu)

These IDs are reserved to avoid collisions; do not reuse.

Proposed examples to close gaps revealed by the v2 audit.

1) EX-32: Settings evolution across project lifecycle
   Domains: settings, repo, governance
   Why missing: settings are only set once, no migration/rollback story.
   Stress-test primitives: `settings show`, `settings set`, `settings migrate`.

2) EX-33: Ops automation (doctor + run)
   Domains: ops, observability, build
   Why missing: ops appear only for commits; no operational checks.
   Stress-test primitives: `ops doctor`, `ops run`, `ops log`.

3) EX-34: Log-driven issue creation pipeline
   Domains: issues, build, repo
   Why missing: no explicit bridge from logs to issues/tasks.
   Stress-test primitives: `issues add --from-log`, `issues link-task`.

4) EX-35: Resume/replay for discuss and work sessions
   Domains: discuss, work, wsession, session
   Why missing: resume is present, replay not specified.
   Stress-test primitives: `discuss replay`, `work replay`, `session list`.

5) EX-36: Convert plan approval workflow with ledger
   Domains: convert, governance, ledger
   Why missing: convert plan is run but never approved.
   Stress-test primitives: `convert plan approve`, `convert plan reject`.

6) EX-37: Hub linking beyond U++ dependency lookup
   Domains: repo hub, repo resolve
   Why missing: hub linking only shows Core example.
   Stress-test primitives: `repo hub find package`, `repo hub link package`.

7) EX-38: Cleanup/archive lifecycle for runbooks and workflows
   Domains: runbook, workflow, governance
   Why missing: no lifecycle closure for stale docs.
   Stress-test primitives: `runbook archive`, `workflow archive`, `runbook list --archived`.

8) EX-39: Branch guard + dirty tree guard with commit template
   Domains: ops, work, repo
   Why missing: branch guard is shown, template generation is not.
   Stress-test primitives: `ops commit template`, `repo guard dirty`, `work close`.
