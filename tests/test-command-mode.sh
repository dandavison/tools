#!/bin/bash

# Test command mode functionality

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=== Command Mode Tests ==="

# Test 1: Direct command mode invocation shows results
echo -n "Test 1: Command mode shows initial results... "
SESSION="cmd-test1-$$"
tmux new-session -d -s "$SESSION" "tools/bash/f-rg --f-rg-command-mode TODO shell-config" 2>/dev/null
sleep 2
output=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null || true)

if echo "$output" | grep -q "lib_prompt" && echo "$output" | grep -q "Command Mode"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
    echo "  Expected to see results and 'Command Mode' header"
fi
tmux kill-session -t "$SESSION" 2>/dev/null || true

# Test 2: Switching from pattern to command shows results
echo -n "Test 2: Tab from pattern to command shows results... "
SESSION="cmd-test2-$$"
tmux new-session -d -s "$SESSION" "tools/bash/f-rg TODO shell-config" 2>/dev/null
sleep 2
tmux send-keys -t "$SESSION" Tab 2>/dev/null
sleep 2
output=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null || true)

if echo "$output" | grep -q "Command Mode" && echo "$output" | grep -q "lib_prompt"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
    echo "  Expected to see 'Command Mode' and results"
    echo "  Output preview:"
    echo "$output" | head -5
fi
tmux kill-session -t "$SESSION" 2>/dev/null || true

# Test 3: Tab back to pattern mode works
echo -n "Test 3: Tab back to pattern mode... "
SESSION="cmd-test3-$$"
tmux new-session -d -s "$SESSION" "tools/bash/f-rg TODO ." 2>/dev/null
sleep 2
# Tab to command mode
tmux send-keys -t "$SESSION" Tab 2>/dev/null
sleep 2
# Tab back to pattern mode
tmux send-keys -t "$SESSION" Tab 2>/dev/null
sleep 2
output=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null || true)

# Check that we're in pattern mode with just "TODO" in query
query_line=$(echo "$output" | grep "^ TODO" | head -1)
header_line=$(echo "$output" | grep "Pattern Mode" | head -1)

if [[ -n "$header_line" ]] && [[ -n "$query_line" ]]; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
    echo "  Expected: Pattern Mode header and 'TODO' in query"
    echo "  Query line: '$query_line'"
    echo "  Header: '$header_line'"
fi
tmux kill-session -t "$SESSION" 2>/dev/null || true

echo "=== Done ==="
