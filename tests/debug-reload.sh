#!/bin/bash
# Debug script to test what {q} contains

cat > /tmp/test-reload.sh << 'EOF'
#!/bin/bash
echo "Received query: $@" >> /tmp/fzf-debug.log
eval "$@" 2>/dev/null
EOF
chmod +x /tmp/test-reload.sh

# Clear debug log
> /tmp/fzf-debug.log

# Run f-rg in command mode with debug reload
echo "" | fzf -d: \
    --query="rg --json TODO shell-config" \
    --phony \
    --bind='start:reload:rg --json TODO shell-config 2>/dev/null | head -5' \
    --bind='change:reload:/tmp/test-reload.sh {q} | head -5' &

FZF_PID=$!
sleep 2

# Type something
echo "Sending keystrokes..."
# This won't work well without tmux, but let's see the log

sleep 3
kill $FZF_PID 2>/dev/null

echo "Debug log contents:"
cat /tmp/fzf-debug.log
