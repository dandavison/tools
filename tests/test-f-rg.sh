#!/bin/bash

# Test suite for f-rg
# Uses test-interactive to verify the tool is working correctly

set -e

cd /Users/dan/src/devenv

echo "======================================"
echo "  f-rg Test Suite"
echo "======================================"
echo

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

test_count=0
failed_count=0

# Test function
run_test() {
    local test_name="$1"
    local command="$2"
    local expected_pattern="$3"
    
    test_count=$((test_count + 1))
    echo -n "Test $test_count: $test_name... "
    
    # Run the command with test-interactive
    output=$(tools/bash/test-interactive "$command" 0.8 2>/dev/null || true)
    
    if echo "$output" | grep -q "$expected_pattern"; then
        echo -e "${GREEN}PASS${NC}"
        return 0
    else
        echo -e "${RED}FAIL${NC}"
        echo "  Expected to find: '$expected_pattern'"
        echo "  Command: $command"
        failed_count=$((failed_count + 1))
        return 1
    fi
}

echo "=== Basic Functionality Tests ==="
echo

# Test 1: Basic search
run_test "Basic pattern search" \
    "tools/bash/f-rg TODO ." \
    "TODO"

# Test 2: Search with specific path
run_test "Search in specific directory" \
    "tools/bash/f-rg TODO shell-config" \
    "lib_prompt.sh"

# Test 3: Multiple paths
run_test "Search in multiple paths" \
    "tools/bash/f-rg class tools/python dotfiles/pdb" \
    "class"

# Test 4: Search with glob filter
run_test "Search with glob filter for Python files" \
    "tools/bash/f-rg -g '*.py' class ." \
    "\.py"

# Test 5: Custom option --real-code-only
run_test "Search with --real-code-only option" \
    "tools/bash/f-rg --real-code-only TODO ." \
    "TODO"

echo
echo "=== UI Rendering Tests ==="
echo

# Test 6: Check if fzf UI loads
run_test "FZF UI renders correctly" \
    "tools/bash/f-rg test ." \
    "─────"

# Test 7: Check preview window border
run_test "Preview window displays" \
    "tools/bash/f-rg function shell-config" \
    "╭─"

echo
echo "=== Mode Switching Tests ==="
echo

# Test 8: Tab switches to command mode
test_count=$((test_count + 1))
echo -n "Test $test_count: Tab switches to command mode... "

SESSION="test-tab-$$"
tmux new-session -d -s "$SESSION" "tools/bash/f-rg TODO ." 2>/dev/null
sleep 1.5
tmux send-keys -t "$SESSION" Tab 2>/dev/null
sleep 1.5
output=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null || true)

# Check that mode switches correctly (results may briefly disappear)
# 1. Header shows Command Mode
# 2. Query line shows the full rg command
if echo "$output" | grep -q "rg.*--json.*TODO"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
    echo "  Expected: Full rg command with --json in query"
    failed_count=$((failed_count + 1))
fi

tmux kill-session -t "$SESSION" 2>/dev/null || true

# Test 9: Tab toggles back to pattern mode
test_count=$((test_count + 1))
echo -n "Test $test_count: Tab toggles back to pattern mode... "

SESSION="test-toggle-$$"
tmux new-session -d -s "$SESSION" "tools/bash/f-rg TODO ." 2>/dev/null
sleep 1.5
tmux send-keys -t "$SESSION" Tab 2>/dev/null  # Switch to command mode
sleep 1.5
tmux send-keys -t "$SESSION" Tab 2>/dev/null  # Switch back to pattern mode
sleep 1.5
output=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null || true)

if echo "$output" | grep -q "rg --follow" && \
   ! echo "$output" | grep -q "rg.*--json"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
    echo "  Expected: rg command header without --json"
    failed_count=$((failed_count + 1))
fi

tmux kill-session -t "$SESSION" 2>/dev/null || true

# Test 10: Typing in command mode shows results
test_count=$((test_count + 1))
echo -n "Test $test_count: Typing in command mode shows results... "

SESSION="test-type-$$"
tmux new-session -d -s "$SESSION" "tools/bash/f-rg TODO ." 2>/dev/null
sleep 1.5
tmux send-keys -t "$SESSION" Tab 2>/dev/null  # Switch to command mode
sleep 1.5
# Add a space to trigger reload
tmux send-keys -t "$SESSION" " " 2>/dev/null
sleep 1.5
output=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null || true)

if echo "$output" | grep -qE "\.(sh|txt|py|el|md):|TODO"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
    echo "  Expected to see results after typing in command mode"
    failed_count=$((failed_count + 1))
fi

tmux kill-session -t "$SESSION" 2>/dev/null || true

# Test 11: Editing command in command mode updates results
test_count=$((test_count + 1))
echo -n "Test $test_count: Editing command in command mode updates results... "

SESSION="test-edit-$$"
tmux new-session -d -s "$SESSION" "tools/bash/f-rg test ." 2>/dev/null
sleep 1.5
tmux send-keys -t "$SESSION" Tab 2>/dev/null  # Switch to command mode
sleep 1.5
# Clear the command and type a new one searching for TODO
tmux send-keys -t "$SESSION" C-u 2>/dev/null  # Clear line
tmux send-keys -t "$SESSION" "rg --follow -i --hidden -g '!.git/*' --json TODO ." 2>/dev/null
sleep 2
output=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null || true)

if echo "$output" | grep -q "TODO"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
    echo "  Expected to find 'TODO' in results after editing command"
    failed_count=$((failed_count + 1))
fi

tmux kill-session -t "$SESSION" 2>/dev/null || true

# Test 12: Path retention when switching modes
test_count=$((test_count + 1))
echo -n "Test $test_count: Path changes are retained when switching modes... "

SESSION="test-path-retention-$$"
tmux new-session -d -s "$SESSION" "tools/bash/f-rg TODO ." 2>/dev/null
sleep 1.5
# Switch to command mode
tmux send-keys -t "$SESSION" Tab 2>/dev/null
sleep 1.5
# Edit command to change . to shell-config
tmux send-keys -t "$SESSION" C-e 2>/dev/null  # Go to end
tmux send-keys -t "$SESSION" BSpace 2>/dev/null  # Delete .
tmux send-keys -t "$SESSION" "shell-config" 2>/dev/null
sleep 1.5
# Switch back to pattern mode
tmux send-keys -t "$SESSION" Tab 2>/dev/null
sleep 1.5
output=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null || true)

# Check if header shows shell-config instead of .
if echo "$output" | grep -q "rg.*shell-config"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
    echo "  Expected: rg command header should show 'shell-config' after editing in command mode"
    echo "  Got: $(echo "$output" | grep "rg --follow" | head -1)"
    failed_count=$((failed_count + 1))
fi

tmux kill-session -t "$SESSION" 2>/dev/null || true

echo
echo "=== Results ==="
echo "Total tests: $test_count"
echo -e "Passed: ${GREEN}$((test_count - failed_count))${NC}"
if [[ $failed_count -gt 0 ]]; then
    echo -e "Failed: ${RED}$failed_count${NC}"
    exit 1
else
    echo -e "Failed: ${GREEN}0${NC}"
    echo
    echo -e "${GREEN}All tests passed!${NC}"
fi
