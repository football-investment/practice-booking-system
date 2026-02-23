# Performance Testing

This directory contains load tests for establishing performance baselines and detecting regressions.

## Quick Start

### 1. Smoke Test (1 user, 10s)
```bash
locust -f tests/performance/locustfile.py --host=http://localhost:8000 \
       --users=1 --spawn-rate=1 --run-time=10s --headless
```

### 2. Baseline Test (10 users, 60s)
```bash
locust -f tests/performance/locustfile.py --host=http://localhost:8000 \
       --users=10 --spawn-rate=2 --run-time=60s --headless \
       --csv=tests/performance/baseline_results \
       --html=tests/performance/baseline_report.html
```

### 3. Review Results
```bash
cat tests/performance/baseline_results_stats.csv
open tests/performance/baseline_report.html  # macOS
```

## Baseline Metrics

**Target Performance (Tournament Creation API):**
- p50 latency: < 500ms
- p95 latency: < 1500ms
- p99 latency: < 3000ms
- RPS (10 users): > 5 req/s
- Error rate: < 1%

## Documentation

See [PERFORMANCE_BASELINE_SPECIFICATION.md](../../PERFORMANCE_BASELINE_SPECIFICATION.md) for:
- Complete performance testing strategy
- API endpoint latency targets
- Load test execution guide
- CI performance gate design

## Current Coverage

- ✅ **Week 4:** Tournament creation baseline (locustfile.py)
- ⏳ **Week 5:** Student enrollment load test (planned)
- ⏳ **Week 6:** Payment verification load test (planned)
