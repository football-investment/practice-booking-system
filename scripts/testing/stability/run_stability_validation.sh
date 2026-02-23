#!/bin/bash
# 5-Run Stability Validation for E2E Test Suite
# Detects flaky tests, timing issues, and determinism

set -e

RUNS=5
PROJECT_DIR="/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Investment Internship/practice_booking_system"

cd "$PROJECT_DIR"
source venv/bin/activate

echo "═══════════════════════════════════════════════════════════"
echo "🔄 STABILITY VALIDATION - 5 Consecutive Runs"
echo "═══════════════════════════════════════════════════════════"
echo "Start Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Expected Duration: ~40 minutes (5 × 8 min)"
echo ""

# Summary file
SUMMARY="/tmp/stability_validation_summary.txt"
echo "Stability Validation - $(date '+%Y-%m-%d %H:%M:%S')" > "$SUMMARY"
echo "═══════════════════════════════════════════════════════════" >> "$SUMMARY"
echo "" >> "$SUMMARY"

for i in $(seq 1 $RUNS); do
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔄 STABILITY RUN $i/$RUNS - $(date '+%H:%M:%S')"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    LOG_FILE="/tmp/stability_run_${i}.log"
    START_TIME=$(date +%s)

    # Run tests
    pytest tests/e2e_frontend/test_tournament_full_ui_workflow.py::test_full_ui_tournament_workflow \
        -v --tb=line 2>&1 | tee "$LOG_FILE"

    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    MINUTES=$((DURATION / 60))
    SECONDS=$((DURATION % 60))

    # Extract result
    RESULT=$(grep -E "^=+.*(passed|failed).*=+$" "$LOG_FILE" | tail -1 || echo "UNKNOWN")

    echo "" | tee -a "$SUMMARY"
    echo "Run $i: $RESULT (${MINUTES}m ${SECONDS}s)" | tee -a "$SUMMARY"

    # Quick analysis
    RETRIES=$(grep -c "retry\|retrying" "$LOG_FILE" 2>/dev/null || echo "0")
    TIMEOUTS=$(grep -c "timeout\|TimeoutError" "$LOG_FILE" 2>/dev/null || echo "0")
    ERRORS=$(grep -c "^ERROR\|Exception" "$LOG_FILE" 2>/dev/null || echo "0")

    if [ "$RETRIES" -gt 0 ] || [ "$TIMEOUTS" -gt 0 ] || [ "$ERRORS" -gt 0 ]; then
        echo "  ⚠️  Warning signs: Retries=$RETRIES, Timeouts=$TIMEOUTS, Errors=$ERRORS" | tee -a "$SUMMARY"
    else
        echo "  ✅ Clean run (no warning signs)" | tee -a "$SUMMARY"
    fi

    echo "  Log: $LOG_FILE" | tee -a "$SUMMARY"
done

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ STABILITY VALIDATION COMPLETE"
echo "═══════════════════════════════════════════════════════════"
echo "End Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "📊 Summary saved to: $SUMMARY"
echo "📋 Individual logs: /tmp/stability_run_{1..5}.log"
echo ""
echo "Run detailed analysis:"
echo "  ./analyze_stability_logs.sh"
