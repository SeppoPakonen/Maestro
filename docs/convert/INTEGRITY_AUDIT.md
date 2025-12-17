# Conversion Integrity Audit

Audit date: 2025-12-17

## Git snapshot

- Branch: main
- HEAD: b90ffc58d02e8fb9ea7d97e6068c19276d5fe2d2
- Worktree: dirty (unrelated TUI edits present; conversion-adjacent files modified include `maestro/ui_facade/semantic.py` and `maestro/ui_facade/decisions.py`.)

## Expected conversion inventory

Based on the previously recorded "140 files changed" conversion batch, the expected conversion assets are captured in:

- `tools/audit_expected_convert_files.txt` (65 entries)

The list includes:

- Core conversion modules (`maestro/convert/*.py`)
- Compatibility shims at repo root (`convert_orchestrator.py`, `conversion_memory.py`, etc.)
- Conversion docs and schemas (`PLAYBOOK_FEATURE.md`, `SEMANTIC_INTEGRITY.md`, `conversion_plan_schema.json`, checklists)
- Conversion test files in repo root and `tests/`
- Conversion scenario harness (`tools/convert_tests/*`)

## Actual inventory check

- Expected files present: 65
- Missing files: 0

Verification command:

```
python - <<'PY'
from pathlib import Path
expected = Path('tools/audit_expected_convert_files.txt').read_text().splitlines()
missing = [p for p in expected if p.strip() and not Path(p.strip()).exists()]
print('MISSING:', len(missing))
for p in missing[:200]:
    print(' -', p)
PY
```

## Entrypoint symbol checks

- `maestro/convert/` entrypoints contain required symbols (cmd_plan/cmd_run, semantic equivalence, memory decisions, playbook validation).
- Root-level conversion files are compatibility shims that forward to `maestro/convert/*`.

Verification command:

```
python - <<'PY'
import pathlib, re
checks = {
  'maestro/convert/convert_orchestrator.py': [r"def\s+cmd_plan\b", r"def\s+cmd_run\b", r"validate_plan", r"inventory"],
  'maestro/convert/semantic_integrity.py': [r"semantic", r"equivalence", r"risk"],
  'maestro/convert/conversion_memory.py': [r"decisions", r"conventions", r"glossary"],
  'maestro/convert/playbook_manager.py': [r"playbook", r"validate", r"override"],
}
failed = []
for f, pats in checks.items():
    p = pathlib.Path(f)
    if not p.exists():
        failed.append((f, 'missing'))
        continue
    txt = p.read_text(errors='ignore')
    for pat in pats:
        if not re.search(pat, txt):
            failed.append((f, f'pattern missing: {pat}'))
            break
print('FAIL:', len(failed))
for f, why in failed:
    print(f'- {f}: {why}')
PY
```

## History / branch drift scan

Conversion pipeline commits are present on `main`, including:

- `3820783` (stage1 overview inventory and mapping plan)
- `4c6403a` (stage2 core builds loop)
- `7adfc7f` (stage3 grow_from_main)
- `7502c10` (generic plan+execute pipeline)
- `b31444b` (realize worker)
- `30f0dcb` (semantic integrity)
- `905c280` (arbitration)
- `3e1a090` (regression replay)
- `0c15f11` (cross-repo semantic diff)
- `eefddd1` (playbooks)
- `d9b4e48` (checkpoint rehearsal)
- `d71f553` (conversion integrity reconciliation)

Recent TUI work begins after these conversions (e.g. `6e17020` and later), and the conversion commits are still reachable from `main`.
A `restored-commits` branch appears in history but contains duplicates of the same conversion commits already on `main`.

## Tests

Audit script run:

```
tools/audit_convert_integrity.sh
```

Result: FAIL due to missing pytest in this environment:

- `python -m pytest --version` failed (pytest not installed)

No conversion tests were executed here. Re-run after installing pytest to confirm full green.

## Missing / altered work

- Missing conversion files: none detected.
- Entrypoint symbols: present in `maestro/convert/*`.
- Root shims: present and import from `maestro.convert`.

## Recovery plan and actions taken

- Recovery actions: none required (no missing files detected; conversion commits present on `main`).
- Actions taken:
  - Added `tools/audit_expected_convert_files.txt`.
  - Added `tools/audit_convert_integrity.sh`.
  - Updated this audit report.

If a future audit finds missing files, recover via `git cherry-pick` from the conversion commits listed above, then re-run the audit script and pytest.
