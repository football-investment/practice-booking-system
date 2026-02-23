#!/bin/bash
# 10-Run Production Stability Validation for E2E Test Suite
# Production-grade stability proof (not just smoke test)

set -e

RUNS=10
PROJECT_DIR="/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Investment Internship/practice_booking_system"

cd "$PROJECT_DIR"
source venv/bin/activate

echo "═══════════════════════════════════════════════════════════"
echo "🎯 PRODUCTION STABILITY VALIDATION - 10 Consecutive Runs"
echo "═══════════════════════════════════════════════════════════"
echo "Start Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Expected Duration: ~80 minutes (10 × 8 min)"
echo ""
echo "Target: 10/10 runs × 8/8 tests = 80/80 PASS (100%)"
echo "Quality: 0 retries, 0 timeouts, 0 network issues"
echo ""

# Summary file
SUMMARY="/tmp/production_stability_summary.txt"
echo "Production Stability Validation - $(date '+%Y-%m-%d %H:%M:%S')" > "$SUMMARY"
echo "═══════════════════════════════════════════════════════════" >> "$SUMMARY"
echo "" >> "$SUMMARY"

PASS_COUNT=0
FAIL_COUNT=0
TOTAL_DURATION=0

for i in $(seq 1 $RUNS); do
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔄 RUN $i/$RUNS - $(date '+%H:%M:%S')"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    LOG_FILE="/tmp/production_run_${i}.log"
    START_TIME=$(date +%s)

    # Run tests
    set +e  # Don't exit on test failure
    pytest tests/e2e_frontend/test_tournament_full_ui_workflow.py::test_full_ui_tournament_workflow \
        -v --tb=line 2>&1 | tee "$LOG_FILE"
    TEST_EXIT_CODE=$?
    set -e

    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    TOTAL_DURATION=$((TOTAL_DURATION + DURATION))
    MINUTES=$((DURATION / 60))
    SECONDS=$((DURATION % 60))

    # Extract result
    if grep -q "8 passed" "$LOG_FILE"; then
        RESULT="✅ 8 PASSED"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        RESULT="❌ FAILED"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi

    echo "" | tee -a "$SUMMARY"
    echo "Run $i: $RESULT (${MINUTES}m ${SECONDS}s)" | tee -a "$SUMMARY"

    # Quality checks
    RETRIES=$(grep -c "retry\|retrying" "$LOG_FILE" 2>/dev/null || echo "0")
    TIMEOUTS=$(grep -c "timeout\|TimeoutError" "$LOG_FILE" 2>/dev/null || echo "0")
    ERRORS=$(grep -c "^ERROR\|Exception" "$LOG_FILE" 2>/dev/null || echo "0")
    NETWORK=$(grep -c "5[0-9][0-9]\|Connection refused" "$LOG_FILE" 2>/dev/null || echo "0")

    WARNINGS=""
    [ "$RETRIES" -gt 0 ] && WARNINGS="${WARNINGS}Retries=$RETRIES "
    [ "$TIMEOUTS" -gt 0 ] && WARNINGS="${WARNINGS}Timeouts=$TIMEOUTS "
    [ "$ERRORS" -gt 0 ] && WARNINGS="${WARNINGS}Errors=$ERRORS "
    [ "$NETWORK" -gt 0 ] && WARNINGS="${WARNINGS}Network=$NETWORK "

    if [ -n "$WARNINGS" ]; then
        echo "  ⚠️  Warning signs: $WARNINGS" | tee -a "$SUMMARY"
    else
        echo "  ✅ Clean run" | tee -a "$SUMMARY"
    fi

    echo "  Log: $LOG_FILE" | tee -a "$SUMMARY"

    # Intermediate summary every 5 runs
    if [ $((i % 5)) -eq 0 ]; then
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "📊 INTERMEDIATE SUMMARY - After $i runs"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Passed: $PASS_COUNT/$i"
        echo "Failed: $FAIL_COUNT/$i"
        AVG_TIME=$((TOTAL_DURATION / i / 60))
        echo "Avg Runtime: ${AVG_TIME}m"
        echo ""
    fi
done

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ PRODUCTION STABILITY VALIDATION COMPLETE"
echo "═══════════════════════════════════════════════════════════"
echo "End Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 FINAL RESULTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Total Runs: $RUNS"
echo "Passed: $PASS_COUNT"
echo "Failed: $FAIL_COUNT"
echo "Success Rate: $((PASS_COUNT * 100 / RUNS))%"
AVG_TIME=$((TOTAL_DURATION / RUNS / 60))
echo "Average Runtime: ${AVG_TIME}m"
echo ""

if [ "$PASS_COUNT" -eq "$RUNS" ]; then
    echo "🎉 VERDICT: PRODUCTION READY - 100% pass rate across 10 runs"
    echo "   Suite is deterministic and stable"
elif [ "$PASS_COUNT" -ge 9 ]; then
    echo "⚠️  VERDICT: MOSTLY STABLE - $PASS_COUNT/$RUNS pass rate"
    echo "   Some flaky tests detected, review logs"
else
    echo "❌ VERDICT: UNSTABLE - $PASS_COUNT/$RUNS pass rate"
    echo "   Significant instability, requires debugging"
fi

echo ""
echo "📋 Detailed Analysis:"
echo "  ./analyze_stability_logs.sh (run on production_run_*.log)"
echo ""
echo "📊 Summary: $SUMMARY"
echo "📁 Logs: /tmp/production_run_{1..10}.log"
