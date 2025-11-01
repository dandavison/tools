#!/bin/bash
# Regression test for command mode editing
# This ensures the bug reported by the user doesn't come back

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=== Command Mode Editing Regression Test ==="
echo "Testing: 'In another repo, I'm running f-rg --f-rg-command-mode Outcome chasm'"
echo "         'initially that does show results. But when I backspace to delete the m,'"
echo "         'the results disappear and don't come back.'"
echo ""

# Since we don't have "Outcome" in this repo, we'll test with "function"
echo -n "Simulating with 'function' pattern... "

SESSION="regression-$$"
tmux new-session -d -s "$SESSION" "tools/bash/f-rg --f-rg-command-mode function shell-config" 2>/dev/null
sleep 3

# Capture initial state
initial=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null | grep -c "function\|hyperlink" || echo "0")

# Delete last character of "function"
tmux send-keys -t "$SESSION" Home 2>/dev/null
for word in rg --follow -i --hidden -g "'!.git/*'" --json function; do
    tmux send-keys -t "$SESSION" C-Right 2>/dev/null
done
tmux send-keys -t "$SESSION" BSpace 2>/dev/null  # Delete 'n'
sleep 3

# Check if results still exist (not disappeared)
after_delete=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null | grep -c "functio\|ZSH_HIGHLIGHT" || echo "0")

# Add character back
tmux send-keys -t "$SESSION" "n" 2>/dev/null
sleep 3

# Check if results are restored
after_restore=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null | grep -c "function\|hyperlink" || echo "0")

tmux kill-session -t "$SESSION" 2>/dev/null || true

# Evaluate test
if [[ $initial -gt 0 ]] && [[ $after_delete -gt 0 ]] && [[ $after_restore -gt 0 ]]; then
    echo -e "${GREEN}PASS${NC}"
    echo "  ✓ Initial results shown: $initial matches"
    echo "  ✓ Results after delete: $after_delete matches (didn't disappear!)"
    echo "  ✓ Results after restore: $after_restore matches"
    exit 0
else
    echo -e "${RED}FAIL${NC}"
    echo "  Initial results: $initial matches"
    echo "  After delete: $after_delete matches"
    echo "  After restore: $after_restore matches"
    echo ""
    echo "  The bug has regressed - results disappear when editing!"
    exit 1
fi
