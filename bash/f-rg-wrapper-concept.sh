#!/bin/bash
# Concept: Wrapper that manages mode switching

STATE_FILE="/tmp/f-rg-state-$$"
MODE="pattern"
PATTERN="$1"
shift
PATHS=("$@")

while true; do
    if [[ "$MODE" == "pattern" ]]; then
        # Run pattern mode
        # Tab binding would write "switch:command:$PATTERN" to STATE_FILE and exit
        echo "" | fzf \
            --bind='tab:execute-silent:echo "switch:command:{q}" > '"$STATE_FILE"'; echo "{q}")+abort' \
            --query="$PATTERN"
    else
        # Run command mode
        # Tab binding would write "switch:pattern:$PATTERN" to STATE_FILE and exit
        full_cmd="rg --json $PATTERN ${PATHS[*]}"
        echo "" | fzf \
            --bind='tab:execute-silent:
                PATTERN=$(echo {q} | sed -E "s/.*--json[[:space:]]+([^[:space:]]+).*/\1/")
                echo "switch:pattern:$PATTERN" > '"$STATE_FILE"'
                echo "$PATTERN"
            +abort' \
            --query="$full_cmd"
    fi
    
    # Check if we should switch modes
    if [[ -f "$STATE_FILE" ]]; then
        ACTION=$(cat "$STATE_FILE")
        rm "$STATE_FILE"
        
        if [[ "$ACTION" == switch:* ]]; then
            MODE=$(echo "$ACTION" | cut -d: -f2)
            PATTERN=$(echo "$ACTION" | cut -d: -f3-)
        else
            break  # Exit on enter or escape
        fi
    else
        break  # No state file means normal exit
    fi
done
