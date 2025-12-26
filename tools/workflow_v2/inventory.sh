#!/usr/bin/env bash
set -euo pipefail

# Script to provide an inventory of v2 IR completeness and flag red-alert tokens

echo "=== Maestro v2 IR Inventory ==="
echo

# 1) IR presence summary
echo "1) IR Presence Summary:"
echo

# Count and list workflow files
intent_files=$(find docs/workflows/v2/ir/wf/ -name "WF-*.intent.yaml" 2>/dev/null | wc -l)
cli_files=$(find docs/workflows/v2/ir/wf/ -name "WF-*.cli.yaml" 2>/dev/null | wc -l)
code_files=$(find docs/workflows/v2/ir/wf/ -name "WF-*.code.yaml" 2>/dev/null | wc -l)
cmd_cli_files=$(find docs/workflows/v2/ir/cmd/ -name "CMD-*.cli.yaml" 2>/dev/null | wc -l)
cmd_code_files=$(find docs/workflows/v2/ir/cmd/ -name "CMD-*.code.yaml" 2>/dev/null | wc -l)

echo "  Intent files (WF-*.intent.yaml): $intent_files"
find docs/workflows/v2/ir/wf/ -name "WF-*.intent.yaml" 2>/dev/null | sed 's/^/    /'

echo
echo "  CLI files (WF-*.cli.yaml): $cli_files"
find docs/workflows/v2/ir/wf/ -name "WF-*.cli.yaml" 2>/dev/null | sed 's/^/    /'

echo
echo "  Code files (WF-*.code.yaml): $code_files"
find docs/workflows/v2/ir/wf/ -name "WF-*.code.yaml" 2>/dev/null | sed 's/^/    /'

echo
echo "  CMD CLI files (CMD-*.cli.yaml): $cmd_cli_files"
find docs/workflows/v2/ir/cmd/ -name "CMD-*.cli.yaml" 2>/dev/null | sed 's/^/    /'

echo
echo "  CMD Code files (CMD-*.code.yaml): $cmd_code_files"
find docs/workflows/v2/ir/cmd/ -name "CMD-*.code.yaml" 2>/dev/null | sed 's/^/    /'

echo
mapping_file="docs/workflows/v2/ir/maps/wf_to_commands.yaml"
if [ -f "$mapping_file" ]; then
    echo "  Mapping file (wf_to_commands.yaml): 1"
    echo "    $mapping_file"
else
    echo "  Mapping file (wf_to_commands.yaml): 0"
fi

echo
echo "2) WF → CMD Link Integrity:"
echo

# Check for mapping file and analyze links if it exists
if [ -f "$mapping_file" ]; then
    echo "  wf_to_commands.yaml exists. Checking WF → CMD links..."
    echo
    
    # Extract the content under wf_to_commands section using sed
    sed -n '/wf_to_commands:/,$p' "$mapping_file" | sed '1d' > /tmp/wf_cmds_temp.yaml
    
    current_wf=""
    while IFS= read -r line; do
        # Skip empty lines and comments
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        
        # Check if this line is a workflow ID
        if [[ $line =~ ^[[:space:]]*WF-[0-9]+:[[:space:]]*$ ]]; then
            # Extract workflow ID using bash parameter expansion
            temp_line=$(echo "$line" | xargs)  # trim whitespace
            current_wf=${temp_line%:}  # remove trailing colon
            echo "  WF: $current_wf"
        # Check if this line is a command under a workflow
        elif [[ $line =~ ^[[:space:]]*-[[:space:]]*CMD-[A-Z0-9-]+[[:space:]]*$ ]] && [ -n "$current_wf" ]; then
            # Extract command ID using xargs and cut to get the second field
            cmd_id=$(echo "$line" | xargs | cut -d' ' -f2)
            echo "    -> CMD: $cmd_id"
            
            # Check if CLI file exists
            cli_file="docs/workflows/v2/ir/cmd/${cmd_id}.cli.yaml"
            if [ ! -f "$cli_file" ]; then
                echo "      ! Missing CLI: $cli_file"
            fi
            
            # Check if CODE file exists
            code_file="docs/workflows/v2/ir/cmd/${cmd_id}.code.yaml"
            if [ ! -f "$code_file" ]; then
                echo "      ! Missing CODE: $code_file"
            fi
        # If we encounter another top-level key, we're out of the wf_to_commands section
        elif [[ $line =~ ^[[:space:]]*[a-z] ]]; then
            break
        fi
    done < /tmp/wf_cmds_temp.yaml
    
    # Clean up temp file
    rm -f /tmp/wf_cmds_temp.yaml
    
    echo
    echo "  Checking for orphan commands (CMD present but not referenced by any WF)..."
    
    # Find all CMD files (both cli and code)
    all_cmd_files_cli=$(find docs/workflows/v2/ir/cmd/ -name "CMD-*.cli.yaml" 2>/dev/null | xargs -n 1 basename | sed 's/\.cli\.yaml$//' | sort -u)
    all_cmd_files_code=$(find docs/workflows/v2/ir/cmd/ -name "CMD-*.code.yaml" 2>/dev/null | xargs -n 1 basename | sed 's/\.code\.yaml$//' | sort -u)
    
    # Combine unique CMD IDs from both CLI and code files
    all_cmd_files=$(printf "%s\n%s\n" "$all_cmd_files_cli" "$all_cmd_files_code" | sort -u)
    
    # Find referenced CMDs in the mapping file by extracting lines with commands
    referenced_cmds=$(sed -n '/wf_to_commands:/,$p' "$mapping_file" | sed '1d' | grep -E '^[[:space:]]*-[[:space:]]*CMD-' | xargs -n 2 | cut -d' ' -f2 2>/dev/null | sort -u)
    
    # Find orphan commands
    if [ -n "$all_cmd_files" ] && [ -n "$referenced_cmds" ]; then
        orphan_cmds=$(comm -23 <(echo "$all_cmd_files" | sort) <(echo "$referenced_cmds" | sort))
        if [ -n "$orphan_cmds" ]; then
            echo "    Orphan commands found:"
            echo "$orphan_cmds" | sed 's/^/      /'
        else
            echo "    No orphan commands found"
        fi
    elif [ -n "$all_cmd_files" ]; then
        echo "    All commands are orphaned (no references found in mapping file)"
        echo "$all_cmd_files" | sed 's/^/      /'
    else
        echo "    No commands found"
    fi
else
    echo "  wf_to_commands.yaml does not exist"
fi

echo
echo "3) Red-alert Token Scan:"
echo

# Search for red-alert tokens in v1 and v2 directories
tokens=("DataMarkdown" "\./\.maestro" "\.maestro/" "docs/todo.md" "docs/done.md" "TODO(" "dangerously_skip_permissions")

for token in "${tokens[@]}"; do
    echo "  Searching for: $token"
    results=$(find docs/workflows/v{1,2}/ -type f \( -name "*.md" -o -name "*.yaml" -o -name "*.yml" -o -name "*.txt" \) -exec grep -n -H -e "$token" {} \; 2>/dev/null | wc -l)
    echo "    FOUND: $token ($results hits)"
    
    # Show the actual findings
    find docs/workflows/v{1,2}/ -type f \( -name "*.md" -o -name "*.yaml" -o -name "*.yml" -o -name "*.txt" \) -exec grep -n -H -e "$token" {} \; 2>/dev/null | sed 's/^/      /'
    echo
done

echo
echo "4) Storage Contract Sanity:"
echo

# Check WF-09 intent for JSON storage declaration
wf09_intent="docs/workflows/v2/ir/wf/WF-09.intent.yaml"
if [ -f "$wf09_intent" ]; then
    echo "  WF-09 intent file exists"
    json_storage=$(grep -E "storage_backend:[[:space:]]*json" "$wf09_intent" 2>/dev/null)
    if [ -n "$json_storage" ]; then
        echo "    WF-09 declares JSON storage"
        wf09_uses_json=true
    else
        echo "    WF-09 does NOT declare JSON storage"
        wf09_uses_json=false
    fi
else
    echo "  WF-09 intent file does not exist"
    wf09_uses_json=false
fi

# Check for CMD code IR files that declare markdown|mixed storage
if [ "$wf09_uses_json" = true ]; then
    echo "  Checking for CMD files that declare markdown|mixed storage (potential conflict with WF-09)..."
    conflicting_files=$(find docs/workflows/v2/ir/cmd/ -name "CMD-*.code.yaml" -exec grep -l -E "storage_backend:[[:space:]]*(markdown|mixed)" {} \; 2>/dev/null)
    if [ -n "$conflicting_files" ]; then
        echo "    ! Conflicting storage declarations found:"
        echo "$conflicting_files" | sed 's/^/      /'
    else
        echo "    No conflicting storage declarations found"
    fi
else
    echo "  WF-09 does not use JSON storage, skipping conflict check"
fi

echo
echo "Inventory complete."