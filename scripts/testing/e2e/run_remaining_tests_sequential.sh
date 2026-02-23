#!/bin/bash
# Run remaining multi-round tests sequentially after SCORE tests complete
# This script waits for SCORE tests to finish, then runs TIME/DISTANCE/PLACEMENT/ROUNDS

set -e

cd "$(dirname "$0")"
source venv/bin/activate

LOG_DIR="/tmp/multi_round_logs"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "========================================"
echo "Sequential Multi-Round Test Runner"
echo "Started: $(date)"
echo "========================================"
echo ""

# Function to run a test group
run_test_group() {
    local keyword=$1
    local description=$2

    echo "========================================"
    echo "Running: $description"
    echo "Started: $(date)"
    echo "========================================"

    GROUP_LOG="$LOG_DIR/${keyword}_${TIMESTAMP}.log"
    START_TIME=$(date +%s)

    # Run tests for this group
    HEADED=1 pytest tests/e2e_frontend/test_tournament_full_ui_workflow.py::test_full_ui_tournament_workflow \
        -k "$keyword" \
        -v --tb=short \
        2>&1 | tee "$GROUP_LOG"

    local exit_code=$?

    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    # Parse results from log
    PASSED=$(grep -c "PASSED" "$GROUP_LOG" 2>/dev/null || echo "0")
    FAILED=$(grep -c "FAILED" "$GROUP_LOG" 2>/dev/null || echo "0")

    echo ""
    echo "Results for $keyword:"
    echo "  ✅ Passed: $PASSED/6"
    echo "  ❌ Failed: $FAILED/6"
    echo "  ⏱️  Duration: ${DURATION}s ($(($DURATION / 60))m $(($DURATION % 60))s)"
    echo "  📄 Log: $GROUP_LOG"
    echo ""

    return $exit_code
}

# Wait for SCORE tests to complete (if still running)
echo "⏳ Checking if SCORE tests are still running..."
while pgrep -f "pytest.*Score" > /dev/null 2>&1; do
    sleep 10
    echo "  ⏳ SCORE tests still running... waiting"
done
echo "✅ SCORE tests completed!"
echo ""

# Run remaining test groups sequentially
run_test_group "Time" "TIME_BASED (6 tests: 1R/2R/3R × League/Knockout)"
run_test_group "Distance" "DISTANCE_BASED (6 tests: 1R/2R/3R × League/Knockout)"
run_test_group "Placement" "PLACEMENT (6 tests: 1R/2R/3R × League/Knockout)"
run_test_group "Rounds" "ROUNDS_BASED (6 tests: 1R/2R/3R × League/Knockout)"

echo "========================================"
echo "All remaining tests complete!"
echo "Finished: $(date)"
echo "========================================"
echo ""
echo "📋 Logs saved to: $LOG_DIR/"
echo ""
echo "Next step: Update MULTI_ROUND_TEST_TRACKING.md with results"
