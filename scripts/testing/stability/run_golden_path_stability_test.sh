#!/bin/bash

# Golden Path UI E2E Test - Stability Validation Script
# Runs the test 20 times in headless mode and tracks results

TEST_NAME="test_group_knockout_7_players_golden_path_ui"
TEST_FILE="tests/e2e_frontend/test_group_knockout_7_players.py"
ITERATIONS=20
LOG_DIR="/tmp/golden_path_stability_logs"
SUMMARY_FILE="/tmp/golden_path_stability_summary.txt"

# Setup
mkdir -p "$LOG_DIR"
rm -f "$SUMMARY_FILE"

echo "=================================="
echo "Golden Path UI Test - Stability Run"
echo "=================================="
echo "Target: $ITERATIONS consecutive runs"
echo "Mode: Headless (CI-ready validation)"
echo "Logs: $LOG_DIR"
echo "=================================="
echo ""

PASS_COUNT=0
FAIL_COUNT=0

for i in $(seq 1 $ITERATIONS); do
    echo "[$i/$ITERATIONS] Running test..."

    LOG_FILE="$LOG_DIR/run_$(printf "%02d" $i).log"

    DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
        timeout 180 \
        pytest "$TEST_FILE::$TEST_NAME" \
        -v -s --tb=short \
        > "$LOG_FILE" 2>&1

    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        echo "   ✅ PASS (run $i)"
        PASS_COUNT=$((PASS_COUNT + 1))
        echo "PASS,$i" >> "$SUMMARY_FILE"
    else
        echo "   ❌ FAIL (run $i) - Exit code: $EXIT_CODE"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        echo "FAIL,$i,$EXIT_CODE" >> "$SUMMARY_FILE"

        # Extract error from log
        echo "   Error details:" | tee -a "$SUMMARY_FILE"
        grep -A 5 "FAILED\|ERROR\|Failed:" "$LOG_FILE" | head -10 | sed 's/^/      /' | tee -a "$SUMMARY_FILE"
    fi

    # Small delay between runs
    sleep 2
done

echo ""
echo "=================================="
echo "STABILITY TEST RESULTS"
echo "=================================="
echo "Total runs: $ITERATIONS"
echo "✅ PASS: $PASS_COUNT ($((PASS_COUNT * 100 / ITERATIONS))%)"
echo "❌ FAIL: $FAIL_COUNT ($((FAIL_COUNT * 100 / ITERATIONS))%)"
echo "=================================="

if [ $FAIL_COUNT -eq 0 ]; then
    echo "🎉 100% PASS - Test is STABLE and CI-ready!"
    exit 0
else
    echo "⚠️  Test is FLAKY - requires stabilization"
    echo "Check logs in: $LOG_DIR"
    exit 1
fi
