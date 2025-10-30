#!/bin/bash

# Run all tests in the tools/tests directory

cd "$(dirname "$0")"

echo "================================"
echo "  Running All Tool Tests"
echo "================================"
echo

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

total_tests=0
passed_tests=0
failed_tests=0

# Run f-rg tests
if [[ -d "f-rg" ]]; then
    for test_script in f-rg/test-*.sh; do
        if [[ -f "$test_script" ]]; then
            echo "Running $test_script..."
            if bash "$test_script"; then
                ((passed_tests++))
                echo -e "${GREEN}✓ $test_script passed${NC}"
            else
                ((failed_tests++))
                echo -e "${RED}✗ $test_script failed${NC}"
            fi
            ((total_tests++))
            echo
        fi
    done
fi

# Run other test scripts in the tests directory
for test_script in test-*.sh; do
    if [[ -f "$test_script" && -x "$test_script" ]]; then
        echo "Running $test_script..."
        if ./"$test_script"; then
            ((passed_tests++))
            echo -e "${GREEN}✓ $test_script passed${NC}"
        else
            ((failed_tests++))
            echo -e "${RED}✗ $test_script failed${NC}"
        fi
        ((total_tests++))
        echo
    fi
done

echo "================================"
echo "  Summary"
echo "================================"
echo "Total test suites: $total_tests"
echo -e "Passed: ${GREEN}$passed_tests${NC}"
if [[ $failed_tests -gt 0 ]]; then
    echo -e "Failed: ${RED}$failed_tests${NC}"
    exit 1
else
    echo -e "Failed: ${GREEN}0${NC}"
    echo
    echo -e "${GREEN}All test suites passed!${NC}"
fi



