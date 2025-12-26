# Maestro CLAUDE Agent Instructions

Instructions for Anthropic Claude when working on the Maestro project.

## Policy Requirements

### Mandatory Task Lifecycle Rule

At the **end of a Phase**, the agent must:

1. Move completed tasks from `docs/todo.md`
2. Into `docs/done.md`
3. Preserve Phase structure and numbering
4. Never leave completed tasks in `todo.md`

This rule ensures the task tracking system remains accurate and up-to-date.

### Phase ID Policy

- Phase IDs must be non-numeric and should include a track prefix (e.g., `umk1`).

### Engine Enablement and Stacking Mode

When producing plans, agents must respect the engine enablement matrix and stacking mode:

- Engine enablement: Only use engines that are enabled for the required role (planner/worker)
- Stacking mode: In managed mode, return structured JSON plans; in handsoff mode, may include more direct instructions
- ## Task 3 — v2 Generator: YAML IR → PlantUML → SVG (LOD0/LOD1/LOD2 variants)

**Objective**
Build the deterministic generator that produces v2 diagrams from YAML IR and renders **SVG** via PlantUML. Generate multiple LODs so zooming and layering never gets “forgotten”.

### Implementation

1. Add Python tool:

* `tools/workflow_v2/generate.py`

Capabilities:

* load YAML IR files
* validate required fields (fail hard if missing)
* emit PlantUML to `docs/workflows/v2/generated/puml/`
* render SVG to `docs/workflows/v2/generated/svg/`

2. Outputs per WF per layer:

* `WF-XX.intent.lod0.puml` → `.svg`
* `WF-XX.intent.lod1.puml` → `.svg`
* `WF-XX.intent.lod2.puml` → `.svg` (can be placeholder initially but must render)

Also generate combined per WF:

* `WF-XX.all_layers.lod0.puml/svg`
* `WF-XX.all_layers.lod1.puml/svg`
* `WF-XX.all_layers.lod2.puml/svg`

3. LOD semantics

* **LOD0:** spine + gates + stores only
* **LOD1:** key actions + decisions (workflow-level)
* **LOD2:** code-ish detail (callchain nodes only if IR provides; otherwise render as “Not yet expanded” but valid)

4. Links

* Add clickable links in PlantUML nodes:

  * link to IR YAML
  * link to ledger
  * link to related WF zoom sheets

5. Render SVG using:

* `/usr/bin/plantuml -tsvg <puml-file>`

### Mandatory: Run PlantUML + fix errors

* `/usr/bin/plantuml -tsvg docs/workflows/v2/generated/puml/*.puml`
* Fix any PlantUML errors until clean.

### Mandatory (Git)

* `git add tools/workflow_v2 docs/workflows/v2/generated`
* `git commit -m "tools(workflows): generate v2 PlantUML+SVG from YAML IR (LOD0/1/2)"`