#!/usr/bin/env bash
set -euo pipefail

echo "Waiting for command extraction to complete..."
EXPECTED=46
CMD_DIR="/home/sblo/Dev/Maestro/docs/workflows/v2/ir/cmd"

while true; do
  COUNT=$(ls "${CMD_DIR}"/CMD-*.yaml 2>/dev/null | wc -l)
  echo "[$(date +%H:%M:%S)] Progress: ${COUNT}/${EXPECTED} files"

  if [ "$COUNT" -ge "$EXPECTED" ]; then
    echo "✓ Extraction complete!"
    break
  fi

  if ! ps aux | grep -q "[a]i_extract_cmd_ir.sh"; then
    echo "⚠ Extraction process not found but only ${COUNT}/${EXPECTED} files exist"
    echo "Proceeding with finalization anyway..."
    break
  fi

  sleep 15
done

echo
echo "Running finalization..."
exec "$(dirname "$0")/finalize_extraction.sh"
