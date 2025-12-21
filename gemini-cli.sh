#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_CLI_DIR="${ROOT}/external/ai-agents/gemini-cli/.local-cli"
INSTALLER_SCRIPT="${ROOT}/external/ai-agents/gemini-cli/scripts/install_local_cli.sh"
GEMINI_DIST="${LOCAL_CLI_DIR}/package/dist/index.js"

if [ -f "${GEMINI_DIST}" ]; then
  exec node "${GEMINI_DIST}" "$@"
fi

echo "Gemini CLI not found at ${GEMINI_DIST}" >&2
echo "Attempting to install locally..." >&2

if [ -x "${INSTALLER_SCRIPT}" ]; then
  "${INSTALLER_SCRIPT}"

  # Retry running the CLI after installation
  if [ -f "${GEMINI_DIST}" ]; then
    exec node "${GEMINI_DIST}" "$@"
  else
    echo "Error: Installation completed but CLI still not found at ${GEMINI_DIST}" >&2
    exit 1
  fi
else
  echo "Error: Installer script not found or not executable at ${INSTALLER_SCRIPT}" >&2
  exit 1
fi

exit 1
