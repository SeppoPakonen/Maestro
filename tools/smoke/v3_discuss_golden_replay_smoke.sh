#!/usr/bin/env bash
set -euo pipefail

MAESTRO_BIN=${MAESTRO_BIN:-maestro.py}

status=0

for fixture_dir in tests/fixtures/discuss_sessions/golden/EX-*; do
  if [[ ! -d "$fixture_dir" ]]; then
    continue
  fi

  context_kind=$(python - <<'PY' "$fixture_dir/meta.json"
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
    print(json.load(f).get("context", {}).get("kind", "global"))
PY
)

  extra_flags=()
  if [[ "$context_kind" == "repo" || "$context_kind" == "runbook" || "$context_kind" == "solutions" ]]; then
    extra_flags+=(--allow-cross-context)
  fi

  if "$MAESTRO_BIN" discuss replay "$fixture_dir" --dry-run "${extra_flags[@]}"; then
    echo "PASS ${fixture_dir}"
  else
    echo "FAIL ${fixture_dir}"
    status=1
  fi
  echo ""
done

exit $status
