#!/bin/bash
# CI Speed Measurement
# Date: 2026-02-08

echo "=========================================="
echo "CI Speed Baseline Measurement"
echo "=========================================="
echo ""

# 1. Smoke Suite
echo "1️⃣ Measuring Smoke Suite..."
START=$(date +%s)
source venv/bin/activate && pytest -m smoke -v --tb=short > smoke_suite.log 2>&1
EXIT_CODE=$?
END=$(date +%s)
SMOKE_TIME=$((END - START))
SMOKE_COUNT=$(grep -c "PASSED\|FAILED" smoke_suite.log || echo "0")

if [ $EXIT_CODE -eq 0 ]; then
  echo "   ✅ PASSED (${SMOKE_TIME}s, ${SMOKE_COUNT} tests)"
else
  echo "   ❌ FAILED (${SMOKE_TIME}s)"
fi
echo ""

# 2. Full Suite (sequential)
echo "2️⃣ Measuring Full Suite (sequential)..."
START=$(date +%s)
source venv/bin/activate && pytest tests/ -v --tb=short > full_suite_sequential.log 2>&1
EXIT_CODE_SEQ=$?
END=$(date +%s)
FULL_SEQ_TIME=$((END - START))
FULL_SEQ_COUNT=$(grep -c "PASSED\|FAILED" full_suite_sequential.log || echo "0")

if [ $EXIT_CODE_SEQ -eq 0 ]; then
  echo "   ✅ PASSED (${FULL_SEQ_TIME}s, ${FULL_SEQ_COUNT} tests)"
else
  echo "   ⚠️  COMPLETED WITH ERRORS (${FULL_SEQ_TIME}s)"
fi
echo ""

# 3. Full Suite (parallel)
echo "3️⃣ Measuring Full Suite (parallel -n auto)..."
START=$(date +%s)
source venv/bin/activate && pytest tests/ -v -n auto --tb=short > full_suite_parallel.log 2>&1
EXIT_CODE_PAR=$?
END=$(date +%s)
FULL_PAR_TIME=$((END - START))
FULL_PAR_COUNT=$(grep -c "PASSED\|FAILED" full_suite_parallel.log || echo "0")

if [ $EXIT_CODE_PAR -eq 0 ]; then
  echo "   ✅ PASSED (${FULL_PAR_TIME}s, ${FULL_PAR_COUNT} tests)"
else
  echo "   ⚠️  COMPLETED WITH ERRORS (${FULL_PAR_TIME}s)"
fi
echo ""

# Summary
echo "=========================================="
echo "Summary:"
echo "=========================================="
echo "Smoke Suite:          ${SMOKE_TIME}s (${SMOKE_COUNT} tests)"
echo "Full Suite (seq):     ${FULL_SEQ_TIME}s (${FULL_SEQ_COUNT} tests)"
echo "Full Suite (parallel): ${FULL_PAR_TIME}s (${FULL_PAR_COUNT} tests)"
echo ""
echo "Speedup (parallel):   $((FULL_SEQ_TIME / FULL_PAR_TIME))x faster"
echo ""
echo "Targets:"
echo "  Smoke:     < 120s  $([ $SMOKE_TIME -lt 120 ] && echo "✅" || echo "❌")"
echo "  Full:      < 600s  $([ $FULL_PAR_TIME -lt 600 ] && echo "✅" || echo "❌")"
echo ""
