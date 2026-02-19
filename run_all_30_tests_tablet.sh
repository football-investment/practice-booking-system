#!/bin/bash
# Run ALL 30 multi-round E2E tests sequentially in HEADED mode (tablet viewport: 1024x768)
# This script runs tests one group at a time for complete visual validation

set -e

cd "$(dirname "$0")"
source venv/bin/activate

LOG_DIR="/tmp/multi_round_logs"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MASTER_LOG="$LOG_DIR/master_${TIMESTAMP}.log"

echo "========================================" | tee -a "$MASTER_LOG"
echo "Multi-Round E2E Test Suite - HEADED Mode (Tablet: 1024x768)" | tee -a "$MASTER_LOG"
echo "Started: $(date)" | tee -a "$MASTER_LOG"
echo "Total configs: 30 (5 scoring types × 2 formats × 3 rounds)" | tee -a "$MASTER_LOG"
echo "Viewport: 1024x768 (iPad size)" | tee -a "$MASTER_LOG"
echo "========================================" | tee -a "$MASTER_LOG"
echo "" | tee -a "$MASTER_LOG"

# Function to run a test group
run_test_group() {
    local keyword=$1
    local description=$2
    local expected_count=$3

    echo "========================================" | tee -a "$MASTER_LOG"
    echo "Running: $description" | tee -a "$MASTER_LOG"
    echo "Started: $(date)" | tee -a "$MASTER_LOG"
    echo "========================================" | tee -a "$MASTER_LOG"

    GROUP_LOG="$LOG_DIR/${keyword}_${TIMESTAMP}.log"
    START_TIME=$(date +%s)

    # Run tests for this group
    HEADED=1 pytest tests/e2e_frontend/test_tournament_full_ui_workflow.py::test_full_ui_tournament_workflow \
        -k "$keyword" \
        -v --tb=short \
        --junit-xml="$LOG_DIR/${keyword}_junit.xml" \
        2>&1 | tee "$GROUP_LOG"

    local exit_code=$?

    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    # Parse results from log
    PASSED=$(grep -c "PASSED" "$GROUP_LOG" 2>/dev/null || echo "0")
    FAILED=$(grep -c "FAILED" "$GROUP_LOG" 2>/dev/null || echo "0")

    echo "" | tee -a "$MASTER_LOG"
    echo "Results for $keyword:" | tee -a "$MASTER_LOG"
    echo "  ✅ Passed: $PASSED/$expected_count" | tee -a "$MASTER_LOG"
    echo "  ❌ Failed: $FAILED/$expected_count" | tee -a "$MASTER_LOG"
    echo "  ⏱️  Duration: ${DURATION}s ($(($DURATION / 60))m $(($DURATION % 60))s)" | tee -a "$MASTER_LOG"
    echo "  📄 Log: $GROUP_LOG" | tee -a "$MASTER_LOG"
    echo "" | tee -a "$MASTER_LOG"

    return $exit_code
}

# Run all test groups sequentially
run_test_group "Score" "SCORE_BASED (6 tests: 1R/2R/3R × League/Knockout)" 6
run_test_group "Time" "TIME_BASED (6 tests: 1R/2R/3R × League/Knockout)" 6
run_test_group "Distance" "DISTANCE_BASED (6 tests: 1R/2R/3R × League/Knockout)" 6
run_test_group "Placement" "PLACEMENT (6 tests: 1R/2R/3R × League/Knockout)" 6
run_test_group "Rounds" "ROUNDS_BASED (6 tests: 1R/2R/3R × League/Knockout)" 6

# Generate final summary
echo "========================================" | tee -a "$MASTER_LOG"
echo "FINAL RESULTS - ALL 30 TESTS" | tee -a "$MASTER_LOG"
echo "========================================" | tee -a "$MASTER_LOG"

TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_DURATION=0

for log_file in "$LOG_DIR"/*_${TIMESTAMP}.log; do
    if [ -f "$log_file" ]; then
        PASSED=$(grep -c "PASSED" "$log_file" 2>/dev/null || echo "0")
        FAILED=$(grep -c "FAILED" "$log_file" 2>/dev/null || echo "0")
        TOTAL_PASSED=$((TOTAL_PASSED + PASSED))
        TOTAL_FAILED=$((TOTAL_FAILED + FAILED))

        # Extract duration from log (pytest summary line)
        DURATION=$(grep -oP 'in \K[0-9]+\.[0-9]+s' "$log_file" | tail -1 | sed 's/s//' || echo "0")
        TOTAL_DURATION=$(echo "$TOTAL_DURATION + $DURATION" | bc 2>/dev/null || echo "$TOTAL_DURATION")
    fi
done

echo "✅ Total Passed: $TOTAL_PASSED/30" | tee -a "$MASTER_LOG"
echo "❌ Total Failed: $TOTAL_FAILED/30" | tee -a "$MASTER_LOG"
echo "📊 Pass Rate: $(( TOTAL_PASSED * 100 / 30 ))%" | tee -a "$MASTER_LOG"
echo "⏱️  Total Duration: ${TOTAL_DURATION}s" | tee -a "$MASTER_LOG"
echo "" | tee -a "$MASTER_LOG"
echo "Completed: $(date)" | tee -a "$MASTER_LOG"
echo "📋 Master log: $MASTER_LOG" | tee -a "$MASTER_LOG"
echo "📁 All logs: $LOG_DIR/" | tee -a "$MASTER_LOG"
echo "========================================" | tee -a "$MASTER_LOG"

# Generate summary table for MULTI_ROUND_TEST_TRACKING.md
echo "" | tee -a "$MASTER_LOG"
echo "📊 Summary by Scoring Type:" | tee -a "$MASTER_LOG"
echo "---" | tee -a "$MASTER_LOG"

for scoring_type in Score Time Distance Placement Rounds; do
    log_file="$LOG_DIR/${scoring_type}_${TIMESTAMP}.log"
    if [ -f "$log_file" ]; then
        PASSED=$(grep -c "PASSED" "$log_file" 2>/dev/null || echo "0")
        FAILED=$(grep -c "FAILED" "$log_file" 2>/dev/null || echo "0")
        echo "  $scoring_type: $PASSED passed, $FAILED failed" | tee -a "$MASTER_LOG"
    fi
done

echo "" | tee -a "$MASTER_LOG"
echo "🎉 Multi-round test suite complete!" | tee -a "$MASTER_LOG"
echo "📋 Next: Update MULTI_ROUND_TEST_TRACKING.md with results from logs" | tee -a "$MASTER_LOG"
