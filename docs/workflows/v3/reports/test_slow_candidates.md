# Slow Test Candidates
Generated: 2025-12-30 18:37:57
Source: docs/workflows/v3/reports/test_durations_latest.txt

Top 20 slowest tests:
- tests/test_repo_resolve_ai_upp.py::test_scan_upp_repo_v2_integration (708.29s) - Mitigation: Mock external subprocesses to avoid real exec.
- tests/test_repo_workflow_ai_upp_e2e.py::test_repo_workflow_e2e (97.15s) - Mitigation: Use tmp_path fixtures and avoid copying full repos.
- tests/test_repo_resolve_ai_upp.py::test_cli_init_resolve_e2e (78.67s) - Mitigation: Reduce fixture scope or reuse session-scoped fixtures.
- tests/test_repo_resolve_ai_upp.py::test_cli_json_output_integration (77.68s) - Mitigation: Stub filesystem scans; limit to small fixture dirs.
- tests/test_discuss_golden_replays.py::test_discuss_golden_replays (35.44s) - Mitigation: Cache expensive setup across tests.
- tests/test_plan_cli_fix.py::test_plan_cli_fix (21.49s) - Mitigation: Avoid network calls; use local fixtures.
- tests/test_ai_cli_smoke.py::test_ai_print_cmd_flags (20.52s) - Mitigation: Skip PlantUML rendering; mock or gate behind marker.
- tests/test_playbook_integration.py::test_playbook_integration (18.66s) - Mitigation: Short-circuit large logs; use smaller fixtures.
- tests/test_ai_cli_smoke.py::test_command_building_with_options (15.34s) - Mitigation: Use in-memory data instead of writing to disk.
- tests/test_structure_integration.py::test_command_aliases (14.49s) - Mitigation: Reduce parametrization combinations.
- tests/test_repo_resolve_portable.py::test_repo_workflow_e2e_portable (14.45s) - Mitigation: Mock external subprocesses to avoid real exec.
- tests/test_structure_integration.py::test_regression_scenario_1 (13.41s) - Mitigation: Use tmp_path fixtures and avoid copying full repos.
- tests/test_repo_resolve_portable.py::test_scan_portable_repo_v2 (12.83s) - Mitigation: Reduce fixture scope or reuse session-scoped fixtures.
- tests/test_repo_resolve_portable.py::test_cli_init_resolve_e2e_portable (11.10s) - Mitigation: Stub filesystem scans; limit to small fixture dirs.
- tests/test_structure_integration.py::test_regression_scenario_2 (10.40s) - Mitigation: Cache expensive setup across tests.
- tests/test_repo_resolve_portable.py::test_cli_json_output_portable (10.63s) - Mitigation: Avoid network calls; use local fixtures.
- tests/test_expanded_tui_smoke.py::test_all_screen_navigations (10.35s) - Mitigation: Skip PlantUML rendering; mock or gate behind marker.
- tests/test_structure_integration.py::test_structure_fix_and_apply (9.76s) - Mitigation: Short-circuit large logs; use smaller fixtures.
- tests/test_cli_surface_contract.py::TestContractStability::test_legacy_mode_is_repeatable (8.02s) - Mitigation: Use in-memory data instead of writing to disk.
- tests/test_structure_integration.py::test_structure_scan (7.09s) - Mitigation: Reduce parametrization combinations.
