#!/bin/bash
# Stability Log Analysis - Detect Flaky Test Warning Signs
# Usage: ./analyze_stability_logs.sh [stability|production]

MODE=${1:-stability}

if [ "$MODE" = "production" ]; then
    echo "═══════════════════════════════════════════════════════════"
    echo "📊 PRODUCTION STABILITY LOG ANALYSIS"
    echo "═══════════════════════════════════════════════════════════"
    TOTAL_RUNS=10
    LOG_PREFIX="production_run"
elif [ "$MODE" = "ci-sim" ]; then
    echo "═══════════════════════════════════════════════════════════"
    echo "📊 CI SIMULATION LOG ANALYSIS"
    echo "═══════════════════════════════════════════════════════════"
    TOTAL_RUNS=5
    LOG_PREFIX="ci_sim_run"
else
    echo "═══════════════════════════════════════════════════════════"
    echo "📊 STABILITY LOG ANALYSIS - Warning Signs Detection"
    echo "═══════════════════════════════════════════════════════════"
    TOTAL_RUNS=5
    LOG_PREFIX="stability_run"
fi

echo ""

ISSUES_FOUND=0

# Color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

for i in $(seq 1 $TOTAL_RUNS); do
    LOG="/tmp/${LOG_PREFIX}_${i}.log"

    if [ ! -f "$LOG" ]; then
        echo "⏳ Run $i: Log not yet created"
        continue
    fi

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔍 Analyzing Run $i"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Extract test result
    RESULT=$(grep -E "^=+.*passed.*=+$|^=+.*failed.*=+$" "$LOG" | tail -1)
    echo "📋 Result: $RESULT"

    # Check for retries
    RETRIES=$(grep -c "retry\|retrying\|attempt" "$LOG" 2>/dev/null || echo "0")
    if [ "$RETRIES" -gt 0 ]; then
        echo -e "${YELLOW}⚠️  WARNING: $RETRIES retry mentions found${NC}"
        grep -n "retry\|retrying\|attempt" "$LOG" | head -3
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    else
        echo -e "${GREEN}✅ No retries detected${NC}"
    fi

    # Check for timeout warnings
    TIMEOUTS=$(grep -c "timeout\|TimeoutError\|timed out" "$LOG" 2>/dev/null || echo "0")
    if [ "$TIMEOUTS" -gt 0 ]; then
        echo -e "${YELLOW}⚠️  WARNING: $TIMEOUTS timeout mentions found${NC}"
        grep -n "timeout\|TimeoutError\|timed out" "$LOG" | head -3
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    else
        echo -e "${GREEN}✅ No timeouts detected${NC}"
    fi

    # Check for selector/element not found issues
    SELECTORS=$(grep -c "not found\|unable to locate\|ElementNotFound\|element is not attached" "$LOG" 2>/dev/null || echo "0")
    if [ "$SELECTORS" -gt 0 ]; then
        echo -e "${YELLOW}⚠️  WARNING: $SELECTORS selector issues found${NC}"
        grep -n "not found\|unable to locate\|ElementNotFound" "$LOG" | head -3
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    else
        echo -e "${GREEN}✅ No selector issues detected${NC}"
    fi

    # Check for unexpected errors (ERROR level logs)
    ERRORS=$(grep -c "^ERROR\|Exception\|Traceback" "$LOG" 2>/dev/null || echo "0")
    if [ "$ERRORS" -gt 0 ]; then
        echo -e "${RED}❌ ERROR: $ERRORS error messages found${NC}"
        grep -n "^ERROR\|Exception\|Traceback" "$LOG" | head -3
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    else
        echo -e "${GREEN}✅ No errors detected${NC}"
    fi

    # Check for warnings
    WARNINGS=$(grep -c "WARNING\|⚠️" "$LOG" 2>/dev/null || echo "0")
    if [ "$WARNINGS" -gt 10 ]; then  # Allow some warnings (expected from sandbox mode)
        echo -e "${YELLOW}⚠️  INFO: $WARNINGS warnings found (>10 threshold)${NC}"
    else
        echo -e "${GREEN}✅ Warning count acceptable ($WARNINGS)${NC}"
    fi

    # Check for network/API issues (NEW)
    API_SLOW=$(grep -c "slow\|latency\|took.*ms" "$LOG" 2>/dev/null || echo "0")
    API_ERRORS=$(grep -c "5[0-9][0-9]\|500\|502\|503\|504\|Connection refused\|Connection reset" "$LOG" 2>/dev/null || echo "0")
    API_RETRIES=$(grep -c "retry.*request\|retrying.*api\|retry.*http" "$LOG" 2>/dev/null || echo "0")

    if [ "$API_SLOW" -gt 5 ] || [ "$API_ERRORS" -gt 0 ] || [ "$API_RETRIES" -gt 0 ]; then
        echo -e "${YELLOW}⚠️  NETWORK: Slow=$API_SLOW, 5xx Errors=$API_ERRORS, API Retries=$API_RETRIES${NC}"
        if [ "$API_ERRORS" -gt 0 ]; then
            grep -n "5[0-9][0-9]\|Connection refused\|Connection reset" "$LOG" | head -3
        fi
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    else
        echo -e "${GREEN}✅ No network/API issues detected${NC}"
    fi

    # Extract runtime
    RUNTIME=$(grep -oP '\d+\.\d+s' "$LOG" | tail -1 || echo "N/A")
    echo "⏱️  Runtime: $RUNTIME"

    echo ""
done

echo "═══════════════════════════════════════════════════════════"
echo "📊 SUMMARY"
echo "═══════════════════════════════════════════════════════════"
echo ""

if [ "$ISSUES_FOUND" -eq 0 ]; then
    echo -e "${GREEN}✅ CLEAN - No warning signs detected${NC}"
    echo "   All runs appear deterministic and stable"
else
    echo -e "${YELLOW}⚠️  $ISSUES_FOUND potential issues detected${NC}"
    echo "   Review warnings above for flaky test indicators"
fi

echo ""
echo "Full logs available at:"
echo "  /tmp/stability_run_{1..5}.log"
echo "  /tmp/stability_summary.log"
