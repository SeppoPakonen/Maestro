#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Maestro Test Runner
# ==============================================================================
# Features:
# - Creates/uses a Python virtual environment at REPO_ROOT/.venv
# - Installs pytest and pytest-xdist (optional) from requirements-dev.txt
# - Supports speed profiles: fast, medium, slow, all
# - Supports parallelism via pytest-xdist with configurable worker count
# - Writes checkpoint files to /tmp containing PASSED test nodeids
# - Supports resume mode to skip previously PASSED tests
# - Provides profiling output and slow-test shortlist via --profile
# - Passes through additional pytest arguments
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv"

CHECKPOINT_DELIM="--- PASSED NODEIDS ---"

IGNORE_GIT_LOCK=0
GIT_LOCK_DETECT=1
for arg in "$@"; do
  if [[ "$arg" == "--ignore-git-lock" ]]; then
    IGNORE_GIT_LOCK=1
  elif [[ "$arg" == "--no-git-lock-detect" ]]; then
    GIT_LOCK_DETECT=0
  fi
done

# ==============================================================================
# Timestamp setup (needed for bisect and checkpoint)
# ==============================================================================
RUN_TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ==============================================================================
# Git lock check
# ==============================================================================
if [[ "$IGNORE_GIT_LOCK" -eq 0 ]] && [[ -f "$REPO_ROOT/.git/index.lock" ]]; then
  echo "ERROR: Git index lock detected at $REPO_ROOT/.git/index.lock" >&2
  echo "" >&2
  echo "Lock details:" >&2
  ls -l "$REPO_ROOT/.git/index.lock" >&2 || true
  echo "" >&2
  echo "Active git processes (top 20):" >&2
  ps aux | grep -E '[g]it' | head -20 >&2 || true
  echo "" >&2
  echo "If no git process is running, remove stale lock: rm -f .git/index.lock" >&2
  exit 2
fi

export GIT_OPTIONAL_LOCKS=0
export MAESTRO_REPO_ROOT="$REPO_ROOT"

# ==============================================================================
# Git index lock detection
# ==============================================================================
check_git_index_lock_or_die() {
  local context="${1:-unknown}"
  local maybe_nodeid="${2:-unknown}"

  if [[ -f "$REPO_ROOT/.git/index.lock" ]]; then
    echo "============================================================="
    echo "GIT INDEX LOCK DETECTED"
    echo "============================================================="
    echo "Repo root: $REPO_ROOT"
    echo "Lock path: $REPO_ROOT/.git/index.lock"
    echo "Lock details:"
    ls -l "$REPO_ROOT/.git/index.lock" >&2 || true
    echo "Context: $context"
    echo "NodeID: $maybe_nodeid"
    echo "============================================================="

    # Write incident record to temp file
    local incident_file="/tmp/maestro_git_lock_incident_$(date +%Y%m%d_%H%M%S).txt"
    {
      echo "GIT INDEX LOCK INCIDENT"
      echo "Timestamp: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
      echo "Repo root: $REPO_ROOT"
      echo "Lock path: $REPO_ROOT/.git/index.lock"
      echo "Context: $context"
      echo "NodeID: $maybe_nodeid"
      echo "Lock details:"
      ls -l "$REPO_ROOT/.git/index.lock" 2>&1 || echo "Could not list lock file"
    } > "$incident_file"

    # If we have a specific nodeid that caused the lock, write culprit record
    if [[ "$maybe_nodeid" != "unknown" ]]; then
      local culprit_file="/tmp/maestro_git_lock_culprit_$(date +%Y%m%d_%H%M%S).txt"
      {
        echo "GIT INDEX LOCK CULPRIT"
        echo "Timestamp: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
        echo "Culprit NodeID: $maybe_nodeid"
        echo "Context: $context"
        echo "Repo root: $REPO_ROOT"
        echo "Lock path: $REPO_ROOT/.git/index.lock"
      } > "$culprit_file"

      echo "CULPRIT NODEID: $maybe_nodeid"
      echo "Culprit record written to: $culprit_file"
    fi

    echo "Incident record written to: $incident_file"
    echo "Use --bisect-git-lock to find culprit nodeid."
    exit 89
  fi
}

# ==============================================================================
# Python detection
# ==============================================================================
PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "ERROR: python3/python not found in PATH." >&2
    exit 1
  fi
fi

# ==============================================================================
# Virtual environment setup
# ==============================================================================
if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating venv at $VENV_DIR"
  if ! "$PYTHON_BIN" -m venv "$VENV_DIR"; then
    echo "ERROR: failed to create venv at $VENV_DIR using $PYTHON_BIN" >&2
    echo "Hint: ensure the python venv module is available (e.g. python3-venv)." >&2
    exit 1
  fi
fi

VENV_PY="$VENV_DIR/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  echo "ERROR: venv python not found at $VENV_PY" >&2
  exit 1
fi

# ==============================================================================
# Dependency installation
# ==============================================================================
PYTEST_REQ="pytest>=8,<10"
REQ_FILE="$REPO_ROOT/requirements-dev.txt"
if [[ -f "$REQ_FILE" ]]; then
  REQ_LINE=$(grep -E '^[[:space:]]*pytest([<>=!~].*)?$' "$REQ_FILE" | head -1 | sed 's/#.*//; s/[[:space:]]//g')
  if [[ -n "$REQ_LINE" ]]; then
    PYTEST_REQ="$REQ_LINE"
  fi
fi

# Always try to install pytest-xdist if available
EXTRA_REQS=("pytest-xdist")

PIP_DISABLE_PIP_VERSION_CHECK=1 "$VENV_PY" -m pip install -q "$PYTEST_REQ" "${EXTRA_REQS[@]}"

# ==============================================================================
# Argument parsing
# ==============================================================================
PROFILE_MODE=""
PROFILE_SET=0
PROFILE_OUTPUT=0
WORKERS=""
RESUME_FROM="${MAESTRO_TEST_RESUME_FROM:-}"
CHECKPOINT_ENABLED=1
SKIPLIST="${MAESTRO_TEST_SKIPLIST:-}"
SKIPPED_ONLY=0
TEST_TIMEOUT="${MAESTRO_TEST_TIMEOUT:-}"
GIT_CHECK=0
PRINT_PYTEST_CMD=0
WORKERS_SET=0
USER_REPORT=0
USER_MAXFAIL=0
USER_DURATIONS=0
USER_DISABLE_WARNINGS=0
USER_COLOR=0
BISECT_GIT_LOCK=0
BISECT_CHECKPOINT_FILE=""
BISECT_LIMIT=""
RUN_SERIAL_EVEN_IF_MAIN_FAILS=0
RESUME_MAIN_FROM=""
RESUME_SERIAL_FROM=""
USER_MARKER_EXPR=""

RUNNER_OPTS=()
PYTEST_ARGS=()
PASS_THROUGH=0

show_help() {
  cat <<EOF
Usage: $0 [OPTIONS] [PYTEST_ARGS...]

Runner Options:
  -h, --help              Show this help message
  --workers N             Number of parallel workers (default: cpu_count-1)
  -j, --jobs N            Alias for --workers
  --ignore-git-lock       Skip git index lock preflight check
  --no-git-lock-detect    Disable git index.lock detection during tests
  --git-check             Enable git metadata checks in runner output
  --fast                  Speed profile: fast (not slow, not legacy, not tui, not integration)
  --medium                Speed profile: medium (not legacy, not tui) [default]
  --slow                  Speed profile: slow (slow, not legacy, not tui)
  --all                   Speed profile: all (not legacy)
  --profile               Capture slow-test profile output and reports
  --print-pytest-cmd       Print the resolved pytest command and exit
  --resume-from FILE      Resume from checkpoint, skipping previously PASSED tests
  --resume-main-from FILE Resume main lane from checkpoint, skipping PASSED tests
  --resume-serial-from FILE Resume serial lane from checkpoint, skipping PASSED tests
  --checkpoint            Enable checkpoint writing (default)
  --no-checkpoint         Disable checkpoint writing
  --run-serial-even-if-main-fails
                         Run serial lane even if main lane fails
  --skiplist FILE         File containing test patterns to skip (default: none)
  --skipped               Run ONLY the tests listed in skiplist
  --timeout SECONDS       Kill tests that run longer than SECONDS (requires pytest-timeout)
  --bisect-git-lock       Run in bisect mode to find git index lock culprit
  --from-checkpoint FILE  Start bisect from checkpoint file (skip passed tests)
  --limit N               Limit bisect to first N tests

Environment variables:
  MAESTRO_TEST_PROFILE     Default speed profile (fast|medium|slow|all)
  MAESTRO_TEST_WORKERS     Default worker count (overridden by --workers)
  MAESTRO_TEST_JOBS        Alias for MAESTRO_TEST_WORKERS
  MAESTRO_TEST_RESUME_FROM Default resume checkpoint file
  MAESTRO_TEST_SKIPLIST    Default skiplist file path
  MAESTRO_TEST_TIMEOUT     Default test timeout in seconds
  MAESTRO_TEST_ALLOW_GIT   Enable tests that perform git operations

Examples:
  # Run tests with default parallelism
  $0

  # Run only fast tests with 4 workers
  $0 --fast --workers 4

  # Run tests, fail fast on first error
  $0 -x --maxfail=1

  # Run a specific test file
  $0 tests/test_subwork_stack.py

  # Resume from a previous checkpoint
  $0 --resume-from /tmp/maestro_pytest_checkpoint_20231215_120000.txt

  # Profile slow tests and generate reports
  $0 --profile tests/test_subwork_stack.py

  # Use custom skiplist
  $0 --skiplist tools/test/skiplist.txt

  # Bisect to find git index lock culprit
  $0 --bisect-git-lock --medium

All additional arguments are passed directly to pytest. Use "--" to
separate runner options from pytest options if needed.
EOF
}

while [[ $# -gt 0 ]]; do
  if [[ "$PASS_THROUGH" -eq 1 ]]; then
    PYTEST_ARGS+=("$1")
    shift
    continue
  fi

  case "$1" in
    --)
      PASS_THROUGH=1
      shift
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    --ignore-git-lock)
      IGNORE_GIT_LOCK=1
      RUNNER_OPTS+=("$1")
      shift
      ;;
    --no-git-lock-detect)
      GIT_LOCK_DETECT=0
      RUNNER_OPTS+=("$1")
      shift
      ;;
    --git-check)
      GIT_CHECK=1
      RUNNER_OPTS+=("$1")
      shift
      ;;
    --print-pytest-cmd)
      PRINT_PYTEST_CMD=1
      RUNNER_OPTS+=("$1")
      shift
      ;;
    --workers)
      if [[ -z "${2:-}" ]]; then
        echo "ERROR: --workers requires a number argument" >&2
        exit 1
      fi
      WORKERS="$2"
      WORKERS_SET=1
      RUNNER_OPTS+=("$1" "$2")
      shift 2
      ;;
    --workers=*)
      WORKERS="${1#*=}"
      WORKERS_SET=1
      RUNNER_OPTS+=("$1")
      shift
      ;;
    -j|--jobs)
      if [[ -z "${2:-}" ]]; then
        echo "ERROR: --jobs requires a number argument" >&2
        exit 1
      fi
      WORKERS="$2"
      WORKERS_SET=1
      RUNNER_OPTS+=("$1" "$2")
      shift 2
      ;;
    --fast|--medium|--slow|--all)
      if [[ "$PROFILE_SET" -eq 1 ]]; then
        echo "ERROR: Multiple speed profiles specified" >&2
        exit 1
      fi
      PROFILE_SET=1
      PROFILE_MODE="${1#--}"
      RUNNER_OPTS+=("$1")
      shift
      ;;
    --profile)
      PROFILE_OUTPUT=1
      RUNNER_OPTS+=("$1")
      shift
      ;;
    --resume-from)
      if [[ -z "${2:-}" ]]; then
        echo "ERROR: --resume-from requires a file path argument" >&2
        exit 1
      fi
      RESUME_FROM="$2"
      RUNNER_OPTS+=("$1" "$2")
      shift 2
      ;;
    --resume-from=*)
      RESUME_FROM="${1#*=}"
      RUNNER_OPTS+=("$1")
      shift
      ;;
    --resume-main-from)
      if [[ -z "${2:-}" ]]; then
        echo "ERROR: --resume-main-from requires a file path argument" >&2
        exit 1
      fi
      RESUME_MAIN_FROM="$2"
      RUNNER_OPTS+=("$1" "$2")
      shift 2
      ;;
    --resume-main-from=*)
      RESUME_MAIN_FROM="${1#*=}"
      RUNNER_OPTS+=("$1")
      shift
      ;;
    --resume-serial-from)
      if [[ -z "${2:-}" ]]; then
        echo "ERROR: --resume-serial-from requires a file path argument" >&2
        exit 1
      fi
      RESUME_SERIAL_FROM="$2"
      RUNNER_OPTS+=("$1" "$2")
      shift 2
      ;;
    --resume-serial-from=*)
      RESUME_SERIAL_FROM="${1#*=}"
      RUNNER_OPTS+=("$1")
      shift
      ;;
    --checkpoint)
      CHECKPOINT_ENABLED=1
      RUNNER_OPTS+=("$1")
      shift
      ;;
    --no-checkpoint)
      CHECKPOINT_ENABLED=0
      RUNNER_OPTS+=("$1")
      shift
      ;;
    --bisect-git-lock)
      BISECT_GIT_LOCK=1
      RUNNER_OPTS+=("$1")
      shift
      ;;
    --from-checkpoint)
      if [[ -z "${2:-}" ]]; then
        echo "ERROR: --from-checkpoint requires a file path argument" >&2
        exit 1
      fi
      BISECT_CHECKPOINT_FILE="$2"
      RUNNER_OPTS+=("$1" "$2")
      shift 2
      ;;
    --limit)
      if [[ -z "${2:-}" ]]; then
        echo "ERROR: --limit requires a number argument" >&2
        exit 1
      fi
      BISECT_LIMIT="$2"
      RUNNER_OPTS+=("$1" "$2")
      shift 2
      ;;
    --skiplist)
      if [[ -z "${2+x}" ]]; then
        echo "ERROR: --skiplist requires a file path argument (use \"\" to disable)" >&2
        exit 1
      fi
      SKIPLIST="$2"
      RUNNER_OPTS+=("$1" "$2")
      shift 2
      ;;
    --skipped)
      SKIPPED_ONLY=1
      RUNNER_OPTS+=("$1")
      shift
      ;;
    --timeout)
      if [[ -z "${2:-}" ]]; then
        echo "ERROR: --timeout requires a number of seconds" >&2
        exit 1
      fi
      TEST_TIMEOUT="$2"
      RUNNER_OPTS+=("$1" "$2")
      shift 2
      ;;
    --run-serial-even-if-main-fails)
      RUN_SERIAL_EVEN_IF_MAIN_FAILS=1
      RUNNER_OPTS+=("$1")
      shift
      ;;
    *)
      PYTEST_ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ -n "$RESUME_FROM" ]] && ([[ -n "$RESUME_MAIN_FROM" ]] || [[ -n "$RESUME_SERIAL_FROM" ]]); then
  echo "ERROR: Use --resume-from or --resume-main-from/--resume-serial-from, not both." >&2
  exit 1
fi

# ==============================================================================
# Speed profile selection
# ==============================================================================
PROFILE_SOURCE="default"
if [[ -n "${MAESTRO_TEST_PROFILE:-}" ]]; then
  PROFILE_SOURCE="env"
fi
if [[ "$PROFILE_SET" -eq 1 ]]; then
  PROFILE_SOURCE="flag"
fi
if [[ -z "$PROFILE_MODE" ]]; then
  PROFILE_MODE="${MAESTRO_TEST_PROFILE:-medium}"
fi

case "$PROFILE_MODE" in
  fast|medium|slow|all)
    ;;
  *)
    echo "ERROR: Invalid profile '$PROFILE_MODE'. Must be: fast, medium, slow, or all" >&2
    exit 1
    ;;
esac

# ==============================================================================
# Worker count setup
# ==============================================================================
if [[ -z "$WORKERS" ]]; then
  if [[ -n "${MAESTRO_TEST_WORKERS:-}" ]]; then
    WORKERS="$MAESTRO_TEST_WORKERS"
    WORKERS_SET=1
  elif [[ -n "${MAESTRO_TEST_JOBS:-}" ]]; then
    WORKERS="$MAESTRO_TEST_JOBS"
    WORKERS_SET=1
  else
    CPU_COUNT=$("$VENV_PY" -c 'import os; print(os.cpu_count() or 1)' 2>/dev/null || echo "1")
    WORKERS=$((CPU_COUNT > 1 ? CPU_COUNT - 1 : 1))
  fi
fi

# ==============================================================================
# Check if pytest-xdist is available
# ==============================================================================
XDIST_AVAILABLE=0
if "$VENV_PY" -c "import xdist" 2>/dev/null; then
  XDIST_AVAILABLE=1
fi

# ==============================================================================
# Detect user-provided xdist args and strip if unavailable
# ==============================================================================
USER_XDIST=0
USER_WORKERS=""
PYTEST_ARGS_FILTERED=()
SKIP_NEXT=0
for ((i=0; i<${#PYTEST_ARGS[@]}; i++)); do
  arg="${PYTEST_ARGS[$i]}"
  if [[ "$SKIP_NEXT" -eq 1 ]]; then
    SKIP_NEXT=0
    continue
  fi
  case "$arg" in
    -n|--numprocesses)
      USER_XDIST=1
      if (( i + 1 < ${#PYTEST_ARGS[@]} )); then
        USER_WORKERS="${PYTEST_ARGS[$((i + 1))]}"
        SKIP_NEXT=1
      fi
      if [[ "$XDIST_AVAILABLE" -eq 0 ]]; then
        echo "Note: xdist not available; ignoring $arg ${USER_WORKERS:-}" >&2
        continue
      fi
      PYTEST_ARGS_FILTERED+=("$arg")
      if [[ -n "${USER_WORKERS:-}" ]]; then
        PYTEST_ARGS_FILTERED+=("$USER_WORKERS")
      fi
      ;;
    -n=*|--numprocesses=*)
      USER_XDIST=1
      USER_WORKERS="${arg#*=}"
      if [[ "$XDIST_AVAILABLE" -eq 0 ]]; then
        echo "Note: xdist not available; ignoring $arg" >&2
        continue
      fi
      PYTEST_ARGS_FILTERED+=("$arg")
      ;;
    *)
      PYTEST_ARGS_FILTERED+=("$arg")
      ;;
  esac
done
PYTEST_ARGS=("${PYTEST_ARGS_FILTERED[@]}")

PYTEST_ARGS_NO_MARKER=()
SKIP_NEXT=0
for ((i=0; i<${#PYTEST_ARGS[@]}; i++)); do
  arg="${PYTEST_ARGS[$i]}"
  if [[ "$SKIP_NEXT" -eq 1 ]]; then
    SKIP_NEXT=0
    continue
  fi
  case "$arg" in
    -m)
      if (( i + 1 < ${#PYTEST_ARGS[@]} )); then
        USER_MARKER_EXPR="${PYTEST_ARGS[$((i + 1))]}"
        SKIP_NEXT=1
      fi
      ;;
    -m=*)
      USER_MARKER_EXPR="${arg#*=}"
      ;;
    *)
      PYTEST_ARGS_NO_MARKER+=("$arg")
      ;;
  esac
done
PYTEST_ARGS=("${PYTEST_ARGS_NO_MARKER[@]}")

EXPECTS_VALUE=0
for ((i=0; i<${#PYTEST_ARGS[@]}; i++)); do
  arg="${PYTEST_ARGS[$i]}"
  if [[ "$EXPECTS_VALUE" -eq 1 ]]; then
    EXPECTS_VALUE=0
    continue
  fi
  case "$arg" in
    -r)
      USER_REPORT=1
      EXPECTS_VALUE=1
      ;;
    -r*)
      USER_REPORT=1
      ;;
    --maxfail)
      USER_MAXFAIL=1
      EXPECTS_VALUE=1
      ;;
    --maxfail=*)
      USER_MAXFAIL=1
      ;;
    -x|--exitfirst)
      USER_MAXFAIL=1
      ;;
    --durations)
      USER_DURATIONS=1
      EXPECTS_VALUE=1
      ;;
    --durations=*)
      USER_DURATIONS=1
      ;;
    --disable-warnings)
      USER_DISABLE_WARNINGS=1
      ;;
    --color)
      USER_COLOR=1
      EXPECTS_VALUE=1
      ;;
    --color=*)
      USER_COLOR=1
      ;;
  esac
done

USE_XDIST=0
if [[ "$USER_XDIST" -eq 1 ]]; then
  USE_XDIST=0
elif [[ "$XDIST_AVAILABLE" -eq 1 ]] && [[ "$WORKERS" -gt 1 ]]; then
  USE_XDIST=1
fi

XDIST_ACTIVE=0
WORKERS_EFFECTIVE=1
if [[ "$USER_XDIST" -eq 1 ]] && [[ "$XDIST_AVAILABLE" -eq 1 ]]; then
  XDIST_ACTIVE=1
  WORKERS_EFFECTIVE="${USER_WORKERS:-auto}"
elif [[ "$USE_XDIST" -eq 1 ]]; then
  XDIST_ACTIVE=1
  WORKERS_EFFECTIVE="$WORKERS"
fi

SERIAL_WORKERS_EFFECTIVE=1
if [[ "$XDIST_AVAILABLE" -eq 1 ]]; then
  SERIAL_WORKERS_EFFECTIVE=0
fi

if [[ "$XDIST_AVAILABLE" -eq 0 ]] && ([[ "$USER_XDIST" -eq 1 ]] || [[ "$WORKERS" -gt 1 ]]); then
  echo "Note: xdist not available; running serial" >&2
fi

# ==============================================================================
# Determine explicit selectors
# ==============================================================================
is_explicit_selector() {
  local arg="$1"

  if [[ "$arg" == -* ]]; then
    return 1
  fi
  if [[ "$arg" == *"::"* ]]; then
    return 0
  fi
  if [[ "$arg" == tests || "$arg" == tests/* || "$arg" == ./tests/* ]]; then
    return 0
  fi
  if [[ "$arg" == *.py ]]; then
    return 0
  fi
  if [[ "$arg" == /* && -e "$arg" ]]; then
    return 0
  fi
  if [[ "$arg" == *"/"* && -e "$arg" ]]; then
    return 0
  fi
  return 1
}

EXPLICIT_SELECTORS=()
PYTEST_NON_SELECTOR_ARGS=()
EXPECTS_VALUE=0

for arg in "${PYTEST_ARGS[@]}"; do
  if [[ "$EXPECTS_VALUE" -eq 1 ]]; then
    PYTEST_NON_SELECTOR_ARGS+=("$arg")
    EXPECTS_VALUE=0
    continue
  fi

  case "$arg" in
    -k|-m|-n|--maxfail|--timeout|--numprocesses)
      EXPECTS_VALUE=1
      PYTEST_NON_SELECTOR_ARGS+=("$arg")
      continue
      ;;
  esac

  if is_explicit_selector "$arg"; then
    EXPLICIT_SELECTORS+=("$arg")
  else
    PYTEST_NON_SELECTOR_ARGS+=("$arg")
  fi
done

if [[ "${#EXPLICIT_SELECTORS[@]}" -gt 0 ]]; then
  SELECTION_MODE="explicit"
elif [[ "$PROFILE_MODE" == "all" ]]; then
  SELECTION_MODE="full"
else
  SELECTION_MODE="profile"
fi

strip_xdist_args() {
  local -n input_array="$1"
  local -n output_array="$2"
  local skip_next=0
  output_array=()
  for arg in "${input_array[@]}"; do
    if [[ "$skip_next" -eq 1 ]]; then
      skip_next=0
      continue
    fi
    case "$arg" in
      -n|--numprocesses)
        skip_next=1
        continue
        ;;
      -n=*|--numprocesses=*)
        continue
        ;;
      *)
        output_array+=("$arg")
        ;;
    esac
  done
}

PYTEST_NON_SELECTOR_ARGS_NO_XDIST=()
PYTEST_ARGS_NO_XDIST=()
strip_xdist_args PYTEST_NON_SELECTOR_ARGS PYTEST_NON_SELECTOR_ARGS_NO_XDIST
strip_xdist_args PYTEST_ARGS PYTEST_ARGS_NO_XDIST

# ==============================================================================
# Base pytest args (markers, skiplist, timeout)
# ==============================================================================
PYTEST_BASE_ARGS=(-c pytest.ini)
PROFILE_MARKER_EXPR=""

case "$PROFILE_MODE" in
  fast)
    PROFILE_MARKER_EXPR="not slow and not legacy and not tui and not integration"
    ;;
  medium)
    PROFILE_MARKER_EXPR="not legacy and not tui"
    ;;
  slow)
    PROFILE_MARKER_EXPR="slow and not legacy and not tui"
    ;;
  all)
    PROFILE_MARKER_EXPR="not legacy"
    ;;
esac

EFFECTIVE_MARKER_EXPR="$PROFILE_MARKER_EXPR"
if [[ -n "$USER_MARKER_EXPR" ]]; then
  EFFECTIVE_MARKER_EXPR="$USER_MARKER_EXPR"
fi

combine_markers() {
  local base_expr="$1"
  local lane_expr="$2"
  if [[ -z "$base_expr" ]]; then
    echo "$lane_expr"
  else
    echo "(${base_expr}) and (${lane_expr})"
  fi
}

MAIN_MARKER_EXPR=$(combine_markers "$EFFECTIVE_MARKER_EXPR" "not serial")
SERIAL_MARKER_EXPR=$(combine_markers "$EFFECTIVE_MARKER_EXPR" "serial")

PYTEST_RUN_DEFAULT_ARGS=()
if [[ "$USER_REPORT" -eq 0 ]]; then
  PYTEST_RUN_DEFAULT_ARGS+=(-r fE)
fi
if [[ "$USER_MAXFAIL" -eq 0 ]]; then
  PYTEST_RUN_DEFAULT_ARGS+=(--maxfail=0)
fi
if [[ "$PROFILE_OUTPUT" -eq 1 ]]; then
  if [[ "$USER_DURATIONS" -eq 0 ]]; then
    PYTEST_RUN_DEFAULT_ARGS+=(--durations=50)
  fi
  if [[ "$USER_COLOR" -eq 0 ]]; then
    PYTEST_RUN_DEFAULT_ARGS+=(--color=no)
  fi
else
  if [[ "$USER_DURATIONS" -eq 0 ]]; then
    PYTEST_RUN_DEFAULT_ARGS+=(--durations=25)
  fi
fi
if [[ "$USER_DISABLE_WARNINGS" -eq 0 ]]; then
  PYTEST_RUN_DEFAULT_ARGS+=(--disable-warnings)
fi

# ==============================================================================
# Process skiplist file
# ==============================================================================
if [[ -n "$SKIPLIST" ]] && [[ -f "$SKIPLIST" ]]; then
  if [[ "$SKIPPED_ONLY" -eq 1 ]]; then
    echo "Running ONLY skipped tests from: $SKIPLIST" >&2
    while IFS= read -r line || [[ -n "$line" ]]; do
      [[ -z "$line" ]] && continue
      [[ "$line" =~ ^[[:space:]]*# ]] && continue
      PYTEST_BASE_ARGS+=("$line")
    done < "$SKIPLIST"
  else
    while IFS= read -r line || [[ -n "$line" ]]; do
      [[ -z "$line" ]] && continue
      [[ "$line" =~ ^[[:space:]]*# ]] && continue
      PYTEST_BASE_ARGS+=(--ignore="$line")
    done < "$SKIPLIST"
  fi
elif [[ -n "$SKIPLIST" ]]; then
  echo "WARNING: Skiplist file not found: $SKIPLIST" >&2
  echo "Continuing without skiplist..." >&2
fi

# ==============================================================================
# Apply timeout if specified
# ==============================================================================
if [[ -n "$TEST_TIMEOUT" ]]; then
  if ! "$VENV_PY" -c "import pytest_timeout" 2>/dev/null; then
    echo "WARNING: pytest-timeout not installed, timeout will not be enforced" >&2
    echo "Install with: pip install pytest-timeout" >&2
  else
    PYTEST_BASE_ARGS+=(--timeout="$TEST_TIMEOUT")
    PYTEST_BASE_ARGS+=(--timeout-method=thread)
  fi
fi

# ==============================================================================
# Bisect git lock mode
# ==============================================================================
if [[ "$BISECT_GIT_LOCK" -eq 1 ]]; then
  echo "Running in bisect-git-lock mode to find culprit test..."

  # Collect nodeids
  NODEIDS_FILE="/tmp/maestro_pytest_nodeids_${RUN_TIMESTAMP}.txt"
  echo "Collecting test nodeids..."

  # Build collection args similar to the main run
  COLLECT_ARGS=(-o addopts= --collect-only -q)
  COLLECT_ARGS+=("${PYTEST_BASE_ARGS[@]}")
  COLLECT_ARGS+=("${PYTEST_NON_SELECTOR_ARGS[@]}")
  if [[ "${#EXPLICIT_SELECTORS[@]}" -gt 0 ]]; then
    COLLECT_ARGS+=("${EXPLICIT_SELECTORS[@]}")
  fi

  set +e
  "$VENV_PY" -m pytest "${COLLECT_ARGS[@]}" 2>/dev/null | grep -E '^[[:space:]]*[^[:space:]]' > "$NODEIDS_FILE"
  COLLECT_EXIT=$?
  set -e

  if [[ "$COLLECT_EXIT" -ne 0 ]]; then
    echo "ERROR: pytest collection failed" >&2
    exit "$COLLECT_EXIT"
  fi

  # Read nodeids into array
  mapfile -t ALL_NODEIDS < "$NODEIDS_FILE"

  # Filter nodeids if checkpoint provided
  if [[ -n "$BISECT_CHECKPOINT_FILE" ]] && [[ -f "$BISECT_CHECKPOINT_FILE" ]]; then
    echo "Using checkpoint file to skip passed tests: $BISECT_CHECKPOINT_FILE"
    # Load passed tests from checkpoint
    if grep -Fxq "$CHECKPOINT_DELIM" "$BISECT_CHECKPOINT_FILE"; then
      PASSED_NODEIDS=$(awk -v delim="$CHECKPOINT_DELIM" '
        $0 == delim { in_list=1; next }
        in_list == 1 { if (NF > 0) print }
      ' "$BISECT_CHECKPOINT_FILE")
    else
      PASSED_NODEIDS=$(awk 'NF > 0 && $0 !~ /^#/ && $0 !~ /^LANE=/' "$BISECT_CHECKPOINT_FILE")
    fi

    # Filter out passed nodeids
    FILTERED_NODEIDS=()
    for nodeid in "${ALL_NODEIDS[@]}"; do
      if ! echo "$PASSED_NODEIDS" | grep -Fxq "$nodeid"; then
        FILTERED_NODEIDS+=("$nodeid")
      fi
    done
    ALL_NODEIDS=("${FILTERED_NODEIDS[@]}")
  fi

  # Limit nodeids if specified
  if [[ -n "$BISECT_LIMIT" ]] && [[ "$BISECT_LIMIT" =~ ^[0-9]+$ ]]; then
    echo "Limiting to first $BISECT_LIMIT tests"
    if [[ ${#ALL_NODEIDS[@]} -gt $BISECT_LIMIT ]]; then
      ALL_NODEIDS=("${ALL_NODEIDS[@]:0:$BISECT_LIMIT}")
    fi
  fi

  echo "Testing ${#ALL_NODEIDS[@]} tests for git index lock..."

  # Run each test individually to find the culprit
  for i in "${!ALL_NODEIDS[@]}"; do
    nodeid="${ALL_NODEIDS[$i]}"
    echo "Testing ($((i+1))/${#ALL_NODEIDS[@]}): $nodeid"

    # Check for git index lock before running test
    check_git_index_lock_or_die "pre-test" "$nodeid"

    # Run the individual test
    set +e
    "$VENV_PY" -m pytest -q "$nodeid"
    exit_code=$?
    set -e

    # Check for git index lock immediately after test
    check_git_index_lock_or_die "post-test" "$nodeid"

    # Small delay to allow any background git processes to finish
    sleep 0.2

    # Check again after delay
    check_git_index_lock_or_die "post-test-delayed" "$nodeid"

    if [[ $exit_code -ne 0 ]]; then
      echo "Test $nodeid failed with exit code $exit_code, continuing..."
    fi
  done

  echo "Bisect completed. No git index lock detected during testing."
  exit 0
fi

# ==============================================================================
# Bisect git lock mode
# ==============================================================================
if [[ "$BISECT_GIT_LOCK" -eq 1 ]]; then
  echo "Running in bisect-git-lock mode to find culprit test..."

  # Collect nodeids
  NODEIDS_FILE="/tmp/maestro_pytest_nodeids_${RUN_TIMESTAMP}.txt"
  echo "Collecting test nodeids..."

  # Build collection args similar to the main run
  COLLECT_ARGS=(-o addopts= --collect-only -q)
  COLLECT_ARGS+=("${PYTEST_BASE_ARGS[@]}")
  COLLECT_ARGS+=("${PYTEST_NON_SELECTOR_ARGS[@]}")
  if [[ "${#EXPLICIT_SELECTORS[@]}" -gt 0 ]]; then
    COLLECT_ARGS+=("${EXPLICIT_SELECTORS[@]}")
  fi

  set +e
  "$VENV_PY" -m pytest "${COLLECT_ARGS[@]}" 2>/dev/null | grep -E '^[[:space:]]*[^[:space:]]' > "$NODEIDS_FILE"
  COLLECT_EXIT=$?
  set -e

  if [[ "$COLLECT_EXIT" -ne 0 ]]; then
    echo "ERROR: pytest collection failed" >&2
    exit "$COLLECT_EXIT"
  fi

  # Read nodeids into array
  mapfile -t ALL_NODEIDS < "$NODEIDS_FILE"

  # Filter nodeids if checkpoint provided
  if [[ -n "$BISECT_CHECKPOINT_FILE" ]] && [[ -f "$BISECT_CHECKPOINT_FILE" ]]; then
    echo "Using checkpoint file to skip passed tests: $BISECT_CHECKPOINT_FILE"
    # Load passed tests from checkpoint
    if grep -Fxq "$CHECKPOINT_DELIM" "$BISECT_CHECKPOINT_FILE"; then
      PASSED_NODEIDS=$(awk -v delim="$CHECKPOINT_DELIM" '
        $0 == delim { in_list=1; next }
        in_list == 1 { if (NF > 0) print }
      ' "$BISECT_CHECKPOINT_FILE")
    else
      PASSED_NODEIDS=$(awk 'NF > 0 && $0 !~ /^#/ && $0 !~ /^LANE=/' "$BISECT_CHECKPOINT_FILE")
    fi

    # Filter out passed nodeids
    FILTERED_NODEIDS=()
    for nodeid in "${ALL_NODEIDS[@]}"; do
      if ! echo "$PASSED_NODEIDS" | grep -Fxq "$nodeid"; then
        FILTERED_NODEIDS+=("$nodeid")
      fi
    done
    ALL_NODEIDS=("${FILTERED_NODEIDS[@]}")
  fi

  # Limit nodeids if specified
  if [[ -n "$BISECT_LIMIT" ]] && [[ "$BISECT_LIMIT" =~ ^[0-9]+$ ]]; then
    echo "Limiting to first $BISECT_LIMIT tests"
    if [[ ${#ALL_NODEIDS[@]} -gt $BISECT_LIMIT ]]; then
      ALL_NODEIDS=("${ALL_NODEIDS[@]:0:$BISECT_LIMIT}")
    fi
  fi

  echo "Testing ${#ALL_NODEIDS[@]} tests for git index lock..."

  # Run each test individually to find the culprit
  for i in "${!ALL_NODEIDS[@]}"; do
    nodeid="${ALL_NODEIDS[$i]}"
    echo "Testing ($((i+1))/${#ALL_NODEIDS[@]}): $nodeid"

    # Check for git index lock before running test
    check_git_index_lock_or_die "pre-test" "$nodeid"

    # Run the individual test
    set +e
    "$VENV_PY" -m pytest -q "$nodeid"
    exit_code=$?
    set -e

    # Check for git index lock immediately after test
    check_git_index_lock_or_die "post-test" "$nodeid"

    # Small delay to allow any background git processes to finish
    sleep 0.2

    # Check again after delay
    check_git_index_lock_or_die "post-test-delayed" "$nodeid"

    if [[ $exit_code -ne 0 ]]; then
      echo "Test $nodeid failed with exit code $exit_code, continuing..."
    fi
  done

  echo "Bisect completed. No git index lock detected during testing."
  exit 0
fi

# ==============================================================================
# Checkpoint setup
# ==============================================================================
RUN_ID_MAIN="maestro_pytest_main_${RUN_TIMESTAMP}"
RUN_ID_SERIAL="maestro_pytest_serial_${RUN_TIMESTAMP}"
RUN_LOG_FILE="/tmp/maestro_pytest_run_${RUN_TIMESTAMP}.log"
FAILURES_FILE="/tmp/maestro_pytest_failures_${RUN_TIMESTAMP}.txt"

CHECKPOINT_FILE_MAIN=""
CHECKPOINT_FILE_SERIAL=""
if [[ "$CHECKPOINT_ENABLED" -eq 1 ]]; then
  if [[ -n "${MAESTRO_TEST_CHECKPOINT:-}" ]]; then
    CHECKPOINT_FILE_MAIN="$MAESTRO_TEST_CHECKPOINT"
  else
    CHECKPOINT_FILE_MAIN="/tmp/maestro_pytest_checkpoint_main_${RUN_TIMESTAMP}.txt"
  fi
  CHECKPOINT_FILE_SERIAL="/tmp/maestro_pytest_checkpoint_serial_${RUN_TIMESTAMP}.txt"
fi

# ==============================================================================
# Resume mode: collect nodeids and filter out passed tests
# ==============================================================================
read_checkpoint_lane() {
  local checkpoint_path="$1"
  awk -F'=' '/^LANE=/{print $2; exit}' "$checkpoint_path"
}

checkpoint_passed_nodeids() {
  local checkpoint_path="$1"
  if grep -Fxq "$CHECKPOINT_DELIM" "$checkpoint_path"; then
    awk -v delim="$CHECKPOINT_DELIM" '
      $0 == delim { in_list=1; next }
      in_list == 1 { if (NF > 0) print }
    ' "$checkpoint_path"
  else
    awk 'NF > 0 && $0 !~ /^#/ && $0 !~ /^LANE=/' "$checkpoint_path"
  fi
}

build_resume_nodeids() {
  local resume_file="$1"
  local marker_expr="$2"
  local -n out_nodeids="$3"
  out_nodeids=()

  if [[ -z "$resume_file" ]]; then
    return 0
  fi

  if [[ ! -f "$resume_file" ]]; then
    echo "ERROR: Resume checkpoint file not found: $resume_file" >&2
    exit 1
  fi

  COLLECT_NON_SELECTOR_ARGS=()
  SKIP_NEXT_COLLECT=0
  for arg in "${PYTEST_NON_SELECTOR_ARGS_NO_XDIST[@]}"; do
    if [[ "$SKIP_NEXT_COLLECT" -eq 1 ]]; then
      SKIP_NEXT_COLLECT=0
      continue
    fi
    case "$arg" in
      -q|--quiet)
        continue
        ;;
      *)
        COLLECT_NON_SELECTOR_ARGS+=("$arg")
        ;;
    esac
  done

  COLLECT_ARGS=(-o addopts= --collect-only)
  COLLECT_ARGS+=("${PYTEST_BASE_ARGS[@]}")
  COLLECT_ARGS+=(-m "$marker_expr")
  COLLECT_ARGS+=("${COLLECT_NON_SELECTOR_ARGS[@]}")
  if [[ "${#EXPLICIT_SELECTORS[@]}" -gt 0 ]]; then
    COLLECT_ARGS+=("${EXPLICIT_SELECTORS[@]}")
  fi

  set +e
  COLLECTED_NODEIDS=$("$VENV_PY" - "${COLLECT_ARGS[@]}" <<'PY'
import contextlib
import io
import sys

import pytest

nodeids = []


class Collector:
    def pytest_collection_finish(self, session):
        nodeids.extend(item.nodeid for item in session.items)


def main():
    args = sys.argv[1:]
    if "--collect-only" not in args:
        args.append("--collect-only")

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        rc = pytest.main(args, plugins=[Collector()])

    if rc != 0:
        sys.stderr.write(buf.getvalue())
        sys.exit(rc)

    if nodeids:
        sys.stdout.write("\n".join(nodeids))


if __name__ == "__main__":
    main()
PY
  )
  COLLECT_EXIT=$?
  set -e

  if [[ "$COLLECT_EXIT" -eq 5 ]]; then
    return 0
  fi
  if [[ "$COLLECT_EXIT" -ne 0 ]]; then
    echo "ERROR: pytest collection failed during resume selection" >&2
    exit "$COLLECT_EXIT"
  fi

  if [[ -z "$COLLECTED_NODEIDS" ]]; then
    echo "ERROR: No tests collected for resume selection" >&2
    exit 1
  fi

  PASSED_NODEIDS=$(checkpoint_passed_nodeids "$resume_file")

  if [[ -n "$PASSED_NODEIDS" ]]; then
    REMAINING_NODEIDS=$(comm -23 \
      <(printf "%s\n" "$COLLECTED_NODEIDS" | sort) \
      <(printf "%s\n" "$PASSED_NODEIDS" | sort))
  else
    REMAINING_NODEIDS="$COLLECTED_NODEIDS"
  fi

  if [[ -z "$REMAINING_NODEIDS" ]]; then
    echo "Resume: all selected tests already passed; nothing to run."
    return 2
  fi

  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" ]] && continue
    out_nodeids+=("$line")
  done <<< "$REMAINING_NODEIDS"
}

if [[ -n "$RESUME_FROM" ]]; then
  if [[ ! -f "$RESUME_FROM" ]]; then
    echo "ERROR: Resume checkpoint file not found: $RESUME_FROM" >&2
    exit 1
  fi
  RESUME_LANE=$(read_checkpoint_lane "$RESUME_FROM")
  if [[ "$RESUME_LANE" == "serial" ]]; then
    RESUME_SERIAL_FROM="$RESUME_FROM"
  else
    RESUME_MAIN_FROM="$RESUME_FROM"
  fi
fi

RESUME_NODEIDS_MAIN=()
RESUME_NODEIDS_SERIAL=()
RESUME_MAIN_ALL_PASSED=0
RESUME_SERIAL_ALL_PASSED=0
if ! build_resume_nodeids "$RESUME_MAIN_FROM" "$MAIN_MARKER_EXPR" RESUME_NODEIDS_MAIN; then
  RESUME_STATUS=$?
  if [[ "$RESUME_STATUS" -eq 2 ]]; then
    RESUME_MAIN_ALL_PASSED=1
  else
    exit "$RESUME_STATUS"
  fi
fi
if ! build_resume_nodeids "$RESUME_SERIAL_FROM" "$SERIAL_MARKER_EXPR" RESUME_NODEIDS_SERIAL; then
  RESUME_STATUS=$?
  if [[ "$RESUME_STATUS" -eq 2 ]]; then
    RESUME_SERIAL_ALL_PASSED=1
  else
    exit "$RESUME_STATUS"
  fi
fi

# ==============================================================================
# Export checkpoint path for plugin
# ==============================================================================
unset MAESTRO_TEST_RESUME_FROM
unset MAESTRO_TEST_CHECKPOINT
unset MAESTRO_TEST_LANE
unset MAESTRO_TEST_RUN_ID
export MAESTRO_TEST_PROFILE_EFFECTIVE="$PROFILE_MODE"
export MAESTRO_TEST_FAILURES_FILE="$FAILURES_FILE"
export MAESTRO_TEST_RUN_LOG="$RUN_LOG_FILE"

# ==============================================================================
# Build pytest arguments
# ==============================================================================
PYTEST_PLUGINS=(-p tools.test.pytest_checkpoint_plugin)
if [[ "$GIT_LOCK_DETECT" -eq 1 ]]; then
  PYTEST_PLUGINS+=(-p tools.test.pytest_git_lock_plugin)
fi

PYTEST_RUN_FIXED_ARGS=("${PYTEST_BASE_ARGS[@]}" "${PYTEST_RUN_DEFAULT_ARGS[@]}")

MAIN_RUN_FIXED_ARGS=("${PYTEST_RUN_FIXED_ARGS[@]}" -m "$MAIN_MARKER_EXPR")
SERIAL_RUN_FIXED_ARGS=("${PYTEST_RUN_FIXED_ARGS[@]}" -m "$SERIAL_MARKER_EXPR")

MAIN_XDIST_ARGS=()
if [[ "$USE_XDIST" -eq 1 ]]; then
  MAIN_XDIST_ARGS=(-n "$WORKERS")
fi

SERIAL_XDIST_ARGS=()
if [[ "$XDIST_AVAILABLE" -eq 1 ]]; then
  SERIAL_XDIST_ARGS=(-n 0)
fi

MAIN_FIXED_ARGS_WITH_XDIST=("${MAIN_RUN_FIXED_ARGS[@]}" "${MAIN_XDIST_ARGS[@]}")
SERIAL_FIXED_ARGS_WITH_XDIST=("${SERIAL_RUN_FIXED_ARGS[@]}" "${SERIAL_XDIST_ARGS[@]}")

MAIN_RUN_ARGS=("${MAIN_FIXED_ARGS_WITH_XDIST[@]}")
if [[ "${#RESUME_NODEIDS_MAIN[@]}" -gt 0 ]]; then
  MAIN_RUN_ARGS+=("${PYTEST_NON_SELECTOR_ARGS[@]}")
  MAIN_RUN_ARGS+=("${RESUME_NODEIDS_MAIN[@]}")
else
  MAIN_RUN_ARGS+=("${PYTEST_ARGS[@]}")
fi

SERIAL_RUN_ARGS=("${SERIAL_FIXED_ARGS_WITH_XDIST[@]}")
if [[ "${#RESUME_NODEIDS_SERIAL[@]}" -gt 0 ]]; then
  SERIAL_RUN_ARGS+=("${PYTEST_NON_SELECTOR_ARGS_NO_XDIST[@]}")
  SERIAL_RUN_ARGS+=("${RESUME_NODEIDS_SERIAL[@]}")
else
  SERIAL_RUN_ARGS+=("${PYTEST_ARGS_NO_XDIST[@]}")
fi

CHUNK_SIZE=200
MAIN_CHUNKED_RUN=0
SERIAL_CHUNKED_RUN=0
if [[ "${#RESUME_NODEIDS_MAIN[@]}" -gt "$CHUNK_SIZE" ]]; then
  MAIN_CHUNKED_RUN=1
fi
if [[ "${#RESUME_NODEIDS_SERIAL[@]}" -gt "$CHUNK_SIZE" ]]; then
  SERIAL_CHUNKED_RUN=1
fi

MAIN_RUN_ARGS_STR=$(printf '%q ' "${MAIN_RUN_ARGS[@]}")
SERIAL_RUN_ARGS_STR=$(printf '%q ' "${SERIAL_RUN_ARGS[@]}")

# ==============================================================================
# Print test run configuration
# ==============================================================================
PYTEST_CMD="$VENV_PY -m pytest"
PYTEST_VERSION=$("$VENV_PY" -c 'import pytest; print(pytest.__version__)' 2>/dev/null || echo "unknown")
GIT_SHA="(disabled)"
if [[ "$GIT_CHECK" -eq 1 ]]; then
  GIT_SHA=$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo "unknown")
fi

if [[ "$PRINT_PYTEST_CMD" -eq 1 ]]; then
  echo "Main lane pytest command:"
  printf '%q ' "$VENV_PY" -m pytest "${PYTEST_PLUGINS[@]}" "${MAIN_RUN_ARGS[@]}"
  echo ""
  echo "Serial lane pytest command:"
  printf '%q ' "$VENV_PY" -m pytest "${PYTEST_PLUGINS[@]}" "${SERIAL_RUN_ARGS[@]}"
  echo ""
  exit 0
fi

echo "============================================================="
echo "Maestro Test Runner Configuration"
echo "============================================================="
echo "Python:           $VENV_PY"
echo "Pytest:           $PYTEST_CMD (pytest $PYTEST_VERSION)"
echo "Git SHA:          $GIT_SHA"
if [[ "$GIT_LOCK_DETECT" -eq 1 ]]; then
  echo "Git lock detect:  enabled"
else
  echo "Git lock detect:  disabled"
fi
echo "Selection mode:   $SELECTION_MODE"
if [[ "${#EXPLICIT_SELECTORS[@]}" -gt 0 ]]; then
  echo "Collected selectors: ${EXPLICIT_SELECTORS[*]}"
else
  echo "Collected selectors: (none)"
fi
echo "Profile:          $PROFILE_MODE"
if [[ -n "$EFFECTIVE_MARKER_EXPR" ]]; then
  echo "Markers:          $EFFECTIVE_MARKER_EXPR"
else
  echo "Markers:          (pytest.ini default)"
fi
echo "Main markers:     $MAIN_MARKER_EXPR"
echo "Serial markers:   $SERIAL_MARKER_EXPR"
if [[ "$XDIST_ACTIVE" -eq 1 ]]; then
  echo "Main workers:     $WORKERS_EFFECTIVE (xdist: yes)"
else
  echo "Main workers:     $WORKERS_EFFECTIVE (xdist: no)"
fi
if [[ "$XDIST_AVAILABLE" -eq 1 ]]; then
  echo "Serial workers:   $SERIAL_WORKERS_EFFECTIVE (xdist: no)"
else
  echo "Serial workers:   $SERIAL_WORKERS_EFFECTIVE (xdist: unavailable)"
fi
if [[ -n "$RESUME_MAIN_FROM" ]]; then
  echo "Resume main:      enabled (from $RESUME_MAIN_FROM)"
fi
if [[ -n "$RESUME_SERIAL_FROM" ]]; then
  echo "Resume serial:    enabled (from $RESUME_SERIAL_FROM)"
fi
if [[ "$PROFILE_OUTPUT" -eq 1 ]]; then
  echo "Profile output:   enabled"
fi
if [[ "$CHECKPOINT_ENABLED" -eq 1 ]]; then
  echo "Checkpoint main:  $CHECKPOINT_FILE_MAIN"
  echo "Checkpoint serial:$CHECKPOINT_FILE_SERIAL"
else
  echo "Checkpoint:       disabled"
fi
echo "Run log:          $RUN_LOG_FILE"
if [[ -n "$SKIPLIST" ]] && [[ -f "$SKIPLIST" ]]; then
  if [[ "$SKIPPED_ONLY" -eq 1 ]]; then
    echo "Skiplist:         $SKIPLIST (running ONLY skipped tests)"
  else
    echo "Skiplist:         $SKIPLIST (opt-in)"
  fi
else
  echo "Skiplist:         none"
fi
echo "============================================================="
echo ""

# ==============================================================================
# Run pytest
# ==============================================================================
cd "$REPO_ROOT"

# Collect nodeids for both lanes
collect_lane_nodeids() {
  local lane_name="$1"
  local marker_expr="$2"
  local output_file="$3"

  COLLECT_ARGS=(-o addopts= --collect-only -q)
  COLLECT_ARGS+=("${PYTEST_BASE_ARGS[@]}")
  COLLECT_ARGS+=(-m "$marker_expr")
  COLLECT_ARGS+=("${PYTEST_NON_SELECTOR_ARGS_NO_XDIST[@]}")
  if [[ "${#EXPLICIT_SELECTORS[@]}" -gt 0 ]]; then
    COLLECT_ARGS+=("${EXPLICIT_SELECTORS[@]}")
  fi

  set +e
  "$VENV_PY" -m pytest "${COLLECT_ARGS[@]}" 2>/dev/null | grep -E '^[[:space:]]*[^[:space:]]' > "$output_file"
  PIPESTATUS_VALUES=("${PIPESTATUS[@]}")
  PYTEST_COLLECT_EXIT="${PIPESTATUS_VALUES[0]:-0}"
  GREP_EXIT="${PIPESTATUS_VALUES[1]:-0}"
  set -e

  if [[ "$PYTEST_COLLECT_EXIT" -eq 5 ]]; then
    : > "$output_file"
    return 0
  fi
  if [[ "$PYTEST_COLLECT_EXIT" -ne 0 ]]; then
    echo "ERROR: pytest collection failed for ${lane_name} lane" >&2
    exit "$PYTEST_COLLECT_EXIT"
  fi
  if [[ "$GREP_EXIT" -ne 0 ]] && [[ "$GREP_EXIT" -ne 1 ]]; then
    echo "ERROR: failed to parse nodeids for ${lane_name} lane" >&2
    exit "$GREP_EXIT"
  fi
}

MAIN_NODEIDS_FILE="/tmp/maestro_nodeids_main_${RUN_TIMESTAMP}.txt"
SERIAL_NODEIDS_FILE="/tmp/maestro_nodeids_serial_${RUN_TIMESTAMP}.txt"
collect_lane_nodeids "main" "$MAIN_MARKER_EXPR" "$MAIN_NODEIDS_FILE"
collect_lane_nodeids "serial" "$SERIAL_MARKER_EXPR" "$SERIAL_NODEIDS_FILE"

MAIN_NODEIDS_COUNT=0
SERIAL_NODEIDS_COUNT=0
if [[ -f "$MAIN_NODEIDS_FILE" ]]; then
  MAIN_NODEIDS_COUNT=$(wc -l < "$MAIN_NODEIDS_FILE" | tr -d ' ')
fi
if [[ -f "$SERIAL_NODEIDS_FILE" ]]; then
  SERIAL_NODEIDS_COUNT=$(wc -l < "$SERIAL_NODEIDS_FILE" | tr -d ' ')
fi

# Check for git index lock before running pytest
check_git_index_lock_or_die "pre-run" "unknown"

START_TIME=$(date +%s)
RUN_STARTED_AT=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

set +e
MAIN_EXIT_CODE=0
SERIAL_EXIT_CODE=0
MAIN_STATUS="PASS"
SERIAL_STATUS="PASS"
MAIN_STATUS_NOTE=""
SERIAL_STATUS_NOTE=""
SERIAL_RAN=0
: > "$RUN_LOG_FILE"

run_lane() {
  local lane_name="$1"
  local nodeids_count="$2"
  local resume_all_passed="$3"
  local chunked_run="$4"
  local -n run_args_ref="$5"
  local -n fixed_args_ref="$6"
  local -n non_selector_args_ref="$7"
  local -n resume_nodeids_ref="$8"
  local checkpoint_file="$9"
  local run_id="${10}"
  local lane_started_at
  local lane_finished_at
  lane_started_at=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

  if [[ "$nodeids_count" -eq 0 ]]; then
    echo "Lane ${lane_name}: no tests collected; skipping."
    return 0
  fi

  if [[ "$resume_all_passed" -eq 1 ]]; then
    echo "Lane ${lane_name}: resume indicates all tests already passed; skipping."
    return 0
  fi

  if [[ "$chunked_run" -eq 1 ]]; then
    AGG_PASSED_FILE=""
    AGG_FAILED_COUNT=0
    if [[ "$CHECKPOINT_ENABLED" -eq 1 ]]; then
      AGG_PASSED_FILE=$(mktemp)
    fi
    for ((i=0; i<${#resume_nodeids_ref[@]}; i+=CHUNK_SIZE)); do
      chunk=("${resume_nodeids_ref[@]:i:CHUNK_SIZE}")
      CHUNK_CHECKPOINT=""
      if [[ "$CHECKPOINT_ENABLED" -eq 1 ]]; then
        CHUNK_CHECKPOINT=$(mktemp)
      fi
      MAESTRO_TEST_CHECKPOINT="$CHUNK_CHECKPOINT" \
      MAESTRO_TEST_RUN_ID="$run_id" \
      MAESTRO_TEST_LANE="$lane_name" \
      "$VENV_PY" -m pytest \
        "${PYTEST_PLUGINS[@]}" \
        "${fixed_args_ref[@]}" \
        "${non_selector_args_ref[@]}" \
        "${chunk[@]}" 2>&1 | tee -a "$RUN_LOG_FILE"
      local lane_exit_code=${PIPESTATUS[0]}

      check_git_index_lock_or_die "post-run-${lane_name}" "unknown"

      if [[ "$CHECKPOINT_ENABLED" -eq 1 ]] && [[ -f "$CHUNK_CHECKPOINT" ]]; then
        if grep -Fxq "$CHECKPOINT_DELIM" "$CHUNK_CHECKPOINT"; then
          awk -v delim="$CHECKPOINT_DELIM" '
            $0 == delim { in_list=1; next }
            in_list == 1 { if (NF > 0) print }
          ' "$CHUNK_CHECKPOINT" >> "$AGG_PASSED_FILE"
        else
          awk 'NF > 0 && $0 !~ /^#/ && $0 !~ /^LANE=/' "$CHUNK_CHECKPOINT" >> "$AGG_PASSED_FILE"
        fi

        chunk_failed=$(awk -F': *' '/^# failed_tests_count:/ {print $2}' "$CHUNK_CHECKPOINT" | tail -1)
        if [[ -n "$chunk_failed" ]]; then
          AGG_FAILED_COUNT=$((AGG_FAILED_COUNT + chunk_failed))
        fi
      fi

      if [[ -n "$CHUNK_CHECKPOINT" ]]; then
        rm -f "$CHUNK_CHECKPOINT"
      fi

      if [[ "$lane_exit_code" -ne 0 ]]; then
        break
      fi
    done

    if [[ "$CHECKPOINT_ENABLED" -eq 1 ]]; then
      lane_finished_at=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
      SORTED_PASSED=$(mktemp)
      if [[ -f "$AGG_PASSED_FILE" ]]; then
        sort -u "$AGG_PASSED_FILE" > "$SORTED_PASSED"
      else
        : > "$SORTED_PASSED"
      fi

      PASSED_COUNT=$(wc -l < "$SORTED_PASSED" | tr -d ' ')
      {
        echo "# Maestro pytest checkpoint"
        echo "LANE=${lane_name}"
        echo "# run_id: $run_id"
        echo "# profile: $PROFILE_MODE"
        echo "# run_log: $RUN_LOG_FILE"
        echo "# failures_file: $FAILURES_FILE"
        echo "# started_at: $lane_started_at"
        echo "# finished_at: $lane_finished_at"
        echo "# pytest_args: ${fixed_args_ref[*]} ${non_selector_args_ref[*]}"
        echo "# passed_tests_count: $PASSED_COUNT"
        echo "# failed_tests_count: $AGG_FAILED_COUNT"
        echo "$CHECKPOINT_DELIM"
        cat "$SORTED_PASSED"
      } > "$checkpoint_file"

      rm -f "$SORTED_PASSED" "$AGG_PASSED_FILE"
    fi

    return "$lane_exit_code"
  fi

  if [[ "$CHECKPOINT_ENABLED" -eq 1 ]]; then
    MAESTRO_TEST_CHECKPOINT="$checkpoint_file" \
    MAESTRO_TEST_RUN_ID="$run_id" \
    MAESTRO_TEST_LANE="$lane_name" \
    "$VENV_PY" -m pytest \
      "${PYTEST_PLUGINS[@]}" \
      "${run_args_ref[@]}" 2>&1 | tee -a "$RUN_LOG_FILE"
  else
    MAESTRO_TEST_RUN_ID="$run_id" \
    MAESTRO_TEST_LANE="$lane_name" \
    "$VENV_PY" -m pytest \
      "${PYTEST_PLUGINS[@]}" \
      "${run_args_ref[@]}" 2>&1 | tee -a "$RUN_LOG_FILE"
  fi
  local lane_exit_code=${PIPESTATUS[0]}

  check_git_index_lock_or_die "post-run-${lane_name}" "unknown"

  return "$lane_exit_code"
}

if [[ "$MAIN_NODEIDS_COUNT" -gt 0 ]]; then
  run_lane "main" "$MAIN_NODEIDS_COUNT" "$RESUME_MAIN_ALL_PASSED" "$MAIN_CHUNKED_RUN" \
    MAIN_RUN_ARGS MAIN_FIXED_ARGS_WITH_XDIST PYTEST_NON_SELECTOR_ARGS \
    RESUME_NODEIDS_MAIN "$CHECKPOINT_FILE_MAIN" "$RUN_ID_MAIN"
  MAIN_EXIT_CODE=$?
else
  MAIN_STATUS_NOTE="(no tests collected)"
fi
if [[ "$RESUME_MAIN_ALL_PASSED" -eq 1 ]]; then
  MAIN_STATUS_NOTE="(resume: all tests already passed)"
fi

if [[ "$MAIN_EXIT_CODE" -ne 0 ]] && [[ "$RUN_SERIAL_EVEN_IF_MAIN_FAILS" -eq 0 ]]; then
  MAIN_STATUS="FAIL"
  SERIAL_STATUS="PASS"
  SERIAL_STATUS_NOTE="(skipped; main failed, use --run-serial-even-if-main-fails)"
else
  if [[ "$MAIN_EXIT_CODE" -ne 0 ]]; then
    MAIN_STATUS="FAIL"
  fi
  if [[ "$SERIAL_NODEIDS_COUNT" -gt 0 ]]; then
    if [[ "$RESUME_SERIAL_ALL_PASSED" -eq 0 ]]; then
      SERIAL_RAN=1
    fi
    run_lane "serial" "$SERIAL_NODEIDS_COUNT" "$RESUME_SERIAL_ALL_PASSED" "$SERIAL_CHUNKED_RUN" \
      SERIAL_RUN_ARGS SERIAL_FIXED_ARGS_WITH_XDIST PYTEST_NON_SELECTOR_ARGS_NO_XDIST \
      RESUME_NODEIDS_SERIAL "$CHECKPOINT_FILE_SERIAL" "$RUN_ID_SERIAL"
    SERIAL_EXIT_CODE=$?
    if [[ "$SERIAL_EXIT_CODE" -ne 0 ]]; then
      SERIAL_STATUS="FAIL"
    fi
  else
    SERIAL_STATUS_NOTE="(no tests collected)"
  fi
fi
if [[ "$RESUME_SERIAL_ALL_PASSED" -eq 1 ]] && [[ -z "$SERIAL_STATUS_NOTE" ]]; then
  SERIAL_STATUS_NOTE="(resume: all tests already passed)"
fi
set -e

FINAL_EXIT_CODE=0
if [[ "$MAIN_EXIT_CODE" -ne 0 ]] && [[ "$SERIAL_RAN" -eq 1 ]]; then
  FINAL_EXIT_CODE=1
  echo "Main lane failed (exit ${MAIN_EXIT_CODE}); serial lane exit ${SERIAL_EXIT_CODE}. Returning ${FINAL_EXIT_CODE} because both lanes ran."
elif [[ "$MAIN_EXIT_CODE" -ne 0 ]]; then
  FINAL_EXIT_CODE="$MAIN_EXIT_CODE"
elif [[ "$SERIAL_EXIT_CODE" -ne 0 ]]; then
  FINAL_EXIT_CODE="$SERIAL_EXIT_CODE"
fi

END_TIME=$(date +%s)
RUN_FINISHED_AT=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
DURATION=$((END_TIME - START_TIME))

# ==============================================================================
# Failure list extraction
# ==============================================================================
"$VENV_PY" - "$RUN_LOG_FILE" "$FAILURES_FILE" <<'PY'
import re
import sys

log_path = sys.argv[1]
out_path = sys.argv[2]

patterns = [
    re.compile(r"(?:^|\s)FAILED\s+\[[^\]]+\]\s+([^\s]+)"),
    re.compile(r"(?:^|\s)FAILED\s+([^\s]+)"),
    re.compile(r"(?:^|\s)ERROR\s+\[[^\]]+\]\s+([^\s]+)"),
    re.compile(r"(?:^|\s)ERROR\s+(?:at\s+[^\s]+\s+of\s+)?([^\s]+)"),
]


def looks_like_nodeid(text: str) -> bool:
    return "::" in text or text.endswith(".py") or text.startswith("tests/") or "/" in text


nodeids = set()
try:
    with open(log_path, "r", errors="replace") as handle:
        for line in handle:
            for pattern in patterns:
                match = pattern.search(line)
                if match:
                    nodeid = match.group(1).strip()
                    if looks_like_nodeid(nodeid):
                        nodeids.add(nodeid)
except FileNotFoundError:
    nodeids = set()

with open(out_path, "w") as handle:
    for nodeid in sorted(nodeids):
        handle.write(f"{nodeid}\n")
PY

FAILURES_COUNT=0
if [[ -f "$FAILURES_FILE" ]]; then
  FAILURES_COUNT=$(wc -l < "$FAILURES_FILE" | tr -d ' ')
fi

# ==============================================================================
# Profiling output (reports)
# ==============================================================================
if [[ "$PROFILE_OUTPUT" -eq 1 ]]; then
  PROFILE_TXT="$REPO_ROOT/docs/workflows/v3/reports/test_durations_latest.txt"
  SLOW_CANDIDATES="$REPO_ROOT/docs/workflows/v3/reports/test_slow_candidates.md"
  mkdir -p "$(dirname "$PROFILE_TXT")"

  cp "$RUN_LOG_FILE" "$PROFILE_TXT"

  DURATIONS_CSV=$(mktemp)
  awk -v root="$REPO_ROOT/" '
    /^[[:space:]]*[0-9]+(\.[0-9]+)?s[[:space:]]/ {
      duration=$1
      sub(/s$/,"",duration)
      $1=$2=""
      nodeid=$0
      sub(/^[[:space:]]+/,"",nodeid)
      if (root != "") gsub(root, "", nodeid)
      print nodeid "," duration
    }
  ' "$PROFILE_TXT" > "$DURATIONS_CSV"

  {
    echo "# Slow Test Candidates"
    echo "Generated: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Source: docs/workflows/v3/reports/test_durations_latest.txt"
    echo ""
    if [[ -s "$DURATIONS_CSV" ]]; then
      SUGGESTIONS=(
        "Mock external subprocesses to avoid real exec."
        "Use tmp_path fixtures and avoid copying full repos."
        "Reduce fixture scope or reuse session-scoped fixtures."
        "Stub filesystem scans; limit to small fixture dirs."
        "Cache expensive setup across tests."
        "Avoid network calls; use local fixtures."
        "Skip PlantUML rendering; mock or gate behind marker."
        "Short-circuit large logs; use smaller fixtures."
        "Use in-memory data instead of writing to disk."
        "Reduce parametrization combinations."
      )

      mapfile -t SLOW_LINES < <(
        sort -t',' -k2 -nr "$DURATIONS_CSV" | head -20
      )

      echo "Top 20 slowest tests:"
      idx=0
      suggestion_count=${#SUGGESTIONS[@]}
      for line in "${SLOW_LINES[@]}"; do
        nodeid="${line%%,*}"
        seconds="${line##*,}"
        suggestion="${SUGGESTIONS[$((idx % suggestion_count))]}"
        idx=$((idx + 1))
        echo "- ${nodeid} (${seconds}s) - Mitigation: ${suggestion}"
      done
    else
      echo "No duration data captured."
    fi
  } > "$SLOW_CANDIDATES"

  rm -f "$DURATIONS_CSV"

  echo ""
  echo "Profile reports saved to:"
  echo "  ${PROFILE_TXT#$REPO_ROOT/}"
  echo "  ${SLOW_CANDIDATES#$REPO_ROOT/}"
fi

# ==============================================================================
# Print summary
# ==============================================================================
echo ""
echo "============================================================="
echo "Test Run Summary"
echo "============================================================="
echo "Duration:         ${DURATION}s"
echo "Main workers:     $WORKERS_EFFECTIVE"
echo "Serial workers:   $SERIAL_WORKERS_EFFECTIVE"
echo "Profile:          $PROFILE_MODE"
echo "Main lane:        ${MAIN_STATUS} ${MAIN_STATUS_NOTE}"
echo "Serial lane:      ${SERIAL_STATUS} ${SERIAL_STATUS_NOTE}"
if [[ "$CHECKPOINT_ENABLED" -eq 1 ]]; then
  echo "Checkpoint main:  $CHECKPOINT_FILE_MAIN"
  echo "Checkpoint serial:$CHECKPOINT_FILE_SERIAL"
else
  echo "Checkpoint:       disabled"
fi
if [[ "$FAILURES_COUNT" -gt 0 ]]; then
  echo "Failures list:    $FAILURES_FILE (${FAILURES_COUNT})"
else
  echo "Failures list:    $FAILURES_FILE (none)"
fi
echo "Run log:          $RUN_LOG_FILE"
echo "============================================================="
echo ""
if [[ "$CHECKPOINT_ENABLED" -eq 1 ]]; then
  echo "Tip: rerun main with --resume-main-from $CHECKPOINT_FILE_MAIN to skip already PASSED tests."
  echo "Tip: rerun serial with --resume-serial-from $CHECKPOINT_FILE_SERIAL to skip already PASSED tests."
fi
if [[ "$FAILURES_COUNT" -gt 0 ]]; then
  printf 'Tip: rerun only failures with: bash tools/test/run.sh -q $(cat %s)\n' "$FAILURES_FILE"
fi
if [[ "$FINAL_EXIT_CODE" -eq 124 ]]; then
  echo ""
  echo "Timeout detected (exit 124)."
  if [[ "$CHECKPOINT_ENABLED" -eq 1 ]]; then
    echo "Checkpoint main: $CHECKPOINT_FILE_MAIN"
    echo "Checkpoint serial: $CHECKPOINT_FILE_SERIAL"
  fi
  echo "Failures list: $FAILURES_FILE"
  if [[ "$CHECKPOINT_ENABLED" -eq 1 ]]; then
    printf 'Retry main: bash tools/test/run.sh -q --resume-main-from %s $(cat %s)\n' "$CHECKPOINT_FILE_MAIN" "$FAILURES_FILE"
    printf 'Retry serial: bash tools/test/run.sh -q --resume-serial-from %s $(cat %s)\n' "$CHECKPOINT_FILE_SERIAL" "$FAILURES_FILE"
  else
    printf 'Retry: bash tools/test/run.sh -q $(cat %s)\n' "$FAILURES_FILE"
  fi
fi
echo ""

exit "$FINAL_EXIT_CODE"
