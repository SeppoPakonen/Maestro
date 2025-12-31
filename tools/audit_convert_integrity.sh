#!/usr/bin/env bash
set -u

root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$root"

fail=0
warn=0
expected_file="tools/audit_expected_convert_files.txt"

echo "== Convert Integrity Audit =="

echo "[1/7] Expected file list"
if [[ ! -f "$expected_file" ]]; then
  echo "FAIL: missing $expected_file"
  exit 2
fi

if ! python - <<'PY'
from pathlib import Path
expected = [p.strip() for p in Path("tools/audit_expected_convert_files.txt").read_text().splitlines() if p.strip()]
missing = [p for p in expected if not Path(p).exists()]
print(f"Expected entries: {len(expected)}")
print(f"Missing entries: {len(missing)}")
for p in missing[:200]:
    print(f" - {p}")
raise SystemExit(1 if missing else 0)
PY
then
  fail=1
fi

echo

echo "[2/7] Entrypoint symbol checks"
if ! python - <<'PY'
import pathlib
import re

checks = {
    "maestro/convert/convert_orchestrator.py": [
        r"def\s+cmd_plan\b",
        r"def\s+cmd_run\b",
        r"validate_plan",
        r"inventory",
    ],
    "maestro/convert/semantic_integrity.py": [r"semantic", r"equivalence", r"risk"],
    "maestro/convert/conversion_memory.py": [r"decisions", r"conventions", r"glossary"],
    "maestro/convert/playbook_manager.py": [r"playbook", r"validate", r"override"],
}

failed = []
for path, pats in checks.items():
    p = pathlib.Path(path)
    if not p.exists():
        failed.append((path, "missing"))
        continue
    text = p.read_text(errors="ignore")
    for pat in pats:
        if not re.search(pat, text):
            failed.append((path, f"pattern missing: {pat}"))
            break

shim_checks = [
    "convert_orchestrator.py",
    "conversion_memory.py",
    "semantic_integrity.py",
    "playbook_manager.py",
    "cross_repo_semantic_diff.py",
    "inventory_generator.py",
    "execution_engine.py",
    "context_builder.py",
    "planner.py",
    "realize_worker.py",
    "regression_replay.py",
    "coverage_report.py",
]

for shim in shim_checks:
    p = pathlib.Path(shim)
    if not p.exists():
        failed.append((shim, "missing"))
        continue
    text = p.read_text(errors="ignore")
    if "maestro.convert" not in text:
        failed.append((shim, "compatibility shim missing maestro.convert import"))

print(f"Entrypoint failures: {len(failed)}")
for path, reason in failed:
    print(f" - {path}: {reason}")
raise SystemExit(1 if failed else 0)
PY
then
  fail=1
fi

echo

echo "[3/7] Syntax compile checks"
if ! python - <<'PY'
import py_compile
import pathlib

paths = [
    "convert_orchestrator.py",
    "execution_engine.py",
    "planner.py",
    "realize_worker.py",
    "semantic_integrity.py",
    "conversion_memory.py",
    "playbook_manager.py",
    "regression_replay.py",
    "cross_repo_semantic_diff.py",
    "maestro/convert/convert_orchestrator.py",
    "maestro/convert/execution_engine.py",
    "maestro/convert/planner.py",
    "maestro/convert/realize_worker.py",
    "maestro/convert/semantic_integrity.py",
    "maestro/convert/conversion_memory.py",
    "maestro/convert/playbook_manager.py",
    "maestro/convert/regression_replay.py",
    "maestro/convert/cross_repo_semantic_diff.py",
]

failed = []
for path in paths:
    p = pathlib.Path(path)
    if not p.exists():
        failed.append((path, "missing"))
        continue
    try:
        py_compile.compile(str(p), doraise=True)
    except py_compile.PyCompileError as exc:
        failed.append((path, str(exc)))

print(f"Compile failures: {len(failed)}")
for path, reason in failed:
    print(f" - {path}: {reason}")
raise SystemExit(1 if failed else 0)
PY
then
  fail=1
fi

echo

echo "[4/7] Import sanity checks"
if ! python - <<'PY'
import importlib
import traceback

modules = [
    "maestro.convert",
    "maestro.convert.convert_orchestrator",
    "maestro.convert.execution_engine",
    "maestro.convert.planner",
    "maestro.convert.realize_worker",
    "maestro.convert.semantic_integrity",
    "maestro.convert.conversion_memory",
    "maestro.convert.playbook_manager",
    "maestro.convert.regression_replay",
    "maestro.convert.cross_repo_semantic_diff",
]

failed = []
for name in modules:
    try:
        importlib.import_module(name)
    except Exception as exc:
        failed.append((name, exc))

print(f"Import failures: {len(failed)}")
for name, exc in failed:
    print(f" - {name}: {exc}")
    traceback.print_exception(type(exc), exc, exc.__traceback__)
raise SystemExit(1 if failed else 0)
PY
then
  fail=1
fi

echo

echo "[5/7] Schema JSON parse checks"
if ! python - <<'PY'
import json
import pathlib

paths = []
root = pathlib.Path(".")

plan_schema = root / "conversion_plan_schema.json"
paths.append(plan_schema)

paths.extend(sorted((root / "tools/convert_tests/schemas").glob("*.json")))
paths.extend(sorted((root / "tools/convert_tests/scenarios").glob("**/expected/*schema*.json")))

failed = []
for path in paths:
    if not path.exists():
        failed.append((path, "missing"))
        continue
    try:
        json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        failed.append((path, f"json decode error: {exc}"))

print(f"Schema JSON files checked: {len(paths)}")
print(f"Schema parse failures: {len(failed)}")
for path, reason in failed:
    print(f" - {path}: {reason}")
raise SystemExit(1 if failed else 0)
PY
then
  fail=1
fi

echo

echo "[6/7] Git history check"
if ! git log --oneline --decorate --all --grep="convert:" --grep="semantic" --grep="playbook" --grep="rehears" --grep="arbitr" --grep="checkpoint" -n 5; then
  echo "FAIL: unable to scan git history"
  fail=1
fi

echo

echo "[7/7] Convert-focused tests"
convert_tests=(
  test_conversion_orchestrator.py
  test_conversion_memory_stability.py
  test_cross_repo_semantic_diff.py
  test_semantic_integrity.py
  test_playbook_functionality.py
  test_playbook_integration.py
  test_regression_replay.py
  test_realize_worker.py
  test_realize_worker_mock.py
  test_checkpoint_rehearsal.py
  test_arbitration.py
  test_arbitration_functionality.py
  test_semantic_diff.py
  test_decision_override.py
  test_decision_override_integration.py
  test_stage3.py
  tests/test_semantic_integrity.py
)

existing_tests=()
for test in "${convert_tests[@]}"; do
  if [[ -f "$test" ]]; then
    existing_tests+=("$test")
  fi
done

if [[ ${#existing_tests[@]} -eq 0 ]]; then
  echo "FAIL: no convert-focused tests found"
  fail=1
else
  if [[ ! -x "$root/tools/test/run.sh" ]]; then
    echo "FAIL: missing tools/test/run.sh"
    fail=1
  else
    echo "Running: bash tools/test/run.sh ${existing_tests[*]}"
    if ! bash tools/test/run.sh "${existing_tests[@]}"; then
      fail=1
    fi
  fi
fi

echo
if [[ $fail -eq 0 ]]; then
  if [[ $warn -eq 1 ]]; then
    echo "PASS: convert integrity audit (warnings)"
  else
    echo "PASS: convert integrity audit"
  fi
  exit 0
fi

echo "FAIL: convert integrity audit"
exit 1
