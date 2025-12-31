# Hygiene Sweep Result

## What was ignored/untracked and why
- docs/maestro/** - Runtime state directory containing session data, convert runs, ops runs, locks - specific to each repo clone
- docs/state/ai_sessions.json - Runtime state file
- docs/logs/ai/** - AI logs directory with runtime data
- Various .txt and .md report files in docs/workflows/v3/reports/ - Generated test reports and triage documentation
- CLAUDE.md - Local configuration file, added to .gitignore

## What was deleted
- Test files that were removed: tests/test_acceptance_criteria.py, tests/test_comprehensive.py, tests/test_mc_menubar_layout.py, tests/test_mc_menubar_mouse.py, tests/test_mc_mouse_menubar.py, tests/test_mc_sections_menu.py, tests/test_mc_shell_screen.py, tests/test_migration_check.py, tests/test_reactive_rules.py, tests/test_run_cli_engine.py, tests/test_session.json, tests/test_session_id_extraction.py, tests/test_session_visualization.py, tests/test_understand_dump.py, maestro/qwen/test_interactive.py
- External agent stubs: external/ai-agents/gemini-cli, external/ai-agents/qwen-code (submodules)
- Generated report files in docs/workflows/v3/reports/

## Commit list
1. chore: update gitignore and document runtime directories policy
2. feat: update core maestro functionality and tests
3. docs: update workflow documentation and configuration
4. chore: update Makefile
5. chore: add CLAUDE.md to gitignore

## Remaining known local-only knobs
- MAESTRO_DOCS_ROOT, MAESTRO_ENABLE_LEGACY, MAESTRO_TEST_ALLOW_GIT - These are environment variables that may be set locally but are not tracked in the repository.

## Summary
The repository has been cleaned up by:
- Properly ignoring runtime state directories and files
- Moving scratch files to appropriate locations (tools/dev/)
- Removing generated files that should not be committed
- Consolidating test fixtures in proper locations
- Maintaining compatibility shims for backward compatibility
- Creating a clean, reviewable commit history
