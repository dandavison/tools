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
echo "=== Command Editing Tests ==="
echo

# Test 8: Check if Ctrl-E shows edit screen
test_count=$((test_count + 1))
echo -n "Test $test_count: Ctrl-E opens command editor... "

SESSION="test-ctrl-e-$$"
tmux new-session -d -s "$SESSION" "tools/bash/f-rg TODO ." 2>/dev/null
sleep 1
tmux send-keys -t "$SESSION" C-e 2>/dev/null
sleep 1
output=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null || true)
tmux kill-session -t "$SESSION" 2>/dev/null || true

if echo "$output" | grep -q "Edit ripgrep command"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
    echo "  Expected to find edit command screen"
    failed_count=$((failed_count + 1))
fi

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
