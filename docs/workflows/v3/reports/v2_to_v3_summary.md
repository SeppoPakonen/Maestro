# v2 → v3 Summary (Runbook Synthesis)

What looks solid:
- The runbook set covers the full lifecycle from repo resolve to work sessions.
- Workflow-first authoring (workflow nodes + export/render) is a strong anchor.
- JSON contract gating is explicit and testable for discuss flows.

What looks fragile:
- CLI surface is inconsistent (workflow node signatures, work resume syntax).
- Build vs make naming is ambiguous and blocks automation.
- Wsession cookie handling and breadcrumb APIs are inconsistent.
- Repo conf gates are implied but not enforced everywhere.

What we must implement:
- A normalized CLI for workflow, work/wsession, and discuss resume/replay.
- Repo conf gate enforcement before build/tu actions.
- OPS-aligned commands for discuss actions (workflow export/render, repo discuss).
- Minimal session logging and replay hooks for auditability.
