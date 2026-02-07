#!/bin/bash
# TRUE GOLDEN PATH E2E STABILITY TEST: 20 Consecutive Runs
# Validates COMPLETE tournament lifecycle reliability

set -e

TEST_FILE="test_true_golden_path_e2e.py::test_true_golden_path_full_lifecycle"
LOG_DIR="/tmp/true_golden_path_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

PASS_COUNT=0
FAIL_COUNT=0

echo "=========================================="
echo "🏆 TRUE GOLDEN PATH E2E: 20 Runs"
echo "=========================================="
echo "Test: Complete Tournament Lifecycle"
echo "Scope: Creation → Results → Finalization → Completion → Rewards"
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
        tail -100 "$LOG_FILE" > "$LOG_DIR/failure_run_$(printf '%02d' $i).txt"
    fi

    echo ""
    sleep 2
done

echo "=========================================="
echo "📊 TRUE GOLDEN PATH E2E RESULTS"
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
    echo "   ✅ Full tournament lifecycle deterministic"
    echo "   ✅ Release-critical reliability requirement MET"
    exit 0
elif [ $PASS_COUNT -ge 18 ]; then
    echo "⚠️  90%+ STABILITY - Minor flakiness detected"
    echo "   Review failure logs before release"
    exit 1
else
    echo "❌ INSTABILITY DETECTED - NOT PRODUCTION READY"
    echo "   Review and fix failures immediately"
    exit 1
fi
