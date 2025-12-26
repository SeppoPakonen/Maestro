#!/usr/bin/env bash
set -euo pipefail

input_dir="docs/workflows/v2/runbooks/examples/proposed"
output_dir="docs/workflows/v3/reports"

mkdir -p "$output_dir"

raw_with_ex_tmp="$(mktemp)"
todo_tmp="$(mktemp)"

awk -v raw_with_ex="$raw_with_ex_tmp" -v todo_tmp="$todo_tmp" '
function trim(s){sub(/^[[:space:]]+/, "", s); sub(/[[:space:]]+$/, "", s); return s}
function normalize(s){gsub(/[[:space:]]+/, " ", s); return trim(s)}
function emit(cmd){cmd=normalize(cmd); if(cmd!=""){print cmd "\t" ex >> raw_with_ex}}
function emit_todo(line){line=normalize(line); if(line!=""){print line >> todo_tmp}}
FNR==1{
  ex="EX-??"
  if (match(FILENAME, /EX-[0-9][0-9]/)) {
    ex=substr(FILENAME, RSTART, RLENGTH)
  }
}
{
  original=$0
  if (index(original, "TODO_CMD:") > 0) {
    todo=original
    sub(/.*TODO_CMD:/, "", todo)
    sub(/#.*/, "", todo)
    emit_todo(todo)
  }

  line=original
  sub(/#.*/, "", line)
  if (line ~ /^[[:space:]]*$/) next

  if (line ~ /^[[:space:]]*run[[:space:]]+/) {
    sub(/^[[:space:]]*run[[:space:]]+/, "", line)
    emit(line)
    next
  }

  if (line ~ /^[[:space:]]*\+[[:space:]]*maestro[[:space:]]+/) {
    sub(/^[[:space:]]*\+[[:space:]]*/, "", line)
    emit(line)
    next
  }

  if (match(line, /maestro[[:space:]]+/)) {
    line=substr(line, RSTART)
    emit(line)
    next
  }
}
' "$input_dir"/*.sh

cut -f1 "$raw_with_ex_tmp" > "$output_dir/allowed_commands.raw.txt"
sort -u "$output_dir/allowed_commands.raw.txt" > "$output_dir/allowed_commands.normalized.txt"

if [[ -s "$todo_tmp" ]]; then
  sort -u "$todo_tmp" > "$output_dir/allowed_commands.todo.txt"
else
  : > "$output_dir/allowed_commands.todo.txt"
fi

{
  echo "command, count, examples"
  awk -F'\t' '
  {
    cmd=$1
    ex=$2
    count[cmd]++
    if (!(cmd in exs)) {
      exs[cmd]=ex
    } else if (index("|" exs[cmd] "|", "|" ex "|") == 0) {
      exs[cmd]=exs[cmd] "|" ex
    }
  }
  END {
    for (cmd in count) {
      print cmd ", " count[cmd] ", " exs[cmd]
    }
  }
  ' "$raw_with_ex_tmp" | sort
} > "$output_dir/command_frequency.csv"

rm -f "$raw_with_ex_tmp" "$todo_tmp"
