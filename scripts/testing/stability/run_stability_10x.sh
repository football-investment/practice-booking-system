#!/bin/bash
# Stability Test: Run Golden Path E2E 10 consecutive times
# Track PASS/FAIL rate to validate production reliability

set -e

TEST_FILE="tests/e2e_frontend/test_group_knockout_7_players.py::test_group_knockout_7_players_golden_path_ui"
LOG_DIR="/tmp/stability_tests_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

PASS_COUNT=0
FAIL_COUNT=0

echo "=========================================="
echo "🔬 STABILITY TEST: 10 Consecutive Runs"
echo "=========================================="
echo "Test: $TEST_FILE"
echo "Logs: $LOG_DIR"
echo ""

for i in {1..10}; do
    echo "----------------------------------------"
    echo "Run #$i of 10"
    echo "----------------------------------------"

    LOG_FILE="$LOG_DIR/run_$(printf '%02d' $i).log"

    if /Users/lovas.zoltan/Seafile/Football\ Investment/Projects/Football\ Investment\ Internship/practice_booking_system/venv/bin/pytest \
        "$TEST_FILE" \
        -v \
        --tb=short \
        > "$LOG_FILE" 2>&1; then
        echo "✅ PASS"
        ((PASS_COUNT++))
    else
        echo "❌ FAIL"
        ((FAIL_COUNT++))
        # Save failure details
        tail -100 "$LOG_FILE" > "$LOG_DIR/failure_run_$(printf '%02d' $i).txt"
    fi

    echo ""
    sleep 2  # Brief pause between runs
done

echo "=========================================="
echo "📊 STABILITY TEST RESULTS"
echo "=========================================="
echo "Total Runs: 10"
echo "✅ PASSED: $PASS_COUNT"
echo "❌ FAILED: $FAIL_COUNT"
echo "Success Rate: $((PASS_COUNT * 10))%"
echo ""
echo "Logs saved to: $LOG_DIR"
echo "=========================================="

if [ $PASS_COUNT -eq 10 ]; then
    echo "🎉 100% STABILITY ACHIEVED"
    exit 0
else
    echo "⚠️  INSTABILITY DETECTED - Review failure logs"
    exit 1
fi
