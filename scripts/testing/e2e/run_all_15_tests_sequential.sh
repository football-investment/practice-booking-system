#!/bin/bash

# Run all 15 INDIVIDUAL tournament E2E tests sequentially in headless mode
# Created: 2026-02-03

echo "================================================================================"
echo "Running All 15 INDIVIDUAL Tournament E2E Tests (Headless Mode)"
echo "================================================================================"
echo ""

# Test configurations in order
TESTS=(
    "T1_Ind_Score_1R"
    "T1_Ind_Score_2R"
    "T1_Ind_Score_3R"
    "T2_Ind_Time_1R"
    "T2_Ind_Time_2R"
    "T2_Ind_Time_3R"
    "T3_Ind_Distance_1R"
    "T3_Ind_Distance_2R"
    "T3_Ind_Distance_3R"
    "T4_Ind_Placement_1R"
    "T4_Ind_Placement_2R"
    "T4_Ind_Placement_3R"
    "T5_Ind_Rounds_1R"
    "T5_Ind_Rounds_2R"
    "T5_Ind_Rounds_3R"
)

PASSED=0
FAILED=0
TOTAL=${#TESTS[@]}

START_TIME=$(date +%s)

# Results array
declare -a RESULTS

for i in "${!TESTS[@]}"; do
    TEST_NUM=$((i + 1))
    TEST_ID="${TESTS[$i]}"

    echo "--------------------------------------------------------------------------------"
    echo "Test $TEST_NUM/$TOTAL: $TEST_ID"
    echo "--------------------------------------------------------------------------------"

    # Run test and capture result
    pytest tests/e2e_frontend/test_tournament_full_ui_workflow.py::test_full_ui_tournament_workflow \
        -k "$TEST_ID" \
        -v \
        --tb=line \
        -q \
        2>&1 | tail -30

    # Check exit code
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        echo "✅ PASSED: $TEST_ID"
        RESULTS[$i]="✅ PASSED"
        ((PASSED++))
    else
        echo "❌ FAILED: $TEST_ID"
        RESULTS[$i]="❌ FAILED"
        ((FAILED++))
    fi

    echo ""
done

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo "================================================================================"
echo "TEST SUITE SUMMARY"
echo "================================================================================"
echo ""
echo "Total Tests:  $TOTAL"
echo "Passed:       $PASSED ($(( PASSED * 100 / TOTAL ))%)"
echo "Failed:       $FAILED ($(( FAILED * 100 / TOTAL ))%)"
echo "Duration:     ${MINUTES}m ${SECONDS}s"
echo ""
echo "Individual Results:"
echo "-------------------"
for i in "${!TESTS[@]}"; do
    TEST_NUM=$((i + 1))
    printf "%2d. %-20s %s\n" "$TEST_NUM" "${TESTS[$i]}" "${RESULTS[$i]}"
done
echo ""
echo "================================================================================"

if [ $FAILED -eq 0 ]; then
    echo "🎉 ALL TESTS PASSED!"
    exit 0
else
    echo "⚠️  Some tests failed - review logs above"
    exit 1
fi
