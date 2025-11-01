#!/bin/bash

# Test command mode editing functionality

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=== Testing Command Mode Editing ==="

# Test 1: Basic command mode invocation
echo -n "Test 1: Initial command mode shows results... "
output=$(tools/bash/test-interactive "tools/bash/f-rg --f-rg-command-mode TODO shell-config" 2.0 2>/dev/null || true)
if echo "$output" | grep -q "lib_prompt"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
    echo "  Expected to see lib_prompt.sh in results"
fi

# Test 2: Editing command in command mode
echo -n "Test 2: Editing command updates results... "
SESSION="edit-test-$$"
tmux new-session -d -s "$SESSION" "tools/bash/f-rg --f-rg-command-mode TODO shell-config" 2>/dev/null
sleep 3

# Initial capture
initial=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null || true)
has_initial=false
if echo "$initial" | grep -q "lib_prompt"; then
    has_initial=true
fi

# Delete last character (D from TODO -> TOD)
tmux send-keys -t "$SESSION" End 2>/dev/null  # Go to end of line
tmux send-keys -t "$SESSION" Left Left Left Left Left Left Left Left Left Left Left Left Left Left 2>/dev/null  # Move to D in TODO
tmux send-keys -t "$SESSION" Delete 2>/dev/null  # Delete D
sleep 3

# Check if results update
edited=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null || true)
has_edited=false
if echo "$edited" | grep -qE "TOD|results"; then
    has_edited=true
fi

tmux kill-session -t "$SESSION" 2>/dev/null || true

if $has_initial && $has_edited; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
    if ! $has_initial; then
        echo "  Initial results not shown"
    fi
    if ! $has_edited; then
        echo "  Results disappeared after editing"
    fi
fi

# Test 3: Clear and type new command
echo -n "Test 3: Clear and type new command... "
SESSION="clear-test-$$"
tmux new-session -d -s "$SESSION" "tools/bash/f-rg --f-rg-command-mode TODO shell-config" 2>/dev/null
sleep 3

# Clear line and type new command
tmux send-keys -t "$SESSION" C-u 2>/dev/null
tmux send-keys -t "$SESSION" "rg --json function shell-config" 2>/dev/null
sleep 3

output=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null || true)
if echo "$output" | grep -q "function"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
    echo "  Expected to see 'function' in results after typing new command"
fi

tmux kill-session -t "$SESSION" 2>/dev/null || true

echo "=== Done ==="
