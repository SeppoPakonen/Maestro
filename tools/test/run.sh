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

# Always try to install pytest-xdist and pytest-timeout (in requirements-dev.txt)
EXTRA_REQS=("pytest-xdist" "pytest-timeout")

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
TEST_TIMEOUT="${MAESTRO_TEST_TIMEOUT:-}"
PROFILE_REPORT=0
SAVE_PROFILE_REPORT=0
SKIPPED_ONLY=0
SLOWEST_FIRST=1
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
  --profile-report        Run tests and show top 25 slowest (default: 10)
  --save-profile-report   Run tests and save ALL timings to docs/workflows/v3/reports/test_timing_latest.txt
  --resume-from FILE      Resume from checkpoint, skipping previously PASSED tests
  --checkpoint FILE       Override checkpoint file path (default: auto-generated in /tmp)
  --skiplist FILE         File containing test patterns to skip (default: tools/test/skiplist.txt)
                          Use --skiplist "" to disable skipping
  --skipped               Run ONLY the tests listed in skiplist (inverse of default behavior)
  --timeout SECONDS       Kill tests that run longer than SECONDS (requires pytest-timeout)

Environment variables:
  MAESTRO_TEST_JOBS       Default worker count (overridden by -j/--jobs)
  MAESTRO_TEST_PROFILE    Default speed profile (overridden by --profile)
  MAESTRO_TEST_RESUME_FROM Default resume checkpoint file
  MAESTRO_TEST_CHECKPOINT  Default checkpoint file path
  MAESTRO_TEST_SKIPLIST    Default skiplist file path
  MAESTRO_TEST_TIMEOUT     Default test timeout in seconds

Examples:
  # Run tests with default parallelism
  $0

  # Run only fast tests with 4 workers
  $0 --profile fast -j 4

  # Run tests, fail fast on first error
  $0 -x --maxfail=1

  # Resume from a previous checkpoint
  $0 --resume-from /tmp/maestro_pytest_checkpoint_20231215_120000_12345.txt

  # Run tests and show top 25 slowest (instead of default 10)
  $0 --profile-report

  # View saved timing report (without running tests)
  cat docs/workflows/v3/reports/test_timing_latest.txt

  # Use custom skiplist
  $0 --skiplist my_skiplist.txt

  # Disable skiplist (run all tests including normally-skipped ones)
  $0 --skiplist ""

  # Kill tests that run longer than 5 seconds
  $0 --timeout 5

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
    --save-profile-report)
      SAVE_PROFILE_REPORT=1
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
    --skipped)
      SKIPPED_ONLY=1
      shift
      ;;
    --timeout)
      if [[ -z "${2:-}" ]]; then
        echo "ERROR: --timeout requires a number of seconds" >&2
        exit 1
      fi
      TEST_TIMEOUT="$2"
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
# Setup profiling output file location
# ==============================================================================
# Always set the path for reading timing data (for slowest-first ordering)
# Only write to it if --save-profile-report is used
PROFILE_OUTPUT_FILE="$REPO_ROOT/docs/workflows/v3/reports/test_timing_latest.txt"

# ==============================================================================
# Determine pytest base arguments
# ==============================================================================
PYTEST_BASE_ARGS=()

# Enable colored output
PYTEST_BASE_ARGS+=(--color=yes)

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

# ==============================================================================
# Speed profile filtering using timing data
# ==============================================================================
# If timing data exists, use actual performance. Otherwise fall back to markers.
# Don't use timing data when generating a new profile report (--save-profile-report)
TIMING_BASED_FILTER=0
if [[ "$PROFILE" != "all" ]] && [[ -f "$PROFILE_OUTPUT_FILE" ]] && [[ "$SAVE_PROFILE_REPORT" -eq 0 ]]; then
  # Parse timing data to build test lists based on actual performance
  FAST_TESTS=$(mktemp)
  MEDIUM_TESTS=$(mktemp)
  SLOW_TESTS=$(mktemp)
  ALL_TIMED_TESTS=$(mktemp)

  # Extract test nodeids and durations from timing file
  # Format: "0.07s call     tests/test_foo.py::TestBar::test_baz"
  grep -E '^\s*[0-9]+\.[0-9]+s\s+(call|setup|teardown)\s+' "$PROFILE_OUTPUT_FILE" 2>/dev/null | while read -r line; do
    duration=$(echo "$line" | awk '{print $1}' | sed 's/s$//')
    nodeid=$(echo "$line" | awk '{$1=$2=""; print $0}' | sed 's/^ *//')

    # Store duration and nodeid for sorting
    echo "$duration $nodeid" >> "$ALL_TIMED_TESTS"

    # Classify by duration
    if awk "BEGIN {exit !($duration < 0.1)}"; then
      echo "$duration $nodeid" >> "$FAST_TESTS"
    elif awk "BEGIN {exit !($duration < 1.0)}"; then
      echo "$duration $nodeid" >> "$MEDIUM_TESTS"
    else
      echo "$duration $nodeid" >> "$SLOW_TESTS"
    fi
  done

  # Apply profile filter based on timing data
  case "$PROFILE" in
    fast)
      if [[ -s "$FAST_TESTS" ]]; then
        echo "Using timing data: running $(wc -l < "$FAST_TESTS") fast tests (<0.1s)" >&2
        if [[ "$SLOWEST_FIRST" -eq 1 ]]; then
          echo "Ordering: slowest first" >&2
          # Sort by duration descending, extract nodeid
          sort -rn "$FAST_TESTS" | while read -r duration nodeid; do
            PYTEST_BASE_ARGS+=("$nodeid")
          done
        else
          while read -r duration nodeid; do
            PYTEST_BASE_ARGS+=("$nodeid")
          done < "$FAST_TESTS"
        fi
        TIMING_BASED_FILTER=1
      fi
      ;;
    medium)
      if [[ -s "$FAST_TESTS" ]] || [[ -s "$MEDIUM_TESTS" ]]; then
        fast_count=$(wc -l < "$FAST_TESTS" 2>/dev/null || echo 0)
        medium_count=$(wc -l < "$MEDIUM_TESTS" 2>/dev/null || echo 0)
        total=$((fast_count + medium_count))
        echo "Using timing data: running $total fast+medium tests (<1.0s)" >&2
        if [[ "$SLOWEST_FIRST" -eq 1 ]]; then
          echo "Ordering: slowest first" >&2
          # Combine and sort by duration descending
          cat "$FAST_TESTS" "$MEDIUM_TESTS" | sort -rn | while read -r duration nodeid; do
            PYTEST_BASE_ARGS+=("$nodeid")
          done
        else
          while read -r duration nodeid; do
            PYTEST_BASE_ARGS+=("$nodeid")
          done < "$FAST_TESTS"
          while read -r duration nodeid; do
            PYTEST_BASE_ARGS+=("$nodeid")
          done < "$MEDIUM_TESTS"
        fi
        TIMING_BASED_FILTER=1
      fi
      ;;
    slow)
      if [[ -s "$SLOW_TESTS" ]]; then
        echo "Using timing data: running $(wc -l < "$SLOW_TESTS") slow tests (>1.0s)" >&2
        if [[ "$SLOWEST_FIRST" -eq 1 ]]; then
          echo "Ordering: slowest first" >&2
          sort -rn "$SLOW_TESTS" | while read -r duration nodeid; do
            PYTEST_BASE_ARGS+=("$nodeid")
          done
        else
          while read -r duration nodeid; do
            PYTEST_BASE_ARGS+=("$nodeid")
          done < "$SLOW_TESTS"
        fi
        TIMING_BASED_FILTER=1
      fi
      ;;
  esac

  rm -f "$FAST_TESTS" "$MEDIUM_TESTS" "$SLOW_TESTS" "$ALL_TIMED_TESTS"
fi

# Fall back to marker-based filtering if no timing data available
if [[ "$TIMING_BASED_FILTER" -eq 0 ]]; then
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

      # If timing data exists and slowest-first is enabled, order all tests by duration
      # Only apply if timing file has actual test data
      # Don't use timing data when generating a new profile report
      if [[ "$SLOWEST_FIRST" -eq 1 ]] && [[ -f "$PROFILE_OUTPUT_FILE" ]] && [[ "$SAVE_PROFILE_REPORT" -eq 0 ]]; then
        # Check if timing file has actual test timing data
        if grep -qE '^\s*[0-9]+\.[0-9]+s\s+(call|setup|teardown)' "$PROFILE_OUTPUT_FILE" 2>/dev/null; then
          ALL_TESTS_SORTED=$(mktemp)
          # Extract all test nodeids with durations and sort slowest first
          grep -E '^\s*[0-9]+\.[0-9]+s\s+(call|setup|teardown)\s+' "$PROFILE_OUTPUT_FILE" 2>/dev/null | \
            awk '{duration=$1; gsub(/s$/,"",duration); $1=$2=""; nodeid=$0; gsub(/^ */,"",nodeid); print duration, nodeid}' | \
            sort -rn > "$ALL_TESTS_SORTED"

          if [[ -s "$ALL_TESTS_SORTED" ]]; then
            echo "Ordering: slowest first ($(wc -l < "$ALL_TESTS_SORTED") tests)" >&2
            while read -r duration nodeid; do
              PYTEST_BASE_ARGS+=("$nodeid")
            done < "$ALL_TESTS_SORTED"
          fi
          rm -f "$ALL_TESTS_SORTED"
        fi
      fi
      ;;
    *)
      echo "ERROR: Invalid profile '$PROFILE'. Must be: fast, medium, slow, or all" >&2
      exit 1
      ;;
  esac
fi

# Always exclude legacy tests (unless running skipped tests)
if [[ "$SKIPPED_ONLY" -eq 0 ]]; then
  if [[ "$TIMING_BASED_FILTER" -eq 0 ]] && [[ "$PROFILE" != "all" ]]; then
    # Marker-based filtering already includes "not legacy"
    :
  else
    PYTEST_BASE_ARGS+=(-m "not legacy")
  fi
fi

# Profiling report - always enabled to track test performance
if [[ "$SAVE_PROFILE_REPORT" -eq 1 ]]; then
  # When saving profile report, get ALL test durations for complete timing database
  PYTEST_BASE_ARGS+=(--durations=0)
elif [[ "$PROFILE_REPORT" -eq 1 ]]; then
  # Show more durations when explicitly requested
  PYTEST_BASE_ARGS+=(--durations=25)
else
  # Default: show top 10 to keep output clean but still track performance
  PYTEST_BASE_ARGS+=(--durations=10)
fi

# ==============================================================================
# Process skiplist file
# ==============================================================================
if [[ -n "$SKIPLIST" ]] && [[ -f "$SKIPLIST" ]]; then
  if [[ "$SKIPPED_ONLY" -eq 1 ]]; then
    # --skipped mode: run ONLY the tests in skiplist
    echo "Running ONLY skipped tests from: $SKIPLIST" >&2
    while IFS= read -r line || [[ -n "$line" ]]; do
      # Skip empty lines and comments
      [[ -z "$line" ]] && continue
      [[ "$line" =~ ^[[:space:]]*# ]] && continue

      # Add pattern as positional argument to run only these tests
      PYTEST_BASE_ARGS+=("$line")
    done < "$SKIPLIST"
  else
    # Normal mode: skip tests in skiplist
    while IFS= read -r line || [[ -n "$line" ]]; do
      # Skip empty lines and comments
      [[ -z "$line" ]] && continue
      [[ "$line" =~ ^[[:space:]]*# ]] && continue

      # Add --ignore for each pattern
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
  # Check if pytest-timeout is available
  if ! "$VENV_PY" -c "import pytest_timeout" 2>/dev/null; then
    echo "WARNING: pytest-timeout not installed, timeout will not be enforced" >&2
    echo "Install with: pip install pytest-timeout" >&2
  else
    PYTEST_BASE_ARGS+=(--timeout="$TEST_TIMEOUT")
    PYTEST_BASE_ARGS+=(--timeout-method=thread)
  fi
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

# ==============================================================================
# Print test run configuration
# ==============================================================================
echo "============================================================="
echo "Maestro Test Runner Configuration"
echo "============================================================="
echo "Profile:          $PROFILE"
echo "Workers:          $JOBS"
echo "Verbose:          $([ "$VERBOSE" -eq 1 ] && echo "yes" || echo "no")"
if [[ -n "$SKIPLIST" ]] && [[ -f "$SKIPLIST" ]]; then
  if [[ "$SKIPPED_ONLY" -eq 1 ]]; then
    echo "Skiplist:         $SKIPLIST (running ONLY skipped tests)"
  else
    echo "Skiplist:         $SKIPLIST"
  fi
else
  echo "Skiplist:         disabled"
fi
if [[ "$SLOWEST_FIRST" -eq 1 ]] && [[ -f "$PROFILE_OUTPUT_FILE" ]] && [[ "$SAVE_PROFILE_REPORT" -eq 0 ]]; then
  if grep -qE '^\s*[0-9]+\.[0-9]+s\s+(call|setup|teardown)' "$PROFILE_OUTPUT_FILE" 2>/dev/null; then
    echo "Test ordering:    slowest-first (timing data available)"
  else
    echo "Test ordering:    default (no timing data)"
  fi
else
  if [[ "$SAVE_PROFILE_REPORT" -eq 1 ]]; then
    echo "Test ordering:    default (generating new profile)"
  else
    echo "Test ordering:    default"
  fi
fi
if [[ -n "$TEST_TIMEOUT" ]]; then
  echo "Timeout:          ${TEST_TIMEOUT}s per test"
fi
if [[ -n "$RESUME_FROM" ]]; then
  echo "Resume mode:      enabled (from $RESUME_FROM)"
fi
if [[ "$SAVE_PROFILE_REPORT" -eq 1 ]]; then
  echo "Save profile:     yes (to ${PROFILE_OUTPUT_FILE#$REPO_ROOT/})"
elif [[ "$PROFILE_REPORT" -eq 1 ]]; then
  echo "Profile report:   yes (25 slowest tests)"
else
  echo "Profile report:   default (10 slowest tests)"
fi
echo "============================================================="
echo ""

# Capture start time
START_TIME=$(date +%s)

# Run pytest with plugin
set +e
if [[ "$SAVE_PROFILE_REPORT" -eq 1 ]]; then
  # Capture output for profiling
  TEMP_OUTPUT=$(mktemp)
  "$VENV_PY" -m pytest \
    -p tools.test.pytest_checkpoint_plugin \
    "${PYTEST_BASE_ARGS[@]}" \
    "${PYTEST_ARGS[@]}" 2>&1 | tee "$TEMP_OUTPUT"
  EXIT_CODE=${PIPEFAIL[0]:-$?}
else
  # Normal execution
  "$VENV_PY" -m pytest \
    -p tools.test.pytest_checkpoint_plugin \
    "${PYTEST_BASE_ARGS[@]}" \
    "${PYTEST_ARGS[@]}"
  EXIT_CODE=$?
fi
set -e

# Capture end time
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# ==============================================================================
# Process profiling output
# ==============================================================================
if [[ "$SAVE_PROFILE_REPORT" -eq 1 ]] && [[ -f "$TEMP_OUTPUT" ]]; then
  {
    echo "# Test Timing Report"
    echo "# Generated: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "# Command: $0 ${BASH_ARGV[@]}"
    echo "# Duration: ${DURATION}s"
    echo "# Workers: $JOBS"
    echo "# Profile: $PROFILE"
    echo ""

    # Extract all durations section and convert to relative paths
    if grep -q "slowest.*durations\|=.* durations =.*" "$TEMP_OUTPUT"; then
      # Extract the durations section (works for both "slowest N durations" and "= durations =")
      sed -n '/slowest.*durations\|=.* durations =.*/,/^$/p' "$TEMP_OUTPUT" | \
        sed "s|$REPO_ROOT/||g"

      echo ""
      echo "# Warnings"

      # Check for slow tests and generate warnings
      SLOW_COUNT=$(sed -n '/slowest.*durations\|=.* durations =.*/,/^$/p' "$TEMP_OUTPUT" | \
        grep -E '^\s*[0-9]+\.[0-9]+s' | \
        awk '$1 ~ /^[0-9]+\.[0-9]+s$/ {gsub(/s$/,"",$1); if ($1 > 1.0) print}' | \
        wc -l)

      if [[ "$SLOW_COUNT" -gt 0 ]]; then
        echo "WARNING: Found $SLOW_COUNT tests slower than 1.0s"
        echo ""
        echo "Slow tests (>1.0s):"
        sed -n '/slowest.*durations\|=.* durations =.*/,/^$/p' "$TEMP_OUTPUT" | \
          grep -E '^\s*[0-9]+\.[0-9]+s' | \
          awk '$1 ~ /^[0-9]+\.[0-9]+s$/ {gsub(/s$/,"",$1); if ($1 > 1.0) print}' | \
          sed "s|$REPO_ROOT/||g" | \
          sed 's/^/  /'
      else
        echo "All tests completed in <1.0s"
      fi
    else
      echo "No timing data found in output"
    fi
  } > "$PROFILE_OUTPUT_FILE"

  rm -f "$TEMP_OUTPUT"

  echo ""
  echo "Profiling report saved to: ${PROFILE_OUTPUT_FILE#$REPO_ROOT/}"
fi

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
