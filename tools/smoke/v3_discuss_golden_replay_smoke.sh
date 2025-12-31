#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${MAESTRO_BIN:-}" ]]; then
  read -r -a MAESTRO_CMD <<<"$MAESTRO_BIN"
elif [[ -x "./maestro.py" ]]; then
  MAESTRO_CMD=("./maestro.py")
else
  MAESTRO_CMD=(python -m maestro)
fi

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

  tmp_dir=$(mktemp -d)
  cp -a "$fixture_dir" "$tmp_dir/"
  temp_fixture="$tmp_dir/$(basename "$fixture_dir")"

  if "${MAESTRO_CMD[@]}" discuss replay "$temp_fixture" --dry-run "${extra_flags[@]}"; then
    echo "PASS ${fixture_dir}"
  else
    echo "FAIL ${fixture_dir}"
    status=1
  fi
  rm -rf "$tmp_dir"
  echo ""
done

exit $status
