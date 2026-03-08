#!/usr/bin/env bash
# Run mutation tests on targeted service modules.
#
# Usage:
#   bash scripts/run_mutation_tests.sh          # run + print results
#   bash scripts/run_mutation_tests.sh --html   # run + open HTML report
#
# Target modules (see .mutmut.ini):
#   app/services/sandbox_verdict_calculator.py  -- pure scoring logic (97% coverage)
#   app/services/specialization_validation.py   -- pure validation (98% coverage)
#   app/services/credit_service.py              -- financial logic (high business risk)
#
# Typical runtime: 10–30 min per module.
# Results are cached in .mutmut-cache; re-running only re-tests changed mutants.

set -euo pipefail

echo "=== Mutation Testing — Sprint 42 ==="
echo "Targets: sandbox_verdict_calculator | specialization_validation | credit_service"
echo ""

python -m mutmut run

echo ""
echo "=== Results ==="
python -m mutmut results

if [[ "${1:-}" == "--html" ]]; then
    python -m mutmut html
    echo ""
    echo "HTML report written to: html/index.html"
fi
