#!/bin/bash

# Test that Tab switching is idempotent - repeatedly pressing Tab
# should alternate between two stable states

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=== Testing Idempotent Tab Switching ==="

SESSION="test-idempotent-$$"
tmux new-session -d -s "$SESSION" "tools/bash/f-rg TODO shell-config" 2>/dev/null
sleep 2

# Capture initial pattern mode state
echo "1. Initial pattern mode:"
PATTERN_STATE_1=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null)
echo "$PATTERN_STATE_1" | head -3

# Switch to command mode
tmux send-keys -t "$SESSION" Tab 2>/dev/null
sleep 2

echo -e "\n2. Command mode (after first Tab):"
COMMAND_STATE_1=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null)
echo "$COMMAND_STATE_1" | head -3

# Switch back to pattern mode
tmux send-keys -t "$SESSION" Tab 2>/dev/null
sleep 2

echo -e "\n3. Back to pattern mode (after second Tab):"
PATTERN_STATE_2=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null)
echo "$PATTERN_STATE_2" | head -3

# Switch to command mode again
tmux send-keys -t "$SESSION" Tab 2>/dev/null
sleep 2

echo -e "\n4. Back to command mode (after third Tab):"
COMMAND_STATE_2=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null)
echo "$COMMAND_STATE_2" | head -3

# One more cycle
tmux send-keys -t "$SESSION" Tab 2>/dev/null
sleep 2
PATTERN_STATE_3=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null)

tmux send-keys -t "$SESSION" Tab 2>/dev/null
sleep 2
COMMAND_STATE_3=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null)

tmux kill-session -t "$SESSION" 2>/dev/null || true

# Compare states
echo -e "\n=== Checking idempotency ==="

PASS=true

# Pattern states should be identical
if [ "$PATTERN_STATE_1" = "$PATTERN_STATE_2" ] && [ "$PATTERN_STATE_2" = "$PATTERN_STATE_3" ]; then
    echo -e "${GREEN}✓${NC} Pattern mode states are identical across switches"
else
    echo -e "${RED}✗${NC} Pattern mode states differ!"
    echo "Differences between state 1 and 2:"
    diff <(echo "$PATTERN_STATE_1" | head -5) <(echo "$PATTERN_STATE_2" | head -5) || true
    PASS=false
fi

# Command states should be identical
if [ "$COMMAND_STATE_1" = "$COMMAND_STATE_2" ] && [ "$COMMAND_STATE_2" = "$COMMAND_STATE_3" ]; then
    echo -e "${GREEN}✓${NC} Command mode states are identical across switches"
else
    echo -e "${RED}✗${NC} Command mode states differ!"
    echo "Differences between state 1 and 2:"
    diff <(echo "$COMMAND_STATE_1" | head -5) <(echo "$COMMAND_STATE_2" | head -5) || true
    PASS=false
fi

# Check that pattern mode query doesn't have quotes or command remnants
# The prompt is a space, so check after that space
if echo "$PATTERN_STATE_2" | grep -q " TODO" && echo "$PATTERN_STATE_2" | head -2 | tail -1 | grep -q "1/"; then
    echo -e "${GREEN}✓${NC} Pattern mode shows results and clean query"
else
    echo -e "${RED}✗${NC} Pattern mode query is corrupted or results missing:"
    echo "First 3 lines:"
    echo "$PATTERN_STATE_2" | head -3
    PASS=false
fi

# Overall result
echo
if [ "$PASS" = true ]; then
    echo -e "${GREEN}=== IDEMPOTENCY TEST PASSED ===${NC}"
    exit 0
else
    echo -e "${RED}=== IDEMPOTENCY TEST FAILED ===${NC}"
    exit 1
fi
