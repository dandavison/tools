#!/bin/bash

# Test f-rg mode switching functionality

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_DIR="$(cd "$SCRIPT_DIR/../bash" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_DIR="/tmp/test-f-rg-modes-$$"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Create test directory
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

# Create test files
echo "TODO: implement feature X" > file1.txt
echo "class MyClass:" > file2.py
echo "TODO: refactor this" > file3.py
echo "function testFunction() {}" > file4.js

run_test() {
    local test_name="$1"
    local cmd="$2"
    echo -e "\n${GREEN}Test:${NC} $test_name"
}

# Test 1: Initial pattern mode displays results
run_test "Initial pattern mode" ""
SESSION="test-1-$$"
timeout 5 bash -c "
tmux new-session -d -s '$SESSION' '$TOOLS_DIR/f-rg TODO $TEST_DIR'
sleep 2
output=\$(tmux capture-pane -t '$SESSION' -p)
tmux kill-session -t '$SESSION' 2>/dev/null

# Check for results
if echo \"\$output\" | grep -q 'TODO: implement feature X'; then
    echo '✓ Pattern mode shows results'
else
    echo '✗ Pattern mode failed to show results'
    echo 'Output:' 
    echo \"\$output\" | head -10
fi
" || echo "✗ Test timed out"

# Test 2: Tab switches to command mode
run_test "Tab switches to command mode" ""
SESSION="test-2-$$"
timeout 5 bash -c "
tmux new-session -d -s '$SESSION' '$TOOLS_DIR/f-rg TODO $TEST_DIR'
sleep 2
tmux send-keys -t '$SESSION' Tab
sleep 1
output=\$(tmux capture-pane -t '$SESSION' -p)
tmux kill-session -t '$SESSION' 2>/dev/null

# Check for command mode
if echo \"\$output\" | grep -q 'Command Mode'; then
    echo '✓ Switched to command mode'
else
    echo '✗ Failed to switch to command mode'
fi

# Check that command is displayed
if echo \"\$output\" | grep -q 'rg --follow'; then
    echo '✓ Command is displayed in query'
else
    echo '✗ Command not displayed'
    echo 'Query line:' 
    echo \"\$output\" | head -2
fi
" || echo "✗ Test timed out"

# Test 3: Command mode shows results after typing
run_test "Command mode shows results after typing" ""
SESSION="test-3-$$"
timeout 5 bash -c "
tmux new-session -d -s '$SESSION' '$TOOLS_DIR/f-rg TODO $TEST_DIR'
sleep 2
tmux send-keys -t '$SESSION' Tab
sleep 1
# Type a space to trigger reload
tmux send-keys -t '$SESSION' Space
sleep 1
output=\$(tmux capture-pane -t '$SESSION' -p)
tmux kill-session -t '$SESSION' 2>/dev/null

# Check for results
if echo \"\$output\" | grep -q 'TODO: implement feature X'; then
    echo '✓ Command mode shows results after typing'
else
    echo '✗ Command mode failed to show results'
    echo 'Output after space:' 
    echo \"\$output\" | head -10
fi
" || echo "✗ Test timed out"

# Test 4: Tab toggles back to pattern mode
run_test "Tab toggles back to pattern mode" ""
SESSION="test-4-$$"
timeout 5 bash -c "
tmux new-session -d -s '$SESSION' '$TOOLS_DIR/f-rg TODO $TEST_DIR'
sleep 2
# Switch to command mode
tmux send-keys -t '$SESSION' Tab
sleep 1
# Switch back to pattern mode
tmux send-keys -t '$SESSION' Tab
sleep 1
output=\$(tmux capture-pane -t '$SESSION' -p)
tmux kill-session -t '$SESSION' 2>/dev/null

# Check we're back in pattern mode (no "Command Mode" in header)
if echo \"\$output\" | grep -q 'Command Mode'; then
    echo '✗ Still in command mode, toggle failed'
else
    echo '✓ Toggled back to pattern mode'
fi

# Check that pattern is restored in query
query=\$(echo \"\$output\" | head -2 | tail -1)
if echo \"\$query\" | grep -q 'TODO'; then
    echo '✓ Pattern restored in query'
else
    echo '✗ Pattern not restored'
    echo \"Query: \$query\"
fi
" || echo "✗ Test timed out"

# Test 5: Editing command in command mode
run_test "Editing command in command mode" ""
SESSION="test-5-$$"
timeout 5 bash -c "
tmux new-session -d -s '$SESSION' '$TOOLS_DIR/f-rg TODO $TEST_DIR'
sleep 2
# Switch to command mode
tmux send-keys -t '$SESSION' Tab
sleep 1
# Move to end of line and change TODO to class
tmux send-keys -t '$SESSION' End
# Move back to TODO and replace it
for i in {1..20}; do tmux send-keys -t '$SESSION' Left; done
# Delete TODO
for i in {1..4}; do tmux send-keys -t '$SESSION' Delete; done
# Type class
tmux send-keys -t '$SESSION' 'class'
sleep 1
output=\$(tmux capture-pane -t '$SESSION' -p)
tmux kill-session -t '$SESSION' 2>/dev/null

# Check that we now see Python class results
if echo \"\$output\" | grep -q 'class MyClass'; then
    echo '✓ Command editing works - shows class results'
else
    echo '✗ Command editing failed'
    echo 'Output:' 
    echo \"\$output\" | head -10
fi
" || echo "✗ Test timed out"

# Test 6: Multiple toggles work correctly
run_test "Multiple toggles" ""
SESSION="test-6-$$"
timeout 7 bash -c "
tmux new-session -d -s '$SESSION' '$TOOLS_DIR/f-rg TODO $TEST_DIR'
sleep 1

# Toggle multiple times and check state
for i in 1 2 3 4; do
    tmux send-keys -t '$SESSION' Tab
    sleep 0.5
    output=\$(tmux capture-pane -t '$SESSION' -p)
    
    if (( i % 2 == 1 )); then
        # Odd toggles should be command mode
        if echo \"\$output\" | grep -q 'Command Mode'; then
            echo \"✓ Toggle \$i: Command mode\"
        else
            echo \"✗ Toggle \$i: Expected command mode\"
        fi
    else
        # Even toggles should be pattern mode
        if echo \"\$output\" | grep -q 'Command Mode'; then
            echo \"✗ Toggle \$i: Expected pattern mode\"
        else
            echo \"✓ Toggle \$i: Pattern mode\"
        fi
    fi
done

tmux kill-session -t '$SESSION' 2>/dev/null
" || echo "✗ Test timed out"

# Cleanup
cd /
rm -rf "$TEST_DIR"

echo -e "\n${GREEN}Mode switching tests complete!${NC}"

