#!/bin/bash
# Phase 1 Stability Test: 20 Consecutive Runs
# Validates tournament creation determinism

set -e

TEST_FILE="test_phase1_creation_only.py::test_tournament_creation_phase1_only"
LOG_DIR="/tmp/phase1_stability_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

PASS_COUNT=0
FAIL_COUNT=0

echo "=========================================="
echo "🎯 PHASE 1 STABILITY: 20 Consecutive Runs"
echo "=========================================="
echo "Target: Tournament Creation (Phase 1 Only)"
echo "Logs: $LOG_DIR"
echo ""

for i in {1..20}; do
    echo "----------------------------------------"
    echo "Run #$i of 20"
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
        tail -50 "$LOG_FILE" > "$LOG_DIR/failure_run_$(printf '%02d' $i).txt"
    fi

    sleep 1
done

echo ""
echo "=========================================="
echo "📊 PHASE 1 STABILITY RESULTS"
echo "=========================================="
echo "Total Runs: 20"
echo "✅ PASSED: $PASS_COUNT"
echo "❌ FAILED: $FAIL_COUNT"
echo "Success Rate: $((PASS_COUNT * 5))%"
echo ""
echo "Logs: $LOG_DIR"
echo "=========================================="

if [ $PASS_COUNT -eq 20 ]; then
    echo "🎉 100% STABILITY ACHIEVED - PRODUCTION READY"
    exit 0
elif [ $PASS_COUNT -ge 18 ]; then
    echo "⚠️  90%+ STABILITY - Minor flakiness detected"
    exit 1
else
    echo "❌ INSTABILITY DETECTED - Review failures"
    exit 1
fi
