#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QWEN_DIST="$ROOT/external/ai-agents/qwen-code/packages/cli/dist/index.js"

if [ -f "$QWEN_DIST" ]; then
  exec node "$QWEN_DIST" "$@"
fi

cat <<EOF >&2
qwen CLI not found at:
  $QWEN_DIST
Build the local CLI (e.g. npm install && npm run build --workspace packages/cli)
then re-run this script.
EOF
exit 1
