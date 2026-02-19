#!/bin/bash
# Real-time stability validation monitor

echo "═══════════════════════════════════════════════════════════"
echo "📊 STABILITY VALIDATION - LIVE MONITOR"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Check which run is currently active
for i in {1..5}; do
    LOG="/tmp/stability_run_${i}.log"

    if [ -f "$LOG" ]; then
        # Check if this run is complete
        if grep -q "passed\|failed" "$LOG" 2>/dev/null; then
            RESULT=$(grep -E "^=+.*(passed|failed).*=+$" "$LOG" | tail -1)
            echo "✅ Run $i: COMPLETE - $RESULT"
        else
            # This run is in progress
            CURRENT_TEST=$(grep -oP "test_tournament_full_ui_workflow\[.*?\]" "$LOG" | tail -1)
            PASSED=$(grep -c "PASSED" "$LOG" || echo "0")
            echo "⏳ Run $i: IN PROGRESS - $PASSED tests passed, current: $CURRENT_TEST"

            # Show last few lines
            echo "   Last activity:"
            tail -3 "$LOG" | sed 's/^/     /'
        fi
    else
        echo "⏸️  Run $i: NOT STARTED"
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "View live output: tail -f /tmp/stability_run_1.log"
echo "Full logs: ls -lh /tmp/stability_run_*.log"
