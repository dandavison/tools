#!/bin/bash
# Comprehensive test for command mode functionality

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "======================================"
echo "  Command Mode Comprehensive Tests"
echo "======================================"

PASS_COUNT=0
FAIL_COUNT=0

# Test 1: Initial invocation with pattern and path
echo -n "Test 1: Command mode with pattern and path... "
output=$(tools/bash/test-interactive "tools/bash/f-rg --f-rg-command-mode TODO shell-config" 2.0 2>/dev/null || true)
if echo "$output" | grep -q "lib_prompt\|lib\.sh"; then
    echo -e "${GREEN}PASS${NC}"
    ((PASS_COUNT++))
else
    echo -e "${RED}FAIL${NC}"
    echo "  Expected to see TODO results from shell-config"
    ((FAIL_COUNT++))
fi

# Test 2: Editing pattern (delete character)
echo -n "Test 2: Delete character from pattern... "
SESSION="delete-char-$$"
tmux new-session -d -s "$SESSION" "tools/bash/f-rg --f-rg-command-mode TODO shell-config" 2>/dev/null
sleep 3

# Navigate to O in TODO and delete it
tmux send-keys -t "$SESSION" Home 2>/dev/null  # Go to start
# Navigate to the O (after --json TOD)
for word in rg --follow -i --hidden -g "'!.git/*'" --json TOD; do
    tmux send-keys -t "$SESSION" C-Right 2>/dev/null
done
tmux send-keys -t "$SESSION" Delete 2>/dev/null
sleep 3

output=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null || true)
if echo "$output" | grep -q "atuin\|TOD"; then
    echo -e "${GREEN}PASS${NC}"
    ((PASS_COUNT++))
else
    echo -e "${RED}FAIL${NC}"
    echo "  Expected to see TOD results after deleting O"
    ((FAIL_COUNT++))
fi
tmux kill-session -t "$SESSION" 2>/dev/null || true

# Test 3: Adding text to pattern
echo -n "Test 3: Add character to pattern... "
SESSION="add-char-$$"
tmux new-session -d -s "$SESSION" "tools/bash/f-rg --f-rg-command-mode TOD shell-config" 2>/dev/null
sleep 3

# Navigate to end of TOD and add O
tmux send-keys -t "$SESSION" Home 2>/dev/null
for word in rg --follow -i --hidden -g "'!.git/*'" --json TOD; do
    tmux send-keys -t "$SESSION" C-Right 2>/dev/null
done
tmux send-keys -t "$SESSION" "O" 2>/dev/null
sleep 3

output=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null || true)
if echo "$output" | grep -q "lib_prompt\|TODO"; then
    echo -e "${GREEN}PASS${NC}"
    ((PASS_COUNT++))
else
    echo -e "${RED}FAIL${NC}"
    echo "  Expected to see TODO results after adding O"
    ((FAIL_COUNT++))
fi
tmux kill-session -t "$SESSION" 2>/dev/null || true

# Test 4: Replace entire command
echo -n "Test 4: Replace entire command... "
SESSION="replace-cmd-$$"
tmux new-session -d -s "$SESSION" "tools/bash/f-rg --f-rg-command-mode TODO shell-config" 2>/dev/null
sleep 3

tmux send-keys -t "$SESSION" C-u 2>/dev/null
tmux send-keys -t "$SESSION" "rg --json function shell-config/lib.sh" 2>/dev/null
sleep 3

output=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null || true)
if echo "$output" | grep -q "function.*print_array\|declare_array"; then
    echo -e "${GREEN}PASS${NC}"
    ((PASS_COUNT++))
else
    echo -e "${RED}FAIL${NC}"
    echo "  Expected to see function results from lib.sh"
    ((FAIL_COUNT++))
fi
tmux kill-session -t "$SESSION" 2>/dev/null || true

# Test 5: Command mode with multiple paths
echo -n "Test 5: Command mode with multiple paths... "
output=$(tools/bash/test-interactive "tools/bash/f-rg --f-rg-command-mode function shell-config tools" 2.0 2>/dev/null || true)
if echo "$output" | grep -q "shell-config\|tools"; then
    echo -e "${GREEN}PASS${NC}"
    ((PASS_COUNT++))
else
    echo -e "${RED}FAIL${NC}"
    echo "  Expected to see results from both shell-config and tools"
    ((FAIL_COUNT++))
fi

# Test 6: Command mode with glob option
echo -n "Test 6: Command mode with glob option... "
output=$(tools/bash/test-interactive "tools/bash/f-rg -g '*.sh' --f-rg-command-mode function shell-config" 2.0 2>/dev/null || true)
if echo "$output" | grep -q "\.sh:"; then
    echo -e "${GREEN}PASS${NC}"
    ((PASS_COUNT++))
else
    echo -e "${RED}FAIL${NC}"
    echo "  Expected to see results only from .sh files"
    ((FAIL_COUNT++))
fi

# Test 7: Remove --json and verify it still works
echo -n "Test 7: Remove --json flag (should be auto-added)... "
SESSION="remove-json-$$"
tmux new-session -d -s "$SESSION" "tools/bash/f-rg --f-rg-command-mode TODO shell-config" 2>/dev/null
sleep 3

# Remove --json from command
tmux send-keys -t "$SESSION" C-u 2>/dev/null
tmux send-keys -t "$SESSION" "rg TODO shell-config" 2>/dev/null
sleep 3

output=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null || true)
# Should still work because we auto-add --json
if echo "$output" | grep -q "TODO\|lib"; then
    echo -e "${GREEN}PASS${NC}"
    ((PASS_COUNT++))
else
    echo -e "${RED}FAIL${NC}"
    echo "  Expected results even without --json (should be auto-added)"
    ((FAIL_COUNT++))
fi
tmux kill-session -t "$SESSION" 2>/dev/null || true

# Test 8: Edit to invalid command
echo -n "Test 8: Invalid command shows no results... "
SESSION="invalid-cmd-$$"
tmux new-session -d -s "$SESSION" "tools/bash/f-rg --f-rg-command-mode TODO shell-config" 2>/dev/null
sleep 3

tmux send-keys -t "$SESSION" C-u 2>/dev/null
tmux send-keys -t "$SESSION" "rg --json --invalid-option TODO shell-config" 2>/dev/null
sleep 3

output=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null || true)
# Should show no results or empty
if ! echo "$output" | grep -q "lib_prompt\|TODO:"; then
    echo -e "${GREEN}PASS${NC}"
    ((PASS_COUNT++))
else
    echo -e "${RED}FAIL${NC}"
    echo "  Invalid command should not show results"
    ((FAIL_COUNT++))
fi
tmux kill-session -t "$SESSION" 2>/dev/null || true

echo ""
echo "=== Results ==="
echo "Total tests: $((PASS_COUNT + FAIL_COUNT))"
echo -e "Passed: ${GREEN}$PASS_COUNT${NC}"
echo -e "Failed: ${RED}$FAIL_COUNT${NC}"

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "\n${GREEN}All command mode tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}Some tests failed${NC}"
    exit 1
fi
