# Planner Templates Regression Checklist

This checklist verifies that the canonical planner prompt templates are working correctly across all three planning contexts.

## Build Target Planning

- [ ] `maestro build plan` works in one-shot mode
- [ ] `maestro build plan` works in interactive mode
- [ ] `/done` command produces valid JSON build target in interactive mode
- [ ] JSON output parses without errors
- [ ] Required fields (`name`, `target_id`, `pipeline`) are present in output
- [ ] At least one `build` step exists in pipeline
- [ ] Prompts are saved to `.maestro/build/inputs/`
- [ ] Outputs are saved to `.maestro/build/outputs/`
- [ ] `--verbose` shows file paths for saved prompts/outputs

## Fix Rulebook Planning

- [ ] `maestro build fix plan` works in interactive mode
- [ ] `/done` command produces valid JSON rulebook
- [ ] JSON output parses without errors
- [ ] Required fields (`name`, `version`, `rules`) are present in output
- [ ] At least one rule exists in rulebook
- [ ] Rules contain match logic and actions
- [ ] Prompts are saved to `~/.config/maestro/fix/inputs/`
- [ ] Outputs are saved to `~/.config/maestro/fix/outputs/`
- [ ] `--verbose` shows file paths for saved prompts/outputs

## Conversion Pipeline Planning

- [ ] `maestro convert plan` works in one-shot mode
- [ ] `maestro convert plan` works in interactive mode
- [ ] `/done` command produces valid JSON pipeline stages
- [ ] JSON output parses without errors
- [ ] Required stages exist (`overview`, `core_builds`, `grow_from_main`, `full_tree_check`)
- [ ] Each stage has defined exit criteria
- [ ] Prompts are saved to `.maestro/convert/inputs/`
- [ ] Outputs are saved to `.maestro/convert/outputs/`
- [ ] `--verbose` shows file paths for saved prompts/outputs

## General Functionality

- [ ] All planner prompts follow the Task 4 contract (GOAL, CONTEXT, REQUIREMENTS, ACCEPTANCE CRITERIA, DELIVERABLES)
- [ ] All finalization prompts include "JSON-only mode" instruction
- [ ] Invalid JSON responses from AI are handled gracefully
- [ ] Quiet mode suppresses streaming but still saves prompts/outputs
- [ ] Print prompts flag shows constructed prompts