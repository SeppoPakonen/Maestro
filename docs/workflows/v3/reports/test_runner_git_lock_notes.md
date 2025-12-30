# Test Runner Git Lock Notes

## Files Reviewed
- tools/test/run.sh
- tools/test/pytest_checkpoint_plugin.py
- pytest.ini
- conftest.py
- tests/conftest.py
- Makefile
- tools/test/README.md

## Git Touchpoints Found
- tools/test/run.sh: preflight checks `.git/index.lock` and exits 2 when present.
- tools/test/run.sh: optional git metadata via `git rev-parse HEAD` when `--git-check` is used.
- maestro/ops/doctor.py: `check_git_status` runs `git rev-parse` and `git status`.
- tests/test_ops_doctor.py: invokes `check_git_status` and `run_doctor` (which calls git).
- tests/test_ops_doctor_subwork.py: invokes `run_doctor` (which calls git).
- tests/test_reactive_fix_loop.py: initializes a git repo via subprocess git calls.
- tests/test_safe_apply_revert.py: initializes a git repo via subprocess git calls.

## Notes
- conftest.py and tests/conftest.py do not call git directly.
- pytest.ini default markexpr is `not legacy and not slow`.
