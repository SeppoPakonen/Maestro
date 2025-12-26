# Example Index (v3)

## v3 Foundation Examples

- EX-29: Select toolchain profiles
  - Status: proposed (docs)
  - Domains: select, toolchain, repo conf, make
  - Files: docs/workflows/v3/runbooks/examples/proposed/EX-29_select_toolchain_profiles.md, docs/workflows/v3/runbooks/examples/proposed/EX-29_select_toolchain_profiles.sh
- EX-30: Platform capabilities (detect + prefer/require)
  - Status: proposed (docs)
  - Domains: platform caps, policy, make
  - Files: docs/workflows/v3/runbooks/examples/proposed/EX-30_platform_caps_detect_prefer_require.md, docs/workflows/v3/runbooks/examples/proposed/EX-30_platform_caps_detect_prefer_require.sh
- EX-31: Integration chain (toolchain + caps -> repoconf -> make/tu)
  - Status: proposed (docs)
  - Domains: select toolchain, platform caps, repo conf, make, tu
  - Files: docs/workflows/v3/runbooks/examples/proposed/EX-31_toolchain_plus_caps_into_repoconf_make_tu.md, docs/workflows/v3/runbooks/examples/proposed/EX-31_toolchain_plus_caps_into_repoconf_make_tu.sh

## v3 Candidate Backlog

- EX-32: Settings evolution across project lifecycle
  - Status: candidate
  - Domains: settings, policy
- EX-33: Ops automation (doctor + run)
  - Status: candidate
  - Domains: ops, diagnostics, automation
- EX-34: Log-driven issue creation pipeline
  - Status: candidate
  - Domains: logs, issues, tasks
- EX-35: Resume/replay for discuss and work sessions
  - Status: candidate
  - Domains: discuss, work, resume
- EX-36: Convert plan approval workflow with ledger
  - Status: candidate
  - Domains: convert, governance, ledger
- EX-37: Hub linking beyond U++ dependency lookup
  - Status: candidate
  - Domains: hub, repo, metadata
- EX-38: Cleanup/archive lifecycle for runbooks and workflows
  - Status: candidate
  - Domains: runbooks, workflows, lifecycle
- EX-39: Branch guard + dirty tree guard with commit template
  - Status: candidate
  - Domains: git guard, commit, governance

## v2 Snapshot Pointer

- v2 input snapshot lives under docs/workflows/v3/runbooks/examples/input_from_v2_proposed/
- Curated task notes live at docs/workflows/v3/reports/task_summaries.md

## Rule of the Road

- Never reuse an EX id once published.
- If an example is replaced, mark it "superseded" and point to the successor.
- Keep this index updated when adding or removing examples.
