#!/bin/bash
# ci-failure.sh - Analyze GitHub Actions CI failures
# Usage: ./ci-failure.sh <github-actions-url>
# Example: ./ci-failure.sh https://github.com/temporalio/temporal/actions/runs/20277567364/job/58243981402?pr=8835

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

usage() {
    echo "Usage: $0 <github-actions-url>"
    echo "Example: $0 https://github.com/org/repo/actions/runs/12345/job/67890"
    exit 1
}

if [[ $# -lt 1 ]]; then
    usage
fi

URL="$1"

# Extract run ID and job ID from URL
# URL format: https://github.com/org/repo/actions/runs/RUN_ID/job/JOB_ID
if [[ "$URL" =~ /runs/([0-9]+)/job/([0-9]+) ]]; then
    RUN_ID="${BASH_REMATCH[1]}"
    JOB_ID="${BASH_REMATCH[2]}"
elif [[ "$URL" =~ /runs/([0-9]+) ]]; then
    RUN_ID="${BASH_REMATCH[1]}"
    JOB_ID=""
else
    echo -e "${RED}Error: Could not parse run ID from URL${NC}"
    usage
fi

# Extract repo from URL
if [[ "$URL" =~ github.com/([^/]+/[^/]+)/ ]]; then
    REPO="${BASH_REMATCH[1]}"
else
    echo -e "${RED}Error: Could not parse repository from URL${NC}"
    usage
fi

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}CI Failure Analysis${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "Repository: ${GREEN}$REPO${NC}"
echo -e "Run ID:     ${GREEN}$RUN_ID${NC}"
if [[ -n "$JOB_ID" ]]; then
    echo -e "Job ID:     ${GREEN}$JOB_ID${NC}"
fi
echo ""

# Get run info
echo -e "${YELLOW}▶ Fetching run information...${NC}"
RUN_INFO=$(gh run view "$RUN_ID" --repo "$REPO" --json name,status,conclusion,headBranch,event,createdAt,updatedAt 2>/dev/null || echo "{}")

if [[ "$RUN_INFO" != "{}" ]]; then
    NAME=$(echo "$RUN_INFO" | jq -r '.name // "N/A"')
    STATUS=$(echo "$RUN_INFO" | jq -r '.status // "N/A"')
    CONCLUSION=$(echo "$RUN_INFO" | jq -r '.conclusion // "N/A"')
    BRANCH=$(echo "$RUN_INFO" | jq -r '.headBranch // "N/A"')

    echo -e "Workflow:   $NAME"
    echo -e "Branch:     $BRANCH"
    echo -e "Status:     $STATUS"
    if [[ "$CONCLUSION" == "failure" ]]; then
        echo -e "Conclusion: ${RED}$CONCLUSION${NC}"
    else
        echo -e "Conclusion: $CONCLUSION"
    fi
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}▶ Failed Jobs${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# List failed jobs
gh run view "$RUN_ID" --repo "$REPO" --json jobs --jq '.jobs[] | select(.conclusion == "failure") | "  ❌ \(.name) (job: \(.databaseId))"' 2>/dev/null || echo "  Could not fetch job list"

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}▶ Fetching failure logs...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Fetch and analyze failed logs
if [[ -n "$JOB_ID" ]]; then
    LOGS=$(gh run view "$RUN_ID" --repo "$REPO" --job "$JOB_ID" --log-failed 2>&1 || echo "")
else
    LOGS=$(gh run view "$RUN_ID" --repo "$REPO" --log-failed 2>&1 || echo "")
fi

if [[ -z "$LOGS" ]] || echo "$LOGS" | grep -q "still in progress"; then
    echo -e "${YELLOW}Run is still in progress or logs are not yet available.${NC}"
    echo -e "${YELLOW}Try again once the run completes.${NC}"
    echo ""
    echo -e "${GREEN}View run status: gh run view $RUN_ID --repo $REPO${NC}"
    exit 0
fi

if echo "$LOGS" | grep -q "failed to get run log"; then
    echo -e "${YELLOW}Failed to fetch logs (GitHub API error). Logs may have expired.${NC}"
    echo ""
    echo -e "${GREEN}Try viewing in browser: $URL${NC}"
    exit 1
fi

# Strip ANSI color codes for easier parsing
LOGS_CLEAN=$(echo "$LOGS" | sed 's/\x1b\[[0-9;]*m//g')

# Extract test failures
echo -e "${RED}Failed Tests:${NC}"
FAILED_TESTS=$(echo "$LOGS_CLEAN" | grep -E "FAIL:.*Test" | sed 's/.*FAIL:/FAIL:/' | sort -u | head -20)
if [[ -n "$FAILED_TESTS" ]]; then
    echo "$FAILED_TESTS" | while read -r line; do
        echo -e "  ❌ $line"
    done
else
    echo "  No test failures found in logs"
fi

echo ""
echo -e "${RED}Assertion Errors:${NC}"
# Get context around errors
ERRORS=$(echo "$LOGS_CLEAN" | grep -E "(Error:.*Not equal|Error:.*Condition never|expected:|actual  :|Messages:)" | head -40)
if [[ -n "$ERRORS" ]]; then
    echo "$ERRORS" | while read -r line; do
        # Strip the job/step prefix for cleaner output
        clean_line=$(echo "$line" | sed 's/^.*Z[[:space:]]*//' | sed 's/^[[:space:]]*/  /')
        echo "$clean_line"
    done
else
    echo "  No assertion errors found"
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}▶ Summary${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Count failures
FAIL_COUNT=$(echo "$LOGS_CLEAN" | grep -c "FAIL:" 2>/dev/null || echo "0")
echo -e "Total FAIL markers: ${RED}$FAIL_COUNT${NC}"

# Check for common issues
if echo "$LOGS_CLEAN" | grep -q "Condition never satisfied"; then
    echo -e "${YELLOW}⚠  Flaky test detected: 'Condition never satisfied' (timing issue)${NC}"
fi

if echo "$LOGS_CLEAN" | grep -q "context deadline exceeded"; then
    echo -e "${YELLOW}⚠  Timeout detected: 'context deadline exceeded'${NC}"
fi

if echo "$LOGS_CLEAN" | grep -q "connection refused"; then
    echo -e "${YELLOW}⚠  Connection issue detected: 'connection refused'${NC}"
fi

if echo "$LOGS_CLEAN" | grep -q "panic:"; then
    echo -e "${RED}🔥 Panic detected in logs${NC}"
    echo "$LOGS_CLEAN" | grep -A5 "panic:" | head -10
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}Commands for further investigation:${NC}"
if [[ -n "$JOB_ID" ]]; then
    echo -e "  Full logs:     gh run view $RUN_ID --repo $REPO --job $JOB_ID --log-failed | less"
    echo -e "  Rerun job:     gh run rerun $RUN_ID --repo $REPO --job $JOB_ID"
else
    echo -e "  Full logs:     gh run view $RUN_ID --repo $REPO --log-failed | less"
    echo -e "  Rerun failed:  gh run rerun $RUN_ID --repo $REPO --failed"
fi
echo -e "  View in browser: $URL"

