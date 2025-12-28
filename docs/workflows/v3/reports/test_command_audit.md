# Test Command Audit Report

**Generated:** 2025-12-28 00:09:10 UTC

**Policy:** [Test Command Truth Policy](test_command_truth_policy.md)

**Canonical Commands:** `allowed_commands.normalized.txt`

---

## Summary

- ✅ Compliant: 41 command references
- ⚠️  Suspicious: 29 potential matches (may be false positives)
- ❌ Non-compliant: 0 command references

---

## ✅ Compliant Tests

These tests reference commands present in `allowed_commands.normalized.txt`.

```
tests/test_build_default.py:106: maestro build default
tests/test_plan_cli_fix.py:65: maestro discuss add
tests/test_reactive_fix_loop.py:231: maestro build run
tests/test_reactive_fix_loop.py:242: maestro build run
tests/test_reactive_fix_loop.py:249: maestro build fix
tests/test_reactive_fix_loop.py:260: maestro build fix
tests/test_reactive_fix_loop.py:318: maestro build run
tests/test_reactive_fix_loop.py:329: maestro build run
tests/test_reactive_fix_loop.py:339: maestro build fix
tests/test_reactive_fix_loop.py:350: maestro build fix
tests/test_repo_resolve_ai_upp.py:185: maestro repo resolve
tests/test_repo_resolve_ai_upp.py:189: maestro repo resolve
tests/test_repo_resolve_ai_upp.py:210: maestro init failed
tests/test_repo_resolve_ai_upp.py:220: maestro repo resolve
tests/test_repo_resolve_ai_upp.py:228: maestro repo resolve
tests/test_repo_resolve_ai_upp.py:2: maestro repo resolve
tests/test_repo_workflow_ai_upp_e2e.py:107: maestro repo show
tests/test_repo_workflow_ai_upp_e2e.py:117: maestro repo show
tests/test_repo_workflow_ai_upp_e2e.py:129: maestro repo show
tests/test_repo_workflow_ai_upp_e2e.py:139: maestro repo show
tests/test_repo_workflow_ai_upp_e2e.py:26: maestro init creates
tests/test_repo_workflow_ai_upp_e2e.py:27: maestro repo resolve
tests/test_repo_workflow_ai_upp_e2e.py:28: maestro repo show
tests/test_repo_workflow_ai_upp_e2e.py:2: maestro repo commands
tests/test_repo_workflow_ai_upp_e2e.py:48: maestro init failed
tests/test_repo_workflow_ai_upp_e2e.py:60: maestro repo resolve
tests/test_repo_workflow_ai_upp_e2e.py:6: maestro repo resolve
tests/test_repo_workflow_ai_upp_e2e.py:71: maestro repo resolve
tests/test_repo_workflow_ai_upp_e2e.py:7: maestro repo show
tests/test_stress_scenarios.py:101: maestro task run
tests/test_stress_scenarios.py:103: maestro task run
tests/test_stress_scenarios.py:125: maestro task run
tests/test_stress_scenarios.py:126: maestro task run
tests/test_stress_scenarios.py:128: maestro task run
tests/test_structure_integration.py:5: maestro build structure
tests/test_structure_rulebooks.py:400: maestro build fix
tests/test_structure_ux.py:328: maestro build structure
tests/test_structure_ux.py:6: maestro build structure
tests/test_structure_ux.py:7: maestro build structure
tests/test_tu6_cli.py:18: maestro tu transform
tests/test_tu6_cli.py:21: maestro tu transform
```

---

## ⚠️ Suspicious References

These may be false positives (code examples, comments, etc.).

```
tests/test_arbitration.py:135: maestro files created (in code/comment)
tests/test_batch_functionality.py:15: maestro package to (in code/comment)
tests/test_branch_guard.py:4: maestro import git_guard (in code/comment)
tests/test_build_default.py:13: maestro directory to (in code/comment)
tests/test_build_functionality.py:11: maestro directory to (in code/comment)
tests/test_build_functionality.py:34: maestro directory structure (in code/comment)
tests/test_build_plan_functionality.py:11: maestro directory to (in code/comment)
tests/test_build_plan_functionality.py:83: maestro directory structure (in code/comment)
tests/test_deterministic_filesystem.py:128: maestro artifacts are (in code/comment)
tests/test_deterministic_filesystem.py:131: maestro state is (in code/comment)
tests/test_hub_functionality.py:11: maestro package to (in code/comment)
tests/test_interrupt_handling.py:110: maestro directory and (in code/comment)
tests/test_plan_cli_fix.py:25: maestro plan should (in code/comment)
tests/test_plan_cli_fix.py:30: maestro plan add (in code/comment)
tests/test_plan_cli_fix.py:35: maestro plan list (in code/comment)
tests/test_plan_cli_fix.py:40: maestro plan sh (in code/comment)
tests/test_plan_cli_fix.py:45: maestro plan discuss (in code/comment)
tests/test_plan_help.py:49: maestro plan --help (in code/comment)
tests/test_regression_replay.py:286: maestro directory if (in code/comment)
tests/test_repo_resolve_ai_upp.py:212: maestro directory was (in code/comment)
tests/test_repo_resolve_ai_upp.py:213: maestro directory was (in code/comment)
tests/test_repo_resolve_ai_upp.py:269: maestro directory if (in code/comment)
tests/test_repo_workflow_ai_upp_e2e.py:150: maestro directory if (in code/comment)
tests/test_repo_workflow_ai_upp_e2e.py:50: maestro directory was (in code/comment)
tests/test_repo_workflow_ai_upp_e2e.py:51: maestro directory was (in code/comment)
tests/test_repo_workflow_ai_upp_e2e.py:58: maestro already exists (in code/comment)
tests/test_rulebook_matching.py:27: maestro directory in (in code/comment)
tests/test_structure_integration.py:18: maestro command and (in code/comment)
tests/test_upp_discovery.py:11: maestro module to (in code/comment)
```

---

## ❌ Non-Compliant Tests

**These tests reference commands NOT in the allowed list.**

**Action Required:**
1. Mark with `@pytest.mark.legacy` OR
2. Rename file with `legacy_` prefix OR
3. Delete if obsolete and document below

_None detected._

---

## 🗑️ Removed Tests

**Tests deleted during this audit:**

_No tests removed yet._

---

## Next Steps

1. Review non-compliant tests
2. Quarantine (mark as `legacy`) or remove
3. Re-run `pytest -q` to verify compliance
4. Update this report after changes

