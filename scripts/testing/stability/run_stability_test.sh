#!/bin/bash
# Golden Path 10x Stability Test
# Date: 2026-02-08

echo "=========================================="
echo "Golden Path 10x Stability Test"
echo "=========================================="
echo ""

PASS_COUNT=0
FAIL_COUNT=0
TOTAL_TIME=0

for i in {1..10}; do
  echo "Run #$i:"
  START=$(date +%s)
  
  source venv/bin/activate && pytest tests/e2e/golden_path/test_golden_path_api_based.py -v --tb=short > golden_path_run_${i}.log 2>&1
  EXIT_CODE=$?
  
  END=$(date +%s)
  DURATION=$((END - START))
  TOTAL_TIME=$((TOTAL_TIME + DURATION))
  
  if [ $EXIT_CODE -eq 0 ]; then
    echo "  ✅ PASSED (${DURATION}s)"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ❌ FAILED (${DURATION}s)"
    FAIL_COUNT=$((FAIL_COUNT + 1))
    echo "  Error log: golden_path_run_${i}.log"
  fi
  
  sleep 2
done

echo ""
echo "=========================================="
echo "Results:"
echo "=========================================="
echo "Total runs: 10"
echo "Passed: $PASS_COUNT"
echo "Failed: $FAIL_COUNT"
echo "Pass rate: $((PASS_COUNT * 100 / 10))%"
echo "Average time: $((TOTAL_TIME / 10))s"
echo ""

if [ $PASS_COUNT -eq 10 ]; then
  echo "✅ Golden Path is 100% STABLE"
  exit 0
else
  echo "❌ Golden Path is UNSTABLE (< 100% pass rate)"
  echo "Failed runs:"
  for i in {1..10}; do
    if grep -q "FAILED" golden_path_run_${i}.log 2>/dev/null; then
      echo "  - Run #$i: $(grep -m1 "FAILED\|ERROR" golden_path_run_${i}.log)"
    fi
  done
  exit 1
fi
