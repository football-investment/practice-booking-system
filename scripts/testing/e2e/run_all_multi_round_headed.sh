#!/bin/bash
# Run ALL 30 multi-round E2E tests in HEADED mode sequentially
# This allows visual validation of UI behavior across all scoring types and round counts

set -e

cd "$(dirname "$0")"
source venv/bin/activate

LOG_DIR="/tmp/multi_round_logs"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MASTER_LOG="$LOG_DIR/master_${TIMESTAMP}.log"

echo "========================================" | tee -a "$MASTER_LOG"
echo "Multi-Round E2E Test Suite - HEADED Mode" | tee -a "$MASTER_LOG"
echo "Started: $(date)" | tee -a "$MASTER_LOG"
echo "Total configs: 30 (5 scoring types × 2 formats × 3 rounds)" | tee -a "$MASTER_LOG"
echo "========================================" | tee -a "$MASTER_LOG"
echo "" | tee -a "$MASTER_LOG"

# Test groups (run sequentially by scoring type)
declare -a TEST_GROUPS=(
    "Score:SCORE_BASED (6 tests)"
    "Time:TIME_BASED (6 tests)"
    "Distance:DISTANCE_BASED (6 tests)"
    "Placement:PLACEMENT (6 tests)"
    "Rounds:ROUNDS_BASED (6 tests)"
)

TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_DURATION=0

for group in "${TEST_GROUPS[@]}"; do
    IFS=':' read -r keyword description <<< "$group"

    echo "========================================" | tee -a "$MASTER_LOG"
    echo "Running: $description" | tee -a "$MASTER_LOG"
    echo "========================================" | tee -a "$MASTER_LOG"

    GROUP_LOG="$LOG_DIR/${keyword}_${TIMESTAMP}.log"
    START_TIME=$(date +%s)

    # Run tests for this group
    if HEADED=1 pytest tests/e2e_frontend/test_tournament_full_ui_workflow.py::test_full_ui_tournament_workflow \
        -k "$keyword" \
        -v --tb=short \
        --junit-xml="$LOG_DIR/${keyword}_junit.xml" \
        2>&1 | tee "$GROUP_LOG"; then

        RESULT="✅ PASSED"
        ((TOTAL_PASSED += 6))
    else
        RESULT="❌ FAILED"
        ((TOTAL_FAILED += 6))
    fi

    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    TOTAL_DURATION=$((TOTAL_DURATION + DURATION))

    echo "" | tee -a "$MASTER_LOG"
    echo "Result: $RESULT" | tee -a "$MASTER_LOG"
    echo "Duration: ${DURATION}s" | tee -a "$MASTER_LOG"
    echo "Log: $GROUP_LOG" | tee -a "$MASTER_LOG"
    echo "" | tee -a "$MASTER_LOG"
done

echo "========================================" | tee -a "$MASTER_LOG"
echo "FINAL RESULTS" | tee -a "$MASTER_LOG"
echo "========================================" | tee -a "$MASTER_LOG"
echo "Total Passed: $TOTAL_PASSED/30" | tee -a "$MASTER_LOG"
echo "Total Failed: $TOTAL_FAILED/30" | tee -a "$MASTER_LOG"
echo "Total Duration: ${TOTAL_DURATION}s ($(($TOTAL_DURATION / 60))m $(($TOTAL_DURATION % 60))s)" | tee -a "$MASTER_LOG"
echo "Completed: $(date)" | tee -a "$MASTER_LOG"
echo "" | tee -a "$MASTER_LOG"
echo "Master log: $MASTER_LOG" | tee -a "$MASTER_LOG"
echo "Individual logs: $LOG_DIR/" | tee -a "$MASTER_LOG"
echo "========================================" | tee -a "$MASTER_LOG"

# Generate summary report
python3 << 'EOF'
import json
import os
from pathlib import Path

log_dir = Path("/tmp/multi_round_logs")
junit_files = list(log_dir.glob("*_junit.xml"))

print("\n📊 JUnit Test Results Summary:")
for junit_file in sorted(junit_files):
    print(f"  - {junit_file.name}")

print(f"\n✅ All test logs saved to: {log_dir}")
EOF

echo ""
echo "🎉 Multi-round test suite complete!"
echo "📋 Update MULTI_ROUND_TEST_TRACKING.md with results"
