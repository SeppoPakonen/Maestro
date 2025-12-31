#!/usr/bin/env bash
set -euo pipefail

TIMEOUT_SECONDS="${MAESTRO_HELP_TIMEOUT:-2}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [[ -n "${MAESTRO_BIN:-}" ]]; then
  MAESTRO_CMD=("$MAESTRO_BIN")
elif [[ -x "$REPO_ROOT/maestro.py" ]]; then
  MAESTRO_CMD=("$REPO_ROOT/maestro.py")
elif [[ -x "$HOME/venv/bin/python" ]]; then
  MAESTRO_CMD=("$HOME/venv/bin/python" "-m" "maestro")
else
  echo "ERROR: Could not resolve MAESTRO_BIN or ./maestro.py" >&2
  exit 1
fi

run_case() {
  local label="$1"
  shift
  local env_prefix=()
  if [[ "$label" == legacy:* ]]; then
    env_prefix=(MAESTRO_ENABLE_LEGACY=1)
    label="${label#legacy:}"
  fi

  printf "CHECK %-32s " "$label"
  cmd=(timeout "${TIMEOUT_SECONDS}s" "${MAESTRO_CMD[@]}" "$@")
  if [[ "${#env_prefix[@]}" -gt 0 ]]; then
    cmd=(env "${env_prefix[@]}" "${cmd[@]}")
  fi
  if "${cmd[@]}" >/tmp/maestro_help_smoke.out 2>/tmp/maestro_help_smoke.err; then
    echo "PASS"
    return 0
  fi

  status=$?
  if [[ "$status" -eq 124 ]]; then
    echo "FAIL (timeout ${TIMEOUT_SECONDS}s)"
  else
    echo "FAIL (exit ${status})"
  fi
  echo "STDOUT:" >&2
  sed -n '1,160p' /tmp/maestro_help_smoke.out >&2 || true
  echo "STDERR:" >&2
  sed -n '1,160p' /tmp/maestro_help_smoke.err >&2 || true
  return 1
}

run_case "legacy:resume --help" resume --help
run_case "legacy:rules --help" rules --help
run_case "legacy:root --help" root --help
run_case "legacy:understand --help" understand --help
run_case "make --help" make --help
run_case "workflow" workflow
