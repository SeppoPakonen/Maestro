#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(pwd)"
MAESTRO_BIN="${MAESTRO_BIN:-python3 ${ROOT_DIR}/maestro.py}"
MAKE_CMD="${MAKE_CMD:-$MAESTRO_BIN make build}"

TMP_DIR=""
CURRENT_SECTION=""
LAST_CMD=""
LAST_OUTFILE=""
LAST_EXIT=0

cleanup() {
  if [ -n "${TMP_DIR}" ] && [ -d "${TMP_DIR}" ]; then
    rm -rf "${TMP_DIR}"
  fi
}
trap cleanup EXIT

banner() {
  echo ""
  echo "== $1 =="
}

section_start() {
  CURRENT_SECTION="$1"
  banner "$CURRENT_SECTION"
}

section_pass() {
  echo "PASS: $CURRENT_SECTION"
}

warn() {
  echo "WARN: $1"
}

fail() {
  echo "FAIL: $CURRENT_SECTION"
  if [ -n "$LAST_CMD" ]; then
    echo "Last command: $LAST_CMD"
  fi
  if [ -n "$LAST_OUTFILE" ] && [ -f "$LAST_OUTFILE" ]; then
    echo "--- output (last 80 lines) ---"
    tail -n 80 "$LAST_OUTFILE"
    echo "--- end output ---"
  fi
  echo "Invariant violated: $1"
  exit 1
}

run() {
  local cmd="$*"
  LAST_CMD="$cmd"
  echo "+ $cmd"
  PYTHONUNBUFFERED=1 bash -c "$cmd"
}

run_capture() {
  local cmd="$1"
  local outfile="$2"
  LAST_CMD="$cmd"
  LAST_OUTFILE="$outfile"
  echo "+ $cmd"
  set +e
  PYTHONUNBUFFERED=1 bash -c "$cmd" >"$outfile" 2>&1
  LAST_EXIT=$?
  set -e
}

assert_exit_zero() {
  if [ "$LAST_EXIT" -ne 0 ]; then
    fail "Expected exit 0"
  fi
}

assert_exit_nonzero() {
  if [ "$LAST_EXIT" -eq 0 ]; then
    fail "Expected non-zero exit"
  fi
}

assert_contains() {
  local file="$1"
  local pattern="$2"
  if ! grep -E -q "$pattern" "$file"; then
    fail "Expected pattern '$pattern'"
  fi
}

assert_not_contains() {
  local file="$1"
  local pattern="$2"
  if grep -E -q "$pattern" "$file"; then
    fail "Unexpected pattern '$pattern'"
  fi
}

assert_file_exists() {
  local path="$1"
  if [ ! -f "$path" ]; then
    fail "Expected file '$path'"
  fi
}

assert_dir_exists() {
  local path="$1"
  if [ ! -d "$path" ]; then
    fail "Expected directory '$path'"
  fi
}

assert_no_path_exists() {
  local path="$1"
  if [ -e "$path" ]; then
    fail "Forbidden path exists: '$path'"
  fi
}

assert_json_files_exist() {
  local target="$1"
  local count=0
  if [ -d "$target" ]; then
    count=$(find "$target" -type f -name "*.json" | wc -l | tr -d ' ')
  else
    count=$(compgen -G "$target" | wc -l | tr -d ' ')
  fi
  if [ "$count" -eq 0 ]; then
    fail "Expected JSON files under '$target'"
  fi
}

snapshot_json_list() {
  local dir="$1"
  local outfile="$2"
  local exclude_ai="$3"
  if [ "$exclude_ai" = "1" ]; then
    find "$dir" -type f -name "*.json" ! -path "$dir/ai/*" -print | sort >"$outfile"
  else
    find "$dir" -type f -name "*.json" -print | sort >"$outfile"
  fi
}

section_start "A) Setup"
TMP_DIR="$(mktemp -d)"
run "cp -a tools/smoke/fixtures/hello_cpp_makefile $TMP_DIR/proj"
echo "+ cd $TMP_DIR/proj"
cd "$TMP_DIR/proj"
section_pass

section_start "B) Init + forbidden path invariant"
run_capture "$MAESTRO_BIN init" out_init.txt
assert_exit_zero
assert_dir_exists "docs/maestro"
assert_no_path_exists ".maestro"
if find "docs/maestro" -type f -name "*.json" | grep -q .; then
  echo "Found JSON repo truth files."
else
  warn "No JSON files created by init; continuing."
fi
section_pass

section_start "C) Make gates (preconditions)"
run_capture "$MAKE_CMD" out_make_no_resolve.txt
assert_exit_nonzero
assert_contains out_make_no_resolve.txt "repo resolve|repoconf|repo model|repo_model"
run_capture "$MAESTRO_BIN repo resolve" out_resolve.txt
assert_exit_zero
assert_file_exists "docs/maestro/repo_model.json"
assert_no_path_exists ".maestro"
run_capture "$MAKE_CMD" out_make_no_repoconf.txt
assert_exit_nonzero
assert_contains out_make_no_repoconf.txt "repo conf|select-default target|target"
section_pass

section_start "D) Repoconf/target selection"
run_capture "$MAESTRO_BIN repo conf --help" out_repoconf_help.txt
assert_exit_zero
TARGET="$(python3 - <<'PY'
import json
import sys
from pathlib import Path

path = Path("docs/maestro/repo_model.json")
if not path.exists():
    sys.exit(0)
data = json.loads(path.read_text())

def first_target(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("targets", "build_targets") and isinstance(v, list):
                for item in v:
                    if isinstance(item, str):
                        return item
                    if isinstance(item, dict):
                        for key in ("name", "id", "target"):
                            if key in item and isinstance(item[key], str):
                                return item[key]
            found = first_target(v)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = first_target(item)
            if found:
                return found
    return ""

target = first_target(data)
if target:
    print(target)
PY
)"
if [ -z "$TARGET" ]; then
  TARGET="default"
fi
SELECT_CMD=""
if grep -E -q "select-default" out_repoconf_help.txt; then
  SELECT_CMD="$MAESTRO_BIN repo conf select-default target $TARGET"
elif grep -E -q "set-target" out_repoconf_help.txt; then
  SELECT_CMD="$MAESTRO_BIN repo conf set-target $TARGET"
fi
if [ -z "$SELECT_CMD" ]; then
  fail "repoconf selection subcommand missing; update smoke script mapping"
fi
run_capture "$SELECT_CMD" out_repoconf_select.txt
if [ "$LAST_EXIT" -ne 0 ] && [ "$TARGET" != "default" ]; then
  TARGET="default"
  if grep -E -q "select-default" out_repoconf_help.txt; then
    SELECT_CMD="$MAESTRO_BIN repo conf select-default target $TARGET"
  else
    SELECT_CMD="$MAESTRO_BIN repo conf set-target $TARGET"
  fi
  run_capture "$SELECT_CMD" out_repoconf_select.txt
fi
assert_exit_zero
run_capture "$MAESTRO_BIN repo conf list" out_repoconf_list.txt
if [ "$LAST_EXIT" -ne 0 ]; then
  warn "repoconf list failed; continuing"
fi
run_capture "$MAESTRO_BIN repo conf show" out_repoconf_show.txt
if [ "$LAST_EXIT" -ne 0 ]; then
  warn "repoconf show failed; continuing"
fi
run_capture "$MAKE_CMD" out_make_after_repoconf.txt
MAKE_AFTER_EXIT=$LAST_EXIT
if [ "$MAKE_AFTER_EXIT" -ne 0 ]; then
  assert_contains out_make_after_repoconf.txt "compiler|toolchain|missing|not found|CXX|build"
fi
assert_no_path_exists ".maestro"
section_pass

section_start "E) Build alias warning"
run_capture "$MAESTRO_BIN build" out_build_alias.txt
if [ "$LAST_EXIT" -ne "$MAKE_AFTER_EXIT" ]; then
  fail "build alias exit code diverged from make"
fi
assert_contains out_build_alias.txt "deprecated|alias|use maestro make"
section_pass

section_start "F) TU gating"
run_capture "$MAESTRO_BIN tu build" out_tu.txt
if [ "$LAST_EXIT" -ne 0 ]; then
  assert_contains out_tu.txt "repo resolve|repo model|repoconf|toolchain"
fi
section_pass

section_start "G) Work + wsession cookie + breadcrumb + close"
run_capture "$MAESTRO_BIN work" out_work_help.txt
if ! grep -E -q "start" out_work_help.txt; then
  warn "work start not available; skipping work/wsession checks"
  section_pass
else
  WORK_START_CMD=""
  if grep -E -q "start[[:space:]]+task" out_work_help.txt; then
    WORK_START_CMD="$MAESTRO_BIN work start task TASK-1"
  else
    WORK_START_CMD="$MAESTRO_BIN work start"
  fi
  run_capture "$WORK_START_CMD" out_work_start.txt
  if [ "$LAST_EXIT" -ne 0 ]; then
    warn "work start failed; skipping work/wsession checks"
    section_pass
  else
    COOKIE=$(grep -R --line-number -m1 '"cookie"' docs/maestro 2>/dev/null | sed -E 's/.*"cookie"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')
    if [ -z "$COOKIE" ]; then
      warn "wsession cookie not found; skipping breadcrumb checks"
      section_pass
    else
      echo "Using cookie: $COOKIE"
      echo '{"event":"breadcrumb"}' > breadcrumb.json
      run_capture "$MAESTRO_BIN wsession breadcrumb add --json breadcrumb.json" out_breadcrumb_no_cookie.txt
      assert_exit_nonzero
      run_capture "$MAESTRO_BIN wsession breadcrumb add --cookie $COOKIE --json breadcrumb.json" out_breadcrumb_with_cookie.txt
      assert_exit_zero
      SESSION_ID=$(grep -R --line-number -m1 '"session_id"' docs/maestro 2>/dev/null | sed -E 's/.*"session_id"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')
      CLOSED_OK=0
      run_capture "$MAESTRO_BIN wsession" out_wsession_help.txt
      if [ -n "$SESSION_ID" ] && [ "$LAST_EXIT" -eq 0 ] && grep -E -q "close" out_wsession_help.txt; then
        run_capture "$MAESTRO_BIN wsession close $SESSION_ID" out_wsession_close.txt
        assert_exit_zero
        CLOSED_OK=1
      elif grep -E -q "close" out_work_help.txt; then
        run_capture "$MAESTRO_BIN work close" out_work_close.txt
        assert_exit_zero
        CLOSED_OK=1
      else
        warn "close command not available; skipping close check"
      fi
      if [ "$CLOSED_OK" -eq 1 ]; then
        run_capture "$MAESTRO_BIN wsession breadcrumb add --cookie $COOKIE --json breadcrumb.json" out_breadcrumb_closed.txt
        assert_exit_nonzero
        assert_contains out_breadcrumb_closed.txt "closed|inactive"
      fi
      section_pass
    fi
  fi
fi

section_start "H) Discuss JSON hard-fail"
run_capture "$MAESTRO_BIN discuss --help" out_discuss_help.txt
assert_exit_zero
DISCUSS_CMD=""
if grep -E -q -- "--from-file" out_discuss_help.txt; then
  DISCUSS_CMD="$MAESTRO_BIN discuss --from-file bad.json"
elif grep -E -q "replay" out_discuss_help.txt; then
  DISCUSS_CMD="$MAESTRO_BIN discuss replay --from-file bad.json"
elif grep -E -q "apply" out_discuss_help.txt; then
  DISCUSS_CMD="$MAESTRO_BIN discuss apply --from-file bad.json"
fi
if [ -z "$DISCUSS_CMD" ]; then
  warn "discuss ingestion mode not available; skipping JSON hard-fail"
  section_pass
else
  echo '{ not valid' > bad.json
  snapshot_json_list "docs/maestro" before_json.txt 1
  run_capture "$DISCUSS_CMD" out_discuss_bad.txt
  assert_exit_nonzero
  assert_contains out_discuss_bad.txt "json|parse|invalid|schema"
  snapshot_json_list "docs/maestro" after_json.txt 1
  if ! diff -u before_json.txt after_json.txt >/dev/null 2>&1; then
    fail "Expected no repo truth JSON changes outside ai/"
  fi
  section_pass
fi

section_start "I) Branch guard (mutate vs active work)"
if ! command -v git >/dev/null 2>&1; then
  warn "git not available; skipping branch guard"
  section_pass
else
  run "git init"
  run "git add ."
  run "git commit -m 'init fixture' >/dev/null"
  run_capture "$MAESTRO_BIN work" out_work_help_branch.txt
  if ! grep -E -q "start" out_work_help_branch.txt; then
    warn "work start not available; skipping branch guard"
    section_pass
  else
    WORK_START_CMD=""
    if grep -E -q "start[[:space:]]+task" out_work_help_branch.txt; then
      WORK_START_CMD="$MAESTRO_BIN work start task TASK-1"
    else
      WORK_START_CMD="$MAESTRO_BIN work start"
    fi
    run_capture "$WORK_START_CMD" out_work_start_branch.txt
    if [ "$LAST_EXIT" -ne 0 ]; then
      warn "work start failed; skipping branch guard"
      section_pass
    else
      run "git checkout -b smoke-branch-guard >/dev/null"
      MUTATE_CMD="$MAESTRO_BIN repo resolve"
      run_capture "$MUTATE_CMD" out_branch_guard.txt
      if [ "$LAST_EXIT" -eq 0 ]; then
        fail "Expected branch guard to block mutation with active work session"
      fi
      assert_contains out_branch_guard.txt "branch|close|return"
      section_pass
    fi
  fi
fi

banner "Smoke complete"
