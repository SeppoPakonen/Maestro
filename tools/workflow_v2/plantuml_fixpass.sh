#!/usr/bin/env bash
set -euo pipefail

mapfile -t FILES < <(find docs/workflows/v2 -name '*.puml' | sort)

OUTPUT_DIR="$(pwd)/docs/workflows/v2/generated/svg"
mkdir -p "$OUTPUT_DIR"

FAIL_LOG="docs/workflows/v2/reports/plantuml_failures.log"
: > "$FAIL_LOG"

total=${#FILES[@]}
ok=0
failed=0

for file in "${FILES[@]}"; do
  if /usr/bin/plantuml -tsvg -o "$OUTPUT_DIR" "$file" > /tmp/plantuml_fixpass.out 2> /tmp/plantuml_fixpass.err; then
    ok=$((ok + 1))
  else
    failed=$((failed + 1))
    printf '%s\n' "$file" | tee -a "$FAIL_LOG" > /dev/null
    cat /tmp/plantuml_fixpass.err >> "$FAIL_LOG"
    printf '\n' >> "$FAIL_LOG"
  fi
done

printf 'total: %s\n' "$total"
printf 'ok: %s\n' "$ok"
printf 'failed: %s\n' "$failed"

if [ "$failed" -ne 0 ]; then
  printf 'FAILED:\n'
  grep -v '^$' "$FAIL_LOG" | awk '/\.puml$/{print}'
fi

exit 0
