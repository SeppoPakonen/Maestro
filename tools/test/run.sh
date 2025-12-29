#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Maestro Test Runner
# ==============================================================================
# Current behavior (as of this version):
# - Creates/uses a Python virtual environment at REPO_ROOT/.venv
# - Installs pytest and pytest-xdist from requirements-dev.txt
# - Supports parallelism via pytest-xdist with configurable worker count
# - Supports speed profiles: fast, medium, slow, all
# - Writes checkpoint files to /tmp containing PASSED test nodeids
# - Supports resume mode to skip previously PASSED tests
# - Provides profiling output for slow tests
# - Passes through additional pytest arguments
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv"

# ==============================================================================
# Git lock check
# ==============================================================================
if [[ -f "$REPO_ROOT/.git/index.lock" ]]; then
  echo "ERROR: Git index lock detected at $REPO_ROOT/.git/index.lock" >&2
  echo "Resolve any active git process, then remove the lock manually." >&2
  exit 2
fi

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

# Always try to install pytest-xdist (it's in requirements-dev.txt now)
EXTRA_REQS=("pytest-xdist")

PIP_DISABLE_PIP_VERSION_CHECK=1 "$VENV_PY" -m pip install -q "$PYTEST_REQ" "${EXTRA_REQS[@]}"

# ==============================================================================
# Parse command-line arguments
# ==============================================================================
VERBOSE=0
JOBS=""
PROFILE="${MAESTRO_TEST_PROFILE:-all}"
RESUME_FROM="${MAESTRO_TEST_RESUME_FROM:-}"
CHECKPOINT_FILE="${MAESTRO_TEST_CHECKPOINT:-}"
SKIPLIST="${MAESTRO_TEST_SKIPLIST:-$SCRIPT_DIR/skiplist.txt}"
PROFILE_REPORT=0
PYTEST_ARGS=()

show_help() {
  cat <<EOF
Usage: $0 [OPTIONS] [PYTEST_ARGS...]

Options:
  -h, --help              Show this help message
  -v, --verbose           Enable verbose pytest output (-vv)
  -j, --jobs N            Number of parallel workers (default: cpu_count-1)
                          Set to 1 to disable parallelism
  --profile PROFILE       Speed profile: fast, medium, slow, all (default: all)
                          - fast: only fast-marked tests
                          - medium: fast + medium-marked tests
                          - slow: only slow-marked tests
                          - all: no speed filtering (still excludes legacy by default)
  --profile-report        Show timing report for slowest 25 tests
  --resume-from FILE      Resume from checkpoint, skipping previously PASSED tests
  --checkpoint FILE       Override checkpoint file path (default: auto-generated in /tmp)
  --skiplist FILE         File containing test patterns to skip (default: tools/test/skiplist.txt)
                          Use --skiplist "" to disable skipping

Environment variables:
  MAESTRO_TEST_JOBS       Default worker count (overridden by -j/--jobs)
  MAESTRO_TEST_PROFILE    Default speed profile (overridden by --profile)
  MAESTRO_TEST_RESUME_FROM Default resume checkpoint file
  MAESTRO_TEST_CHECKPOINT  Default checkpoint file path
  MAESTRO_TEST_SKIPLIST    Default skiplist file path

Examples:
  # Run tests with default parallelism
  $0

  # Run only fast tests with 4 workers
  $0 --profile fast -j 4

  # Run tests, fail fast on first error
  $0 -x --maxfail=1

  # Resume from a previous checkpoint
  $0 --resume-from /tmp/maestro_pytest_checkpoint_20231215_120000_12345.txt

  # Show profiling report
  $0 --profile-report

  # Use custom skiplist
  $0 --skiplist my_skiplist.txt

  # Disable skiplist (run all tests including normally-skipped ones)
  $0 --skiplist ""

All additional arguments are passed directly to pytest.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      show_help
      exit 0
      ;;
    -v|--verbose)
      VERBOSE=1
      shift
      ;;
    -j|--jobs)
      if [[ -z "${2:-}" ]]; then
        echo "ERROR: --jobs requires a number argument" >&2
        exit 1
      fi
      JOBS="$2"
      shift 2
      ;;
    --profile)
      if [[ -z "${2:-}" ]]; then
        echo "ERROR: --profile requires an argument (fast|medium|slow|all)" >&2
        exit 1
      fi
      PROFILE="$2"
      shift 2
      ;;
    --profile-report)
      PROFILE_REPORT=1
      shift
      ;;
    --resume-from)
      if [[ -z "${2:-}" ]]; then
        echo "ERROR: --resume-from requires a file path argument" >&2
        exit 1
      fi
      RESUME_FROM="$2"
      shift 2
      ;;
    --checkpoint)
      if [[ -z "${2:-}" ]]; then
        echo "ERROR: --checkpoint requires a file path argument" >&2
        exit 1
      fi
      CHECKPOINT_FILE="$2"
      shift 2
      ;;
    --skiplist)
      if [[ -z "${2+x}" ]]; then
        echo "ERROR: --skiplist requires a file path argument (use \"\" to disable)" >&2
        exit 1
      fi
      SKIPLIST="$2"
      shift 2
      ;;
    *)
      PYTEST_ARGS+=("$1")
      shift
      ;;
  esac
done

# ==============================================================================
# Determine worker count for parallelism
# ==============================================================================
if [[ -z "$JOBS" ]]; then
  if [[ -n "${MAESTRO_TEST_JOBS:-}" ]]; then
    JOBS="$MAESTRO_TEST_JOBS"
  else
    # Compute default: max(1, cpu_count - 1)
    CPU_COUNT=$("$VENV_PY" -c 'import os; print(os.cpu_count() or 1)' 2>/dev/null || echo "1")
    JOBS=$((CPU_COUNT > 1 ? CPU_COUNT - 1 : 1))
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
# Determine pytest base arguments
# ==============================================================================
PYTEST_BASE_ARGS=()

# Verbosity
if [[ "$VERBOSE" -eq 1 ]]; then
  PYTEST_BASE_ARGS+=(-vv)
else
  PYTEST_BASE_ARGS+=(-q)
fi

# Parallelism (only if xdist available and jobs > 1)
if [[ "$XDIST_AVAILABLE" -eq 1 ]] && [[ "$JOBS" -gt 1 ]]; then
  PYTEST_BASE_ARGS+=(-n "$JOBS")
elif [[ "$JOBS" -gt 1 ]] && [[ "$XDIST_AVAILABLE" -eq 0 ]]; then
  echo "Note: xdist not available; running serial" >&2
fi

# Speed profile filtering
# Note: pytest.ini already has default addopts with "-m 'not legacy and not slow'"
# We need to override this for different profiles
case "$PROFILE" in
  fast)
    PYTEST_BASE_ARGS+=(-m "fast and not legacy")
    ;;
  medium)
    PYTEST_BASE_ARGS+=(-m "(fast or medium) and not legacy")
    ;;
  slow)
    PYTEST_BASE_ARGS+=(-m "slow and not legacy")
    ;;
  all)
    # Don't add speed filtering, but still exclude legacy
    PYTEST_BASE_ARGS+=(-m "not legacy")
    ;;
  *)
    echo "ERROR: Invalid profile '$PROFILE'. Must be: fast, medium, slow, or all" >&2
    exit 1
    ;;
esac

# Profiling report
if [[ "$PROFILE_REPORT" -eq 1 ]]; then
  PYTEST_BASE_ARGS+=(--durations=25)
fi

# ==============================================================================
# Process skiplist file
# ==============================================================================
if [[ -n "$SKIPLIST" ]] && [[ -f "$SKIPLIST" ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    # Skip empty lines and comments
    [[ -z "$line" ]] && continue
    [[ "$line" =~ ^[[:space:]]*# ]] && continue

    # Add --ignore for each pattern
    PYTEST_BASE_ARGS+=(--ignore="$line")
  done < "$SKIPLIST"
elif [[ -n "$SKIPLIST" ]]; then
  echo "WARNING: Skiplist file not found: $SKIPLIST" >&2
  echo "Continuing without skiplist..." >&2
fi

# ==============================================================================
# Setup checkpoint file
# ==============================================================================
if [[ -z "$CHECKPOINT_FILE" ]]; then
  # Auto-generate checkpoint filename
  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
  PID=$$
  CHECKPOINT_FILE="/tmp/maestro_pytest_checkpoint_${TIMESTAMP}_${PID}.txt"
fi

# ==============================================================================
# Setup resume mode
# ==============================================================================
if [[ -n "$RESUME_FROM" ]]; then
  if [[ ! -f "$RESUME_FROM" ]]; then
    echo "ERROR: Resume checkpoint file not found: $RESUME_FROM" >&2
    exit 1
  fi
  echo "Resume enabled: using checkpoint $RESUME_FROM"
  export MAESTRO_TEST_RESUME_FROM="$RESUME_FROM"
fi

# ==============================================================================
# Export checkpoint path for plugin
# ==============================================================================
export MAESTRO_TEST_CHECKPOINT="$CHECKPOINT_FILE"

# ==============================================================================
# Load checkpoint plugin and run pytest
# ==============================================================================
PLUGIN_PATH="$SCRIPT_DIR/pytest_checkpoint_plugin.py"
if [[ ! -f "$PLUGIN_PATH" ]]; then
  echo "ERROR: Checkpoint plugin not found at $PLUGIN_PATH" >&2
  exit 1
fi

# Add plugin to PYTHONPATH and load it
export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"

cd "$REPO_ROOT"

# Capture start time
START_TIME=$(date +%s)

# Run pytest with plugin
set +e
"$VENV_PY" -m pytest \
  -p tools.test.pytest_checkpoint_plugin \
  "${PYTEST_BASE_ARGS[@]}" \
  "${PYTEST_ARGS[@]}"
EXIT_CODE=$?
set -e

# Capture end time
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# ==============================================================================
# Print summary
# ==============================================================================
echo ""
echo "============================================================="
echo "Test Run Summary"
echo "============================================================="
echo "Duration:         ${DURATION}s"
echo "Workers:          $JOBS"
echo "Profile:          $PROFILE"
echo "Checkpoint:       $CHECKPOINT_FILE"
echo "============================================================="
echo ""
echo "Tip: Re-run with --resume-from $CHECKPOINT_FILE to skip PASSED tests."
echo ""

exit $EXIT_CODE
